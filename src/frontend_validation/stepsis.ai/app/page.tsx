"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [rawData, setRawData] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"risk" | "phenotype">("risk");
  const [selectedRow, setSelectedRow] = useState<any>(null);

  useEffect(() => {
    fetch("/ui_payload.json")
      .then(res => res.json())
      .then(json => {
        // Force the data into a flat array regardless of structure
        const data = Array.isArray(json) ? json : [...(json.biomarkers || []), ...(json.phenotypes || [])];
        console.log("Total Items Loaded:", data.length);
        setRawData(data);
      })
      .catch(e => console.error("JSON Fetch Failed:", e));
  }, []);

  // STRICT FILTERING
  // Biomarkers: Items that do NOT have a cluster_id
  const biomarkers = rawData.filter(item => !item.hasOwnProperty('cluster_id'));
  // Phenotypes: Items that DO have a cluster_id
  const phenotypes = rawData.filter(item => item.hasOwnProperty('cluster_id'));

  const currentList = activeTab === "risk" ? biomarkers : phenotypes;

  // AUTO-SELECT when tab changes
  useEffect(() => {
    if (currentList.length > 0) {
      setSelectedRow(currentList[0]);
    } else {
      setSelectedRow(null);
    }
  }, [activeTab, rawData]);

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 p-8 font-sans selection:bg-red-500/30">
      <header className="max-w-[1600px] mx-auto mb-10 border-b border-slate-800 pb-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="bg-red-600 p-3 rounded-2xl shadow-2xl text-3xl font-bold">🩸</div>
            <h1 className="text-4xl font-black tracking-tighter uppercase leading-none">
              stepsis<span className="text-red-500">.ai</span>
            </h1>
          </div>
          
          {/* TAB SWITCHER WITH DIAGNOSTIC COUNTS */}
          <div className="flex bg-slate-900 p-1.5 rounded-2xl border border-slate-800 shadow-2xl">
            <button 
              onClick={() => setActiveTab("risk")}
              className={`px-8 py-3 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'risk' ? 'bg-red-600 text-white' : 'text-slate-500'}`}
            >
              Risk Predictors ({biomarkers.length})
            </button>
            <button 
              onClick={() => setActiveTab("phenotype")}
              className={`px-8 py-3 rounded-xl text-xs font-black uppercase transition-all ${activeTab === 'phenotype' ? 'bg-blue-600 text-white' : 'text-slate-500'}`}
            >
              Phenotype Atlas ({phenotypes.length})
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto grid grid-cols-12 gap-8 items-start">
        <section className="col-span-12 xl:col-span-9 bg-[#0f172a]/40 border border-slate-800 rounded-3xl shadow-2xl overflow-hidden backdrop-blur-md">
          <div className="overflow-x-auto custom-scrollbar">
            <table className="w-full text-left border-collapse min-w-[1200px]">
              <thead className="bg-[#020617] border-b border-slate-800 text-[10px] uppercase text-slate-500 tracking-[0.2em] font-black">
                {activeTab === "risk" ? (
                  <tr>
                    <th className="p-6">Cohort / Source</th>
                    <th className="p-6">Predictor</th>
                    <th className="p-6">Outcome</th>
                    <th className="p-6 text-center">Effect Size</th>
                    <th className="p-6 text-right">Verdict</th>
                  </tr>
                ) : (
                  <tr>
                    <th className="p-6">Study / Method</th>
                    <th className="p-6 text-center">Cluster</th>
                    <th className="p-6">Key Features</th>
                    <th className="p-6">Interpretation</th>
                    <th className="p-6 text-right">Outcomes</th>
                  </tr>
                )}
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {currentList.length > 0 ? (
                  currentList.map((row, i) => (
                    <tr key={i} onClick={() => setSelectedRow(row)} 
                      className={`cursor-pointer transition-all duration-200 ${selectedRow === row ? (activeTab === 'risk' ? 'bg-red-600/10 border-l-4 border-l-red-600' : 'bg-blue-600/10 border-l-4 border-l-blue-600') : 'hover:bg-white/5 border-l-4 border-l-transparent'}`}>
                      
                      {activeTab === "risk" ? (
                        <>
                          <td className="p-6"><div className="text-xs font-black text-white uppercase">{row.cohort_population}</div></td>
                          <td className="p-6"><div className="font-bold text-white text-sm">{row.predictor}</div><div className="text-[10px] text-slate-500 italic">{row.statistical_method}</div></td>
                          <td className="p-6 text-[11px] text-slate-400">{row.outcome}</td>
                          <td className="p-6 text-center"><span className="text-xs font-mono text-red-400 bg-black/40 px-3 py-1 rounded border border-white/5">{row.formatted_effect_size}</span></td>
                          <td className="p-6 text-right"><span className={`px-2 py-0.5 rounded-full text-[9px] font-black border ${row.auditor_verdict === 'ENTAILMENT' ? 'bg-green-500/10 text-green-500' : 'bg-yellow-500/10 text-yellow-500'}`}>● {row.auditor_verdict}</span></td>
                        </>
                      ) : (
                        <>
                          <td className="p-6"><div className="text-xs font-black text-white uppercase">{row.study}</div><div className="text-[9px] text-slate-500 italic">{row.method}</div></td>
                          <td className="p-6 text-center font-black text-blue-400 text-2xl">{row.cluster_id}</td>
                          <td className="p-6 text-xs text-slate-400 font-mono leading-relaxed">{row.features}</td>
                          <td className="p-6 text-xs font-bold text-slate-200">{row.description}</td>
                          <td className="p-6 text-right text-xs text-red-400 font-black whitespace-nowrap">{row.outcomes}</td>
                        </>
                      )}
                    </tr>
                  ))
                ) : (
                  <tr><td colSpan={5} className="p-20 text-center text-slate-600 italic">No {activeTab} data found. Check your JSON keys.</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </section>

        <aside className="col-span-12 xl:col-span-3 sticky top-8">
          {selectedRow ? (
            <div className="bg-[#0f172a] border border-slate-800 p-8 rounded-3xl shadow-2xl space-y-6 animate-in fade-in zoom-in-95 duration-300">
              <h3 className={`text-[10px] font-black uppercase tracking-widest ${activeTab === 'risk' ? 'text-red-500' : 'text-blue-500'}`}>Evidence Anchor</h3>
              <blockquote className="text-lg italic font-serif leading-relaxed text-slate-200 border-l-2 border-slate-700 pl-4 py-1">"{selectedRow.source_anchor}"</blockquote>
              <div className="pt-6 border-t border-slate-800">
                <div className="flex justify-between items-end mb-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Confidence</span>
                  <span className="text-2xl font-black text-white">{(selectedRow.confidence_score * 100 || 0).toFixed(0)}%</span>
                </div>
                <div className="h-1.5 w-full bg-slate-950 rounded-full border border-white/5 overflow-hidden">
                  <div className={`h-full transition-all duration-700 ${activeTab === 'risk' ? 'bg-red-600' : 'bg-blue-600'}`} style={{ width: `${selectedRow.confidence_score * 100}%` }} />
                </div>
              </div>
            </div>
          ) : (
            <div className="h-64 border-2 border-dashed border-slate-800 rounded-3xl flex items-center justify-center text-slate-600 text-sm italic p-10 text-center">
              Select a clinical finding to trigger the AI Auditor verification.
            </div>
          )}
        </aside>
      </main>
    </div>
  );
}