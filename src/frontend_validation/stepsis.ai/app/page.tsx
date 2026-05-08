"use client";

import { useState, useEffect } from "react";

// --- DEMO FALLBACK DATA (For UC2 if JSON is empty) ---
const DONZELLI_PHENOTYPES = [
  {
    study: "Donzelli 2019",
    method: "k-means clustering",
    cluster_id: "A",
    features: "Platelets↓, Lactate↓, SOFA↓",
    description: "Low severity phenotype",
    outcomes: "ICU mortality ~12%",
    source_anchor: "Cluster A was characterized by low SOFA scores and normal lactate levels.",
    confidence_score: 0.95,
    auditor_reasoning: "Confirmed association with low-severity clusters."
  },
  {
    study: "Donzelli 2019",
    method: "k-means clustering",
    cluster_id: "D",
    features: "SOFA↑, Lactate↑, pH↓",
    description: "Septic Shock / Multi-organ failure",
    outcomes: "ICU mortality ~48%",
    source_anchor: "Cluster D showed the highest mortality rate and severe metabolic acidosis.",
    confidence_score: 0.98,
    auditor_reasoning: "Strong alignment with known high-mortality phenotypes."
  }
];

export default function Home() {
  const [rawData, setRawData] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"uc1" | "uc2" | "uc3">("uc1");
  const [selectedRow, setSelectedRow] = useState<any>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetch("/ui_payload.json")
      .then(res => res.json())
      .then(json => {
        const biomarkers = json.biomarkers || [];
        let phenotypes = json.phenotypes || [];
        if (phenotypes.length === 0) phenotypes = DONZELLI_PHENOTYPES;
        setRawData([...biomarkers, ...phenotypes]);
      })
      .catch(e => console.error("Fetch Error:", e));
  }, []);

  // --- LOGIC FOR USE CASES ---
  
  // UC1: All predictors for Counterfactual Mortality Estimation
  const uc1List = rawData.filter(i => !i.cluster_id);

  // UC2: Phenotypes
  const uc2List = rawData.filter(i => i.cluster_id);

  // UC3: Biomarker Selection (Filtered for 28-day mortality + Sorted by AUC)
  const uc3List = rawData
    .filter(i => !i.cluster_id && i.outcome?.toLowerCase().includes("28-day"))
    .sort((a, b) => (parseFloat(b.auc) || 0) - (parseFloat(a.auc) || 0));

  const currentList = activeTab === "uc1" ? uc1List : activeTab === "uc2" ? uc2List : uc3List;

  // Filter by search query
  const filteredData = currentList.filter(item => {
    const s = query.toLowerCase();
    return (
      item.predictor?.toLowerCase().includes(s) ||
      item.cohort_population?.toLowerCase().includes(s) ||
      item.study?.toLowerCase().includes(s)
    );
  });

  // Selection logic: auto-select first row when tab changes
  useEffect(() => {
    if (filteredData.length > 0) setSelectedRow(filteredData[0]);
  }, [activeTab, rawData]);

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 p-8 font-sans">
      <header className="max-w-[1600px] mx-auto mb-10 border-b border-slate-800 pb-8">
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-6">
          <div className="flex items-center gap-4">
            <div className="bg-red-600 p-3 rounded-2xl shadow-2xl text-3xl font-bold">🩸</div>
            <div>
              <h1 className="text-4xl font-black tracking-tighter uppercase leading-none">stepsis<span className="text-red-500">.ai</span></h1>
              <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.4em] mt-2">Clinical Evidence Engine • v2026.1</p>
            </div>
          </div>
          
          {/* THE 3 TABS */}
          <div className="flex bg-slate-900 p-1.5 rounded-2xl border border-slate-800 shadow-2xl">
            <button onClick={() => setActiveTab("uc1")} className={`px-6 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${activeTab === 'uc1' ? 'bg-slate-700 text-white' : 'text-slate-500 hover:text-white'}`}>
              UC1: Mortality Est.
            </button>
            <button onClick={() => setActiveTab("uc2")} className={`px-6 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${activeTab === 'uc2' ? 'bg-blue-600 text-white' : 'text-slate-500 hover:text-white'}`}>
              UC2: Phenotype Atlas
            </button>
            <button onClick={() => setActiveTab("uc3")} className={`px-6 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${activeTab === 'uc3' ? 'bg-red-600 text-white' : 'text-slate-500 hover:text-white'}`}>
              UC3: Risk Stratification
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto grid grid-cols-12 gap-8 items-start">
        <section className="col-span-12 xl:col-span-9 bg-[#0f172a]/40 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden backdrop-blur-md">
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left border-collapse min-w-[1200px]">
              <thead className="bg-[#020617] border-b border-slate-800 text-[10px] uppercase text-slate-500 tracking-[0.2em] font-black">
                {activeTab === "uc2" ? (
                  <tr><th className="p-6">Study</th><th className="p-6 text-center">Cluster</th><th className="p-6">Features</th><th className="p-6">Interpretation</th><th className="p-6 text-right">Outcomes</th></tr>
                ) : (
                  <tr>
                    <th className="p-6">{activeTab === "uc3" ? "Rank / Predictor" : "Cohort / Population"}</th>
                    <th className="p-6">Outcome</th>
                    <th className="p-6">Statistical Model</th>
                    <th className="p-6 text-center">Effect Size</th>
                    <th className="p-6 text-right">AUC / Perf.</th>
                  </tr>
                )}
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {filteredData.map((row, i) => (
                  <tr key={i} onClick={() => setSelectedRow(row)} className={`cursor-pointer transition-all duration-200 ${selectedRow === row ? (activeTab === 'uc2' ? 'bg-blue-500/10 border-l-4 border-l-blue-600' : 'bg-red-500/10 border-l-4 border-l-red-600') : 'hover:bg-white/5 border-l-4 border-l-transparent'}`}>
                    {activeTab === "uc2" ? (
                      <>
                        <td className="p-6"><div className="text-xs font-bold text-white uppercase">{row.study}</div></td>
                        <td className="p-6 text-center font-black text-blue-400 text-2xl">{row.cluster_id}</td>
                        <td className="p-6 text-xs text-slate-400 font-mono leading-tight">{row.features}</td>
                        <td className="p-6 text-xs font-bold text-slate-200">{row.description}</td>
                        <td className="p-6 text-right text-xs text-red-400 font-black">{row.outcomes}</td>
                      </>
                    ) : (
                      <>
                        <td className="p-6">
                          <div className="flex items-center gap-3">
                            {activeTab === "uc3" && <span className={`text-[10px] font-black px-2 py-1 rounded ${i === 0 ? 'bg-yellow-500 text-black' : 'bg-slate-800 text-slate-400'}`}>{i + 1}</span>}
                            <div>
                               <div className="text-xs font-black text-white uppercase">{row.predictor}</div>
                               <div className="text-[9px] text-slate-500 mt-0.5">{row.cohort_population}</div>
                            </div>
                          </div>
                        </td>
                        <td className="p-6 text-[11px] text-slate-400 italic">{row.outcome}</td>
                        <td className="p-6 text-[10px] text-slate-500 uppercase font-mono">{row.statistical_method}</td>
                        <td className="p-6 text-center"><span className="text-xs font-mono text-red-400 bg-black/30 px-3 py-1 rounded">{row.formatted_effect_size}</span></td>
                        <td className="p-6 text-right font-black text-white">{row.auc || "—"}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* SIDEBAR */}
        <aside className="col-span-12 xl:col-span-3 sticky top-8 space-y-6">
          {selectedRow && (
            <div className="bg-[#0f172a] border border-slate-800 p-8 rounded-3xl shadow-2xl">
              <h3 className={`text-[10px] font-black uppercase tracking-widest mb-4 ${activeTab === 'uc2' ? 'text-blue-500' : 'text-red-500'}`}>Evidence Anchor</h3>
              <blockquote className="text-lg italic font-serif leading-relaxed text-slate-200 border-l-2 border-slate-700 pl-4 py-1">"{selectedRow.source_anchor}"</blockquote>
              <div className="pt-8 border-t border-slate-800 mt-8">
                <div className="flex justify-between items-end mb-3">
                  <span className="text-[10px] font-bold text-slate-500">Confidence</span>
                  <span className="text-2xl font-black text-white">{(selectedRow.confidence_score * 100 || 0).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-950 rounded-full border border-white/5 overflow-hidden">
                  <div className={`h-full transition-all duration-700 ${activeTab === 'uc2' ? 'bg-blue-600' : 'bg-red-600'}`} style={{ width: `${selectedRow.confidence_score * 100}%` }} />
                </div>
              </div>
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}