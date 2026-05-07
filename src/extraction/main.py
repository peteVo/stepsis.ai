import os
import instructor
from openai import OpenAI
from dotenv import load_dotenv
from schema import SepsisExtraction 
import pandas as pd # We will use this to print the final table!

load_dotenv()

client = instructor.from_openai(
    OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )
)

with open("testing/dummy_context.txt", "r") as file:
    text_context = file.read()

# --- Solves Phase 3: The Row Splitter Logic ---
system_prompt = """
You are an expert clinical data extractor specializing in Sepsis (Sepsis-3).
Your objective is to extract evidence for "Counterfactual Mortality Estimation".

CRITICAL RULES:
1. THE ROW SPLITTER: You MUST create a separate EvidenceRow for EVERY single predictor or variable mentioned. If a table lists Age, SOFA, and Lactate, you MUST output 3 separate rows.
2. NULL ENFORCEMENT: If a specific confidence interval or p-value is missing, return null. Do not guess.
3. TRACEABILITY: 'source_anchor' must be the exact sentence or table row where you found the data.
"""

print("Sending text to OpenRouter for extraction...")

try:
    extraction = client.chat.completions.create(
        model="openai/gpt-4o-mini", 
        response_model=SepsisExtraction, 
        temperature=0.0, 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Extract the data from this document snippet:\n\n{text_context}"}
        ]
    )

    # Convert the extracted Pydantic objects into a Pandas DataFrame
    # This proves you have an "Analysis-Ready" flat table!
    rows = []
    for record in extraction.extracted_records:
        row_dict = record.model_dump(exclude={'odds_ratio', 'or_ci_lower', 'or_ci_upper', 'auc', 'auc_ci_lower', 'auc_ci_upper'})
        row_dict['Effect Size, performance and significance'] = record.formatted_effect_size
        rows.append(row_dict)

    df = pd.DataFrame(rows)
    
    use_case_1_columns = [
        'cohort_population', 
        'predictor', 
        'outcome', 
        'statistical_method', 
        'Effect Size, performance and significance', 
        'source_anchor'
    ]

    print("\nExtraction Successful! Here is your Flat Table:\n")
    # Print specific columns to check our work
    print(df[use_case_1_columns].to_markdown(index=False))

except Exception as e:
    print(f"\nExtraction failed. Error: {e}")
