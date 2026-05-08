from pydantic import BaseModel, Field
from typing import Optional, List, Literal

# ==========================================
# THE AUDITOR
# ==========================================
class AuditorVerdict(BaseModel):
    reasoning: str = Field(description="One sentence explaining why the fact is or isn't supported by the quote.")
    verdict: Literal["ENTAILMENT", "NEUTRAL", "CONTRADICTION"] = Field(
        description="ENTAILMENT = The quote proves the fact perfectly. NEUTRAL = implies it. CONTRADICTION = hallucinates."
    )

# ==========================================
# USE CASE 1 & 3: PREDICTOR / BIOMARKER MODELS
# ==========================================
class EvidenceRow(BaseModel):
    # --- RAG SOURCE ATTRIBUTION ---
    study_id: str = Field(description="The exact Source ID provided in the text chunk, e.g., 'Suttapanit_2022'") 
    
    # --- COHORT ---
    cohort_population: str = Field(description="e.g., 'Adult patients with Sepsis-3'")
    cohort_setting: str = Field(description="e.g., 'ICU, China (Prospective)', 'Multicenter, US'")
    sample_size_total: Optional[int] = Field(description="Total N for the study/cohort.")
    
    # --- PREDICTOR ---
    predictor: str = Field(description="e.g., 'Initial Lactate > 4.0 mmol/L', 'SOFA score'")
    predictor_timing: Optional[str] = Field(description="e.g., 'Within 24h of ICU admission', 'Baseline'. Null if unknown.")
    
    # --- OUTCOME & STATS ---
    outcome: str = Field(description="e.g., '28-day mortality'")
    statistical_method: str = Field(description="e.g., 'Multivariable logistic regression', 'ROC'")
    
    odds_ratio: Optional[float] = Field(description="The OR value if present.")
    or_ci_lower: Optional[float] = Field(description="Lower 95% CI for OR.")
    or_ci_upper: Optional[float] = Field(description="Upper 95% CI for OR.")
    auc: Optional[float] = Field(description="The exact AUC value if present (e.g., 0.78).")
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

# ==========================================
# USE CASE 2: PHENOTYPE MODELS
# ==========================================
class PhenotypeCluster(BaseModel):
    cluster_id: str = Field(description="e.g., 'Cluster A', 'Phenotype 1'")
    key_features: str = Field(description="e.g., 'Platelets down, Lactate down, SOFA down'")
    clinical_description: str = Field(description="e.g., 'Low severity phenotype', 'Hyper-inflammatory'")
    outcomes: str = Field(description="e.g., 'ICU mortality ~12%', 'Highest mortality'")
    notes: Optional[str] = Field(description="Any additional qualitative notes.")

class PhenotypeStudyMetadata(BaseModel):
    # --- RAG SOURCE ATTRIBUTION ---
    study_id: str = Field(description="The exact Source ID provided in the text chunk, e.g., 'Donzelli_2019'")
    
    clustering_method: str = Field(description="e.g., 'k-means clustering', 'latent class analysis'")
    variables_used: str = Field(description="List of variables used for clustering, e.g., '18 vars'")
    number_of_clusters: int = Field(description="Total number of identified phenotypes, e.g., 4")
    
    reproducibility_status: Literal["Assignment Possible", "Insufficient Information"] = Field(
        description="Can a new clinician assign their own patients to these phenotypes based on the text?"
    )
    
    clusters: List[PhenotypeCluster] = Field(description="List of the specific phenotypes identified.")

# ==========================================
# MASTER WRAPPER (Handles everything)
# ==========================================
class SepsisExtraction(BaseModel):
    # Note: NO study_id here anymore. The LLM must assign it at the row level!
    
    # Biomarker/Predictor Rows (Use Case 1 & 3)
    extracted_records: List[EvidenceRow] = Field(
        default_factory=list, 
        description="Extract all individual predictor-to-mortality relationships here."
    )
    
    # Phenotype/Cluster Rows (Use Case 2)
    # Changed to a List so it can extract phenotypes from multiple different chunks safely!
    phenotype_data: List[PhenotypeStudyMetadata] = Field(
        default_factory=list, 
        description="If the chunks identify Sepsis Phenotypes or Clusters, extract them here."
    )