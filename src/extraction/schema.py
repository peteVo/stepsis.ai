from pydantic import BaseModel, Field
from typing import Optional, List

class CohortDetails(BaseModel):
    population_description: str = Field(description="Description of the patient group, e.g., 'ED patients with suspected infection'.")
    total_sample_size: Optional[int] = Field(description="Total 'N' of the cohort. Return null if not explicitly stated.")
    survivors_n: Optional[int] = Field(description="Number of survivors. Return null if not stated.")
    non_survivors_n: Optional[int] = Field(description="Number of non-survivors. Return null if not stated.")

class EffectSizeData(BaseModel):
    metric_type: str = Field(description="The statistical metric used, e.g., 'AUC', 'OR' (Odds Ratio), 'HR' (Hazard Ratio).")
    value: float = Field(description="The actual value of the metric, e.g., 0.78 or 3.42.")
    ci_lower: Optional[float] = Field(description="Lower bound of the 95% Confidence Interval.")
    ci_upper: Optional[float] = Field(description="Upper bound of the 95% Confidence Interval.")
    p_value: Optional[str] = Field(description="The p-value, e.g., '<0.001' or '0.02'.")

class SepsisExtraction(BaseModel):
    study_id: str = Field(description="The ID or name of the paper.")
    
    # Cohort
    cohort: CohortDetails
    
    # Predictor
    predictor_name: str = Field(description="The clinical variable being evaluated, e.g., 'Initial Lactate' or 'Lymphocyte count'.")
    predictor_timing: Optional[str] = Field(description="When was it measured? e.g., 'First 24h', 'Admission'. Return null if unknown.")
    
    # Outcome
    outcome_definition: str = Field(description="What is the outcome? e.g., '28-day mortality', 'In-hospital mortality'.")
    
    # Results & Stats
    effect_size: Optional[EffectSizeData] = Field(description="The statistical relationship between predictor and outcome.")
    
    # Traceability (CRITICAL FOR THE HACKATHON)
    source_quote: str = Field(description="VERBATIM quote from the text that proves these numbers. DO NOT alter the text.")