import os
import json
import time
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from schema import SepsisExtraction, AuditorVerdict
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

client = instructor.from_openai(
    OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )
)

# ---------------------------------------------------------
# AUTO-DISCOVER THE LATEST RAG OUTPUT
# ---------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_RETRIEVAL_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../output/retrieval/"))

if not os.path.exists(BASE_RETRIEVAL_DIR):
    print(f"❌ Error: Directory '{BASE_RETRIEVAL_DIR}' not found.")
    exit(1)

all_json_files = [f for f in os.listdir(BASE_RETRIEVAL_DIR) if f.endswith('.json')]

if not all_json_files:
    print(f"❌ Error: No JSON files found in '{BASE_RETRIEVAL_DIR}'.")
    exit(1)

all_json_files.sort(reverse=True)
latest_filename = all_json_files[0]
full_input_path = os.path.join(BASE_RETRIEVAL_DIR, latest_filename)

print(f"🔎 Auto-detected newest file: {latest_filename}")
print(f"📂 Loading chunks from: {full_input_path}")

try:
    with open(full_input_path, "r") as file:
        raw_data = json.load(file)
except Exception as e:
    print(f"❌ Error loading the JSON file: {e}")
    exit(1)

# Handle Person 3's exact JSON structure (extracting the "retrieved_context" array)
if isinstance(raw_data, dict):
    if "retrieved_context" in raw_data:
        retrieval_data = raw_data["retrieved_context"]
    else:
        retrieval_data = next((val for val in raw_data.values() if isinstance(val, list)), [raw_data])
elif isinstance(raw_data, list):
    retrieval_data = raw_data
else:
    retrieval_data = []

print(f"📦 Successfully loaded {len(retrieval_data)} chunks!")

# ---------------------------------------------------------
# BUILD METADATA LOOKUP DICTIONARY
# We store the page_number and reference so Python can inject it later!
# ---------------------------------------------------------
metadata_lookup = {}
for item in retrieval_data:
    if isinstance(item, dict):
        src_id = item.get('source_id') or item.get('id') or 'Unknown'
        metadata_lookup[src_id] = {
            "source_reference": item.get("source_reference", "Unknown"),
            "page_number": item.get("page_number", "Unknown")
        }

# ---------------------------------------------------------

system_prompt = """
You are an expert clinical data extractor specializing in Sepsis (Sepsis-3).
You have two primary extraction goals:

GOAL 1: PREDICTORS & MORTALITY (Use Cases 1 & 3)
Extract independent predictors (biomarkers, scores) and their effect sizes. 

GOAL 2: SEPSIS PHENOTYPES (Use Case 2)
If the study uses clustering to group patients into distinct Phenotypes, populate the 'phenotype_data' list.

CRITICAL RULES:
1. SOURCE ATTRIBUTION: You MUST correctly assign the 'study_id' field in every row based on the "Source ID" label provided above each chunk.
2. ROW SPLITTER: Create a separate EvidenceRow for EVERY single predictor.
3. NULL ENFORCEMENT: If a value is missing, return null. Do not guess.
4. TRACEABILITY: 'source_anchor' must be the exact sentence.
"""

print("🧠 Step 1: Extracting Sepsis Data from Retrieved JSON (IN PARALLEL)...")
step1_start = time.time()

# --- THE NEW PARALLEL EXTRACTION FUNCTION ---
def extract_single_chunk(chunk_item):
    if not isinstance(chunk_item, dict):
        return None
        
    source_id = chunk_item.get('source_id') or chunk_item.get('id') or 'Unknown'
    text_content = chunk_item.get('text') or chunk_item.get('content') or ''
    
    if not text_content.strip():
        return None
        
    mini_context = f"--- START CHUNK (Source ID: {source_id}) ---\n{text_content}\n--- END CHUNK ---"
    
    try:
        return client.chat.completions.create(
            model="openai/gpt-4o-mini", 
            response_model=SepsisExtraction, 
            temperature=0.0, 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Extract data from this snippet:\n\n{mini_context}"}
            ]
        )
    except Exception as e:
        print(f"⚠️ Error extracting chunk {source_id}: {e}")
        return None

try:
    # Blast chunks to OpenRouter at the same time. 
    # Max workers set to 5 so we don't trip OpenRouter's rate limit for generation.
    with ThreadPoolExecutor(max_workers=5) as executor:
        all_extractions = list(executor.map(extract_single_chunk, retrieval_data))

    # Gather all parallel results into master lists
    master_records = []
    master_phenotypes = []
    
    for ext in all_extractions:
        if ext: # Ensure the chunk didn't error out
            master_records.extend(ext.extracted_records)
            if ext.phenotype_data:
                master_phenotypes.extend(ext.phenotype_data)

    step1_end = time.time()
    print(f"⚡ Step 1 Completed in {step1_end - step1_start:.2f} seconds")

    final_payload = {
        "biomarkers": [],
        "phenotypes": []
    }
    
    print(f"🕵️‍♂️ Step 2: Running Clinical Auditor on {len(master_records)} Biomarkers (IN PARALLEL)...")
    step2_start = time.time()

    def audit_single_record(record):
        claims = []
        if record.odds_ratio is not None: claims.append(f"an Odds Ratio of {record.odds_ratio}")
        if record.auc is not None: claims.append(f"an AUC of {record.auc}")
        if record.p_value is not None: claims.append(f"a p-value of {record.p_value}")
        
        fact_to_check = f"'{record.predictor}' has " + " and ".join(claims) if claims else f"'{record.predictor}' is mentioned."

        auditor_prompt = f"""
        Does the provided Source Quote strictly entail the Extracted Fact?
        Source Quote: "{record.source_anchor}"
        Extracted Fact: "{fact_to_check}"
        """

        try:
            audit = client.chat.completions.create(
                model="openai/gpt-4o-mini",
                response_model=AuditorVerdict,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": "You are a strict clinical auditor. You check if the extracted numbers are explicitly supported by the quote."},
                    {"role": "user", "content": auditor_prompt}
                ]
            )
            
            score_mapping = {"ENTAILMENT": 1.0, "NEUTRAL": 0.5, "CONTRADICTION": 0.0}
            confidence_score = score_mapping.get(audit.verdict, 0.0)
            reasoning = audit.reasoning
            verdict = audit.verdict
        except Exception:
            # Fallback if the auditor API call fails
            confidence_score = 0.0
            reasoning = "Auditor check failed."
            verdict = "CONTRADICTION"
        
        row_dict = dict(record) 
        row_dict['formatted_effect_size'] = record.formatted_effect_size
        row_dict['confidence_score'] = confidence_score
        row_dict['auditor_reasoning'] = reasoning
        row_dict['auditor_verdict'] = verdict
        
        # --- INJECT PERSON 3's METADATA DIRECTLY INTO THE BIOMARKER ROW ---
        src_id = row_dict.get('study_id', '')
        row_dict['source_reference'] = metadata_lookup.get(src_id, {}).get('source_reference', 'Unknown')
        row_dict['page_number'] = metadata_lookup.get(src_id, {}).get('page_number', 'Unknown')
        
        keys_to_remove = ['or_ci_lower', 'or_ci_upper', 'auc_ci_lower', 'auc_ci_upper', 'odds_ratio']
        for k in keys_to_remove:
            row_dict.pop(k, None)
            
        return row_dict

    # Execute auditor in parallel (Safe to use 10 here because the prompts are tiny)
    with ThreadPoolExecutor(max_workers=10) as executor:
        final_payload["biomarkers"] = list(executor.map(audit_single_record, master_records))

    step2_end = time.time()
    print(f"⚡ Step 2 Completed in {step2_end - step2_start:.2f} seconds")

    print("🧬 Step 3: Processing Phenotype Data (Flattening for UI)...")
    
    for pheno_study in master_phenotypes:
        # We loop through the internal clusters and map them to Person 4's exact naming convention
        for cluster in pheno_study.clusters:
            src_id = pheno_study.study_id
            flat_cluster = {
                "study": src_id,
                # --- INJECT PERSON 3's METADATA DIRECTLY INTO THE PHENOTYPE ROW ---
                "source_reference": metadata_lookup.get(src_id, {}).get('source_reference', 'Unknown'),
                "page_number": metadata_lookup.get(src_id, {}).get('page_number', 'Unknown'),
                "method": pheno_study.clustering_method,
                "clusters_count": pheno_study.number_of_clusters,
                "cluster_id": cluster.cluster_id,
                "features": cluster.key_features,
                "description": cluster.clinical_description,
                "outcomes": cluster.outcomes,
                "reproducibility": pheno_study.reproducibility_status,
                "source_anchor": cluster.source_anchor
            }
            final_payload["phenotypes"].append(flat_cluster)

    # ---------------------------------------------------------
    # --- 3. SAVE TO FILE (Auto-Incrementing) ---
    # ---------------------------------------------------------
    OUTPUT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "../../output/extraction/"))
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    file_index = 1
    while True:
        output_filename = f"ui_payload_{file_index}.json"
        full_output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        if not os.path.exists(full_output_path):
            break
            
        file_index += 1

    with open(full_output_path, "w") as f:
        json.dump(final_payload, f, indent=2)
    
    total_time = time.time() - step1_start
    print(f"\n✅ Pipeline Complete in {total_time:.2f} seconds!")
    print(f"💾 Data saved safely to: {full_output_path}")

except Exception as e:
    print(f"\n❌ Pipeline failed. Error: {e}")