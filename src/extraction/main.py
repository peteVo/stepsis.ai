import os
import json
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from schema import SepsisExtraction, AuditorVerdict

load_dotenv()

client = instructor.from_openai(
    OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )
)

# ---------------------------------------------------------
# Ingest Person 2's JSON Format
# ---------------------------------------------------------
with open("retrieved_chunks.json", "r") as file:
    retrieval_data = json.load(file)

# Build a formatted string for the LLM to read
text_context = "Here are the retrieved document chunks:\n\n"
for item in retrieval_data:
    text_context += f"--- START CHUNK (Source ID: {item.get('source_id', 'Unknown')}) ---\n"
    text_context += f"{item.get('text', '')}\n"
    text_context += f"--- END CHUNK ---\n\n"

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

print("🧠 Step 1: Extracting Sepsis Data from Retrieved JSON...")

try:
    # --- PASS 1: THE EXTRACTION ---
    extraction = client.chat.completions.create(
        model="openai/gpt-4o-mini", 
        response_model=SepsisExtraction, 
        temperature=0.0, 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract the data from this document snippet:\n\n{text_context}"}
        ]
    )

    # We use a dictionary so Person 4 gets two clean lists: one for tables, one for clusters
    final_payload = {
        "biomarkers": [],
        "phenotypes": []
    }
    
    print("🕵️‍♂️ Step 2: Running Clinical Auditor on Biomarkers...")

    # --- PROCESS 1: BIOMARKERS (Use Cases 1 & 3) ---
    for record in extraction.extracted_records:
        
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

        # We use dict() here instead of model_dump() to safely avoid property errors
        row_dict = dict(record) 
        
        row_dict['formatted_effect_size'] = record.formatted_effect_size
        row_dict['confidence_score'] = confidence_score
        row_dict['auditor_reasoning'] = audit.reasoning
        row_dict['auditor_verdict'] = audit.verdict
        
        keys_to_remove = ['or_ci_lower', 'or_ci_upper', 'auc_ci_lower', 'auc_ci_upper', 'odds_ratio']
        for k in keys_to_remove:
            row_dict.pop(k, None)

        final_payload["biomarkers"].append(row_dict)

    # --- PROCESS 2: PHENOTYPES (Use Case 2) ---
    print("🧬 Step 3: Processing Phenotype Data...")
    if extraction.phenotype_data:
        for pheno_study in extraction.phenotype_data:
            # We dump the nested Pydantic models directly to dicts for JSON serialization
            final_payload["phenotypes"].append(pheno_study.model_dump())

    # --- 3. SAVE TO FILE ---
    output_filename = "ui_payload.json"
    with open(output_filename, "w") as f:
        json.dump(final_payload, f, indent=2)
    
    print(f"\n✅ Pipeline Complete! Ideal JSON saved to {output_filename}")

except Exception as e:
    print(f"\n❌ Extraction failed. Error: {e}")