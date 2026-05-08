"use client";

import { useState, useEffect } from "react";

// --- DEMO FALLBACK DATA ---
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
    auditor_reasoning: "Confirmed association with low-severity clusters.",
    source_reference: "Donzelli_2019, Page 4, Chunk 1/3"
  }
];

export default function Home() {
  const [data, setData] = useState<{ biomarkers: any[], phenotypes: any[] }>({ biomarkers: [], phenotypes: [] });
  // Add this new state (defaulting to 30 just in case)
  const [articleCount, setArticleCount] = useState<number>(30);
  const [activeTab, setActiveTab] = useState<"uc1" | "uc2" | "uc3">("uc1");
  const [selectedRow, setSelectedRow] = useState<any>(null);
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // INITIAL LOAD
  useEffect(() => {
    // NEW: Fetch the live PDF count
    fetch("/api/stats")
      .then(res => res.json())
      .then(json => {
        if (json.count) setArticleCount(json.count);
      })
      .catch(e => console.error("Stats Fetch Error:", e));

    // EXISTING: Fetch the initial payload
    fetch("/ui_payload.json")
      .then(res => res.json())
      .then(json => {
        setData({
          biomarkers: json.biomarkers || [],
          phenotypes: json.phenotypes?.length ? json.phenotypes : DONZELLI_PHENOTYPES
        });
      })
      .catch(e => console.error("Initial Fetch Error:", e));
  }, []);

  // 1. TRIGGER THE BACKEND PIPELINE (run.sh via API)
  const handleRunAnalysis = async () => {
    if (!prompt) return;
    setLoading(true);
    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      const result = await res.json();
      if (result.error) throw new Error(result.error);
      
      setData({
        biomarkers: result.biomarkers || [],
        phenotypes: result.phenotypes?.length ? result.phenotypes : DONZELLI_PHENOTYPES
      });
      setPrompt("");
    } catch (e) {
      console.error("Pipeline Error:", e);
      alert("Pipeline Execution Failed. Check Terminal Logs.");
    } finally {
      setLoading(false);
    }
  };

  // 2. CSV EXPORT LOGIC
  const downloadCSV = () => {
    const list = activeTab === "uc2" ? data.phenotypes : data.biomarkers;
    if (!list.length) return;

    const headers = Object.keys(list[0]).join(",");
    const rows = list.map(row => 
      Object.values(row).map(value => `"${String(value).replace(/"/g, '""')}"`).join(",")
    ).join("\n");

    const blob = new Blob([`${headers}\n${rows}`], { type: "text/csv" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `stepsis_evidence_${activeTab}.csv`;
    a.click();
  };

  // --- USE CASE FILTERING ---
  const uc1List = data.biomarkers;
  const uc2List = data.phenotypes;
  const uc3List = data.biomarkers
    .filter(i => i.outcome?.toLowerCase().includes("28-day"))
    .sort((a, b) => (parseFloat(b.auc) || 0) - (parseFloat(a.auc) || 0));

  const currentList = activeTab === "uc1" ? uc1List : activeTab === "uc2" ? uc2List : uc3List;

  const filteredData = currentList.filter(item => {
    const s = searchQuery.toLowerCase();
    return (
      item.predictor?.toLowerCase().includes(s) ||
      item.study?.toLowerCase().includes(s) ||
      item.cohort_population?.toLowerCase().includes(s)
    );
  });

  // Selection auto-sync
  useEffect(() => {
    if (filteredData.length > 0) setSelectedRow(filteredData[0]);
  }, [activeTab, data]);

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 p-8 font-sans selection:bg-red-500/30">
      <header className="max-w-[1600px] mx-auto mb-10 border-b border-slate-800 pb-8">
        <div className="flex flex-col xl:flex-row xl:items-center justify-between gap-8">
          <div className="flex items-center gap-4">
            <div className="bg-red-600 p-3 rounded-2xl shadow-2xl text-3xl font-bold animate-pulse">🩸</div>
            <div>
              <h1 className="text-4xl font-black tracking-tighter uppercase leading-none italic">
                stepsis<span className="text-red-500">.ai</span>
              </h1>
              <p className="text-[10px] text-slate-500 font-black uppercase tracking-[0.4em] mt-2">
                Unified Sepsis Evidence Pipeline
              </p>
            </div>
          </div>

          {/* PIPELINE INPUT */}
          <div className="flex-1 max-w-2xl relative group">
            <input 
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={loading}
              placeholder="Type clinical question to trigger RAG pipeline..."
              className="w-full bg-[#0f172a] border border-slate-700 rounded-2xl py-4 px-6 pr-32 outline-none focus:ring-2 focus:ring-red-500/50 transition-all text-lg"
            />
            <button 
              onClick={handleRunAnalysis}
              disabled={loading}
              className="absolute right-2 top-2 bottom-2 bg-red-600 hover:bg-red-500 disabled:bg-slate-800 text-white px-6 rounded-xl font-black text-xs uppercase tracking-tighter transition-all"
            >
              {loading ? "Processing..." : "Run Analysis"}
            </button>
          </div>
        </div>

        {/* TAB NAVIGATION & DOWNLOAD */}
        <div className="flex items-center justify-between mt-10">
          <div className="flex bg-slate-900 p-1.5 rounded-2xl border border-slate-800 shadow-xl">
            <button onClick={() => setActiveTab("uc1")} className={`px-6 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${activeTab === 'uc1' ? 'bg-slate-700 text-white shadow-md' : 'text-slate-500'}`}>UC1: Mortality Estimation</button>
            <button onClick={() => setActiveTab("uc2")} className={`px-6 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${activeTab === 'uc2' ? 'bg-blue-600 text-white shadow-md' : 'text-slate-500'}`}>UC2: Phenotype Atlas</button>
            <button onClick={() => setActiveTab("uc3")} className={`px-6 py-3 rounded-xl text-[10px] font-black uppercase transition-all ${activeTab === 'uc3' ? 'bg-red-600 text-white shadow-md' : 'text-slate-500'}`}>UC3: Risk Stratification</button>
          </div>
          
          <div className="flex gap-4">
             <input 
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search results..."
              className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-xs outline-none focus:border-slate-500"
            />
            <button onClick={downloadCSV} className="bg-white/5 hover:bg-white/10 text-white border border-white/10 px-6 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all">
              Download CSV
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto grid grid-cols-12 gap-8 items-start">
        {/* MAIN RESULTS TABLE */}
        <section className="col-span-12 xl:col-span-9 bg-[#0f172a]/40 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden backdrop-blur-md min-h-[500px] relative">
          {loading && (
             <div className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm z-10 flex flex-col items-center justify-center space-y-4">
                <div className="w-12 h-12 border-4 border-red-600 border-t-transparent rounded-full animate-spin"></div>
                <p className="text-xs font-black uppercase tracking-widest text-red-500">
                  Synthesizing Evidence from {articleCount} Articles...
                </p>
             </div>
          )}
          
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left border-collapse min-w-[1200px]">
              <thead className="bg-[#020617] border-b border-slate-800 text-[10px] uppercase text-slate-500 tracking-[0.2em] font-black">
                {activeTab === "uc2" ? (
                  <tr><th className="p-6">Study</th><th className="p-6 text-center">Cluster</th><th className="p-6">Features</th><th className="p-6">Description</th><th className="p-6 text-right">Outcomes</th></tr>
                ) : (
                  <tr>
                    <th className="p-6">{activeTab === "uc3" ? "Rank / Predictor" : "Cohort / Source"}</th>
                    <th className="p-6">Outcome</th>
                    <th className="p-6">Stat. Model</th>
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
                        <td className="p-6"><div className="text-xs font-bold text-white uppercase">{row.study || row.study_id}</div></td>
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
                              <div className="text-[9px] text-slate-500 mt-1">{row.cohort_population || "Total Cohort"}</div>
                            </div>
                           </div>
                        </td>
                        <td className="p-6 text-[11px] text-slate-400 italic">{row.outcome}</td>
                        <td className="p-6 text-[10px] text-slate-500 uppercase font-mono">{row.statistical_method}</td>
                        <td className="p-6 text-center font-mono text-red-400 text-xs">{row.formatted_effect_size}</td>
                        <td className="p-6 text-right font-black text-white">{row.auc || "—"}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* GROUNDING PANEL */}
        <aside className="col-span-12 xl:col-span-3 sticky top-8 space-y-6">
          {selectedRow && (
            <div className="bg-[#0f172a] border border-slate-800 p-8 rounded-3xl shadow-2xl animate-in fade-in slide-in-from-right-4 duration-300">
              <h3 className={`text-[10px] font-black uppercase tracking-widest mb-6 ${activeTab === 'uc2' ? 'text-blue-500' : 'text-red-500'}`}>Evidence Grounding</h3>
              
              {/* NEW: SOURCE REFERENCE BADGE */}
              {selectedRow.source_reference && (
                <div className="mb-4 inline-flex items-center gap-2 bg-slate-950/50 border border-slate-700/50 px-3 py-1.5 rounded-lg">
                  <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span className="text-[10px] font-mono text-slate-300 tracking-tight">
                    {selectedRow.source_reference}
                  </span>
                </div>
              )}

              <blockquote className="text-lg italic font-serif leading-relaxed text-slate-200 border-l-2 border-slate-700 pl-4 py-1">
                "{selectedRow.source_anchor}"
              </blockquote>
              
              <div className="pt-8 border-t border-slate-800 mt-8">
                <div className="flex justify-between items-end mb-3">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Confidence Score</span>
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