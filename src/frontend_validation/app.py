import streamlit as st
import pandas as pd
import json
import os

# ==========================================
# PHASE 1: THE DATA ENGINE (UPDATED)
# ==========================================
def get_analysis_ready_data():
    file_path = "ui_payload.json"
    if not os.path.exists(file_path):
        return pd.DataFrame()
    
    with open(file_path, "r") as f:
        raw_data = json.load(f)
        
    df = pd.DataFrame(raw_data)
    
    ui_df = pd.DataFrame()
    # We maintain the study_id even if not explicitly in this specific JSON snippet
    ui_df["Study ID"] = df.get("study_id", "PMC1234567") 
    ui_df["Population"] = df.get("cohort_population", "N/A")
    ui_df["N"] = df.get("sample_size_total", "N/A")
    ui_df["Predictor"] = df.get("predictor", "N/A")
    ui_df["Outcome"] = df.get("outcome", "N/A")
    ui_df["Method"] = df.get("statistical_method", "N/A")
    ui_df["Effect Size (Result)"] = df.get("formatted_effect_size", "Not reported")
    
    # TRUST LAYER: Hidden columns for the Verification Panel
    ui_df["_evidence_quote"] = df.get("source_anchor", "No source provided.")
    ui_df["_confidence"] = df.get("confidence_score", 0.0)
    ui_df["_verdict"] = df.get("auditor_verdict", "UNKNOWN")
    ui_df["_reasoning"] = df.get("auditor_reasoning", "No explanation provided.")
    
    return ui_df

# ==========================================
# PHASE 2: THE ATLAS UI
# ==========================================
st.set_page_config(
    page_title="Sepsis Atlas",
    page_icon="🩸",
    layout="wide"
)

st.title("🩸 Sepsis Atlas Dashboard")
st.subheader("Clinically Verified Evidence for Mortality Estimation")
st.markdown("---")

df = get_analysis_ready_data()

if df.empty:
    st.warning("⚠️ No data found. Ensure 'ui_payload.json' is correctly formatted.")
else:
    display_df = df.fillna("Not Reported")
    visible_cols = [col for col in display_df.columns if not col.startswith("_")]

    st.sidebar.header("🔍 Clinical Filters")
    all_predictors = sorted(display_df["Predictor"].unique().tolist())
    selected_predictor = st.sidebar.multiselect(
        "Filter by Predictor:", options=all_predictors, default=all_predictors
    )
    
    filtered_df = display_df[display_df["Predictor"].isin(selected_predictor)]

    st.markdown("### 📊 Master Evidence Table")
    event = st.dataframe(
        filtered_df,
        column_order=visible_cols, 
        width="stretch",           
        hide_index=True,
        on_select="rerun",         
        selection_mode="single-row"
    )

    # ==========================================
    # PHASE 3: THE TRUST LAYER (AUDITOR UPDATE)
    # ==========================================
    st.markdown("---")
    
    if event.selection.rows:
        selected_index = event.selection.rows[0]
        row_data = filtered_df.iloc[selected_index]
        
        quote_col, audit_col = st.columns([2, 1])
        
        with quote_col:
            st.subheader("🕵️ Source Evidence")
            st.info(f"\"{row_data['_evidence_quote']}\"")
            st.caption(f"Source Link: {row_data['Study ID']}")
            
        with audit_col:
            st.subheader("🤖 Auditor Verdict")
            
            # Use the new Verdict to show visual status
            verdict = row_data["_verdict"]
            conf = row_data["_confidence"]
            
            if verdict == "ENTAILMENT":
                st.success(f"**{verdict}**")
                st.metric("Trust Score", f"{conf*100:.0f}%")
            elif verdict == "NEUTRAL":
                st.warning(f"**{verdict}**")
                st.metric("Trust Score", f"{conf*100:.0f}%", delta="-50%", delta_color="inverse")
            else:
                st.error(f"**{verdict}**")
                st.metric("Trust Score", "0%")

            st.write("**Auditor Reasoning:**")
            st.write(row_data["_reasoning"])
    else:
        st.info("💡 Select a clinical finding in the table above to trigger the AI Auditor verification.")