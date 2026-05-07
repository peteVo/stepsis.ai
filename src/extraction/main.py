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

with open("testing/dummy_context.txt", "r") as file:
    text_context = file.read()

system_prompt = """
You are an expert clinical data extractor specializing in Sepsis (Sepsis-3).
CRITICAL RULES:
1. THE ROW SPLITTER: You MUST create a separate EvidenceRow for EVERY single predictor or variable mentioned.
2. NULL ENFORCEMENT: If a specific confidence interval or p-value is missing, return null. Do not guess.
3. TRACEABILITY: 'source_anchor' must be the exact sentence or table row where you found the data.
"""

print("🧠 Step 1: Extracting Sepsis Data...")

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

    final_payload = []
    
    print("🕵️‍♂️ Step 2: Running Clinical Auditor (NLI Verification)...")

    for record in extraction.extracted_records:
        
        # --- THE FIX: Build a dynamic claim string so we don't audit 'None' ---
        claims = []
        if record.odds_ratio is not None: claims.append(f"an Odds Ratio of {record.odds_ratio}")
        if record.auc is not None: claims.append(f"an AUC of {record.auc}")
        if record.p_value is not None: claims.append(f"a p-value of {record.p_value}")
        
        # Stitch it together. If there are no numbers at all, just fall back to a basic mention.
        fact_to_check = f"'{record.predictor}' has " + " and ".join(claims) if claims else f"'{record.predictor}' is mentioned."

        # 1. Auditor Call
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

        # ---------------------------------------------------------
        # 2. THE FLATTENING LOGIC (Creates the perfect UI Payload)
        # ---------------------------------------------------------
        
        # Convert the Pydantic row model to a dictionary
        row_dict = record.model_dump()
        
        # INJECT the study_id from the parent document!
        row_dict['study_id'] = extraction.study_id
        
        # Inject the stitched effect size string
        row_dict['formatted_effect_size'] = record.formatted_effect_size
        
        # Inject Auditor stats
        row_dict['confidence_score'] = confidence_score
        row_dict['auditor_reasoning'] = audit.reasoning
        row_dict['auditor_verdict'] = audit.verdict
        
        # Clean up the output to exactly match the Ideal JSON schema (Optional but clean)
        keys_to_remove = ['or_ci_lower', 'or_ci_upper', 'auc_ci_lower', 'auc_ci_upper', 'odds_ratio']
        for k in keys_to_remove:
            row_dict.pop(k, None)

        # Add it to the final array
        final_payload.append(row_dict)

    # 3. Save to file
    output_filename = "ui_payload.json"
    with open(output_filename, "w") as f:
        json.dump(final_payload, f, indent=2)
    
    print(f"\n✅ Pipeline Complete! Ideal JSON saved to {output_filename}")
    
    # Print a quick preview
    for item in final_payload:
        print(f"Predictor: {item['predictor']}")
        print(f"Verdict: {item['auditor_verdict']} ({item['confidence_score']}) -> {item['auditor_reasoning']}\n")

except Exception as e:
<<<<<<< HEAD
    print(f"\nExtraction failed. Error: {e}")
=======
    print(f"\n❌ Extraction failed. Error: {e}")
>>>>>>> 91bb224f78224b41ced81f4ce1659d05d3039149
