from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class AuditorVerdict(BaseModel):
    reasoning: str = Field(description="One sentence explaining why the fact is or isn't supported by the quote.")
    verdict: Literal["ENTAILMENT", "NEUTRAL", "CONTRADICTION"] = Field(
        description="ENTAILMENT = The quote proves the fact perfectly. NEUTRAL = implies it. CONTRADICTION = hallucinates."
    )

class EvidenceRow(BaseModel):
    # --- 1. EXPANDED COHORT ---
    cohort_population: str = Field(description="e.g., 'Adult patients with Sepsis-3'")
    cohort_setting: str = Field(description="e.g., 'ICU, China (Prospective)', 'Multicenter, US'") # <--- NEW
    sample_size_total: Optional[int] = Field(description="Total N for the study/cohort.")
    
    # --- 2. PREDICTOR TIMING ---
    predictor: str = Field(description="e.g., 'Initial Lactate > 4.0 mmol/L', 'SOFA score'")
    predictor_timing: Optional[str] = Field(description="e.g., 'Within 24h of ICU admission', 'Baseline'. Null if unknown.") # <--- HIGHLIGHTED
    
    outcome: str = Field(description="e.g., '28-day mortality'")
    statistical_method: str = Field(description="e.g., 'Multivariable logistic regression', 'ROC'")
    
    # --- 3. SEPARATED AUC ---
    odds_ratio: Optional[float] = Field(description="The OR value if present.")
    or_ci_lower: Optional[float] = Field(description="Lower 95% CI for OR.")
    or_ci_upper: Optional[float] = Field(description="Upper 95% CI for OR.")
    auc: Optional[float] = Field(description="The exact AUC value if present (e.g., 0.78).") # <--- EXPLICITLY SEPARATED
    auc_ci_lower: Optional[float] = Field(description="Lower 95% CI for AUC.")
    auc_ci_upper: Optional[float] = Field(description="Upper 95% CI for AUC.")
    p_value: Optional[str] = Field(description="e.g., '<0.001', '0.02'")
    
    source_anchor: str = Field(description="VERBATIM quote proving these numbers.")

    @property
    def formatted_effect_size(self) -> str:
        parts = []
        if self.odds_ratio:
            ci_str = f" (95% CI {self.or_ci_lower}-{self.or_ci_upper})" if self.or_ci_lower else ""
            parts.append(f"OR {self.odds_ratio}{ci_str}")
            
        if self.auc:
            ci_str = f" (95% CI {self.auc_ci_lower}-{self.auc_ci_upper})" if self.auc_ci_lower else ""
            parts.append(f"AUC {self.auc}{ci_str}")
            
        if self.p_value:
            p_str = f"p={self.p_value}" if not any(c in self.p_value for c in ['<', '>', '=']) else f"p{self.p_value}"
            parts.append(p_str)
            
        return "; ".join(parts) if parts else "Not reported"

class SepsisExtraction(BaseModel):
    # --- 4. BIBLIOGRAPHIC METADATA ---
    study_id: str = Field(description="Author and Year + DOI if available, e.g., 'Gai et al. 2022'") # <--- NEW
    extracted_records: List[EvidenceRow] = Field(description="List of ALL predictors found.")