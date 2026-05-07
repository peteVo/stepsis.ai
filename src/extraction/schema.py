from pydantic import BaseModel, Field
from typing import Optional, List

class EvidenceRow(BaseModel):
    # COHORT
    cohort_population: str = Field(description="e.g., 'Adult patients with Sepsis-3'")
    sample_size_total: Optional[int] = Field(description="Total N for the study/cohort.")
    
    # PREDICTOR
    predictor: str = Field(description="e.g., 'Lactate', 'SOFA score', 'Age'")
    predictor_timing: Optional[str] = Field(description="e.g., 'Within 24h of ICU admission'. Null if unknown.")
    
    # OUTCOME
    outcome: str = Field(description="e.g., '28-day mortality'")
    
    # METHODS & STATS (Extracted safely as individual fields)
    statistical_method: str = Field(description="e.g., 'Univariate logistic regression', 'ROC'")
    odds_ratio: Optional[float] = Field(description="The OR value if present.")
    or_ci_lower: Optional[float] = Field(description="Lower 95% CI for OR.")
    or_ci_upper: Optional[float] = Field(description="Upper 95% CI for OR.")
    auc: Optional[float] = Field(description="The AUC value if present.")
    auc_ci_lower: Optional[float] = Field(description="Lower 95% CI for AUC.")
    auc_ci_upper: Optional[float] = Field(description="Upper 95% CI for AUC.")
    p_value: Optional[str] = Field(description="e.g., '<0.001', '0.02'")
    
    # TRACEABILITY
    source_anchor: str = Field(description="VERBATIM quote proving these numbers.")

    # --- Solves Phase 2: The String Stitcher ---
    @property
    def formatted_effect_size(self) -> str:
        """Automatically formats the raw numbers into the judges' required CSV blob."""
        parts = []
        if self.odds_ratio:
            ci_str = f" (95% CI {self.or_ci_lower}-{self.or_ci_upper})" if self.or_ci_lower else ""
            parts.append(f"OR {self.odds_ratio}{ci_str}")
        
        if self.p_value:
            # Handle cases where LLM forgets the '<' or '=' 
            p_str = f"p={self.p_value}" if not any(c in self.p_value for c in ['<', '>', '=']) else f"p{self.p_value}"
            if parts:
                parts[0] += f", {p_str}"
            else:
                parts.append(p_str)
                
        if self.auc:
            ci_str = f" (95% CI {self.auc_ci_lower}-{self.auc_ci_upper})" if self.auc_ci_lower else ""
            parts.append(f"AUC: {self.auc}{ci_str}")
            
        return "; ".join(parts) if parts else "Not reported"

class SepsisExtraction(BaseModel):
    study_id: str = Field(description="Author and Year, e.g., 'Smith 2023'")
    extracted_records: List[EvidenceRow] = Field(description="List of ALL predictors found.")