"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [data, setData] = useState<any[]>([]);
  const [selectedRow, setSelectedRow] = useState<any>(null);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetch("/ui_payload.json")
      .then((res) => res.json())
      .then((json) => {
        setData(json);
        if (json.length > 0) setSelectedRow(json[0]);
      })
      .catch((err) => console.error("Error loading atlas data:", err));
  }, []);

  const filteredData = data.filter((row) => {
    const searchTerm = query.toLowerCase();
    return (
      row.predictor?.toLowerCase().includes(searchTerm) ||
      row.cohort_population?.toLowerCase().includes(searchTerm) ||
      row.outcome?.toLowerCase().includes(searchTerm)
    );
  });

  return (
    <div className="min-h-screen bg-[#020617] text-slate-100 p-8 font-sans selection:bg-red-500/30">
      <header className="max-w-[1600px] mx-auto mb-10 flex items-center justify-between border-b border-slate-800 pb-6">
        <div className="flex items-center gap-4">
          <div className="bg-red-600 p-3 rounded-xl shadow-2xl text-3xl font-bold">🩸</div>
          <div>
            <h1 className="text-4xl font-black tracking-tight text-white uppercase leading-none">
              stepsis<span className="text-red-500">.ai</span>
            </h1>
            <p className="text-slate-500 text-xs font-bold uppercase tracking-widest mt-2">
              Use Case 1: Counterfactual Mortality Estimation
            </p>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto">
        <div className="mb-8 relative max-w-xl">
          <input 
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search biomarkers, outcomes, or cohorts..."
            className="w-full bg-[#0f172a] border border-slate-800 rounded-2xl py-3 px-6 text-md focus:ring-2 focus:ring-red-500/50 outline-none transition-all shadow-inner"
          />
          <div className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 text-[10px] font-black uppercase bg-slate-950 px-2 py-1 rounded border border-white/5">
            {filteredData.length} Records
          </div>
        </div>

        <div className="grid grid-cols-12 gap-8 items-start">
          {/* TABLE CONTAINER WITH SIDEWAYS SCROLL */}
          <section className="col-span-12 xl:col-span-9 bg-[#0f172a]/50 border border-slate-800 rounded-3xl shadow-2xl backdrop-blur-md overflow-hidden">
            <div className="overflow-x-auto custom-scrollbar">
              <table className="w-full text-left border-collapse min-w-[1300px]">
                <thead className="bg-[#020617] border-b border-slate-800 text-[10px] uppercase text-slate-500 tracking-[0.2em] font-black">
                  <tr>
                    <th className="p-5 w-[20%]">Cohort Description</th>
                    <th className="p-5 w-[15%]">Predictor Variable</th>
                    <th className="p-5 w-[15%]">Outcome Def.</th>
                    <th className="p-5 w-[15%]">Stat. Method</th>
                    <th className="p-5 w-[20%]">Effect Size / Perf.</th>
                    <th className="p-5 w-[15%] text-right">Auditor Verdict</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/50">
                  {filteredData.map((row, i) => (
                    <tr 
                      key={i} 
                      onClick={() => setSelectedRow(row)} 
                      className={`cursor-pointer transition-all duration-200 ${
                        selectedRow === row ? 'bg-red-600/10 border-l-4 border-l-red-600' : 'hover:bg-white/5 border-l-4 border-l-transparent'
                      }`}
                    >
                      <td className="p-5">
                        <div className="text-xs font-bold text-white uppercase">{row.cohort_population}</div>
                        <div className="text-[10px] text-slate-500 mt-1">N = {row.sample_size_total}</div>
                      </td>
                      <td className="p-5">
                        <div className="font-black text-white text-sm">{row.predictor}</div>
                      </td>
                      <td className="p-5 text-[11px] text-slate-400 italic">
                        {row.outcome}
                      </td>
                      <td className="p-5 text-[10px] text-slate-500 uppercase font-mono tracking-tighter">
                        {row.statistical_method}
                      </td>
                      <td className="p-5">
                        <span className="text-xs font-mono text-red-400 bg-black/40 px-3 py-1.5 rounded-lg border border-white/5 shadow-inner">
                          {row.formatted_effect_size}
                        </span>
                      </td>
                      <td className="p-5 text-right whitespace-nowrap">
                        <span className={`px-3 py-1 rounded-full text-[9px] font-black border inline-block ${
                          row.auditor_verdict === 'ENTAILMENT' 
                          ? 'bg-green-500/10 text-green-500 border-green-500/20' 
                          : 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20'
                        }`}>
                          ● {row.auditor_verdict}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          {/* VERIFICATION SIDEBAR */}
          <aside className="col-span-12 xl:col-span-3 space-y-6 sticky top-8">
            {selectedRow && (
              <>
                <div className="bg-[#0f172a] border border-slate-800 p-8 rounded-3xl shadow-2xl relative overflow-hidden">
                  <h3 className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-6 flex items-center gap-2 text-white">
                    <span className="w-2 h-2 rounded-full bg-red-600"></span> Source Grounding
                  </h3>
                  <blockquote className="text-lg italic font-serif text-slate-200 border-l-2 border-red-600 pl-4 py-1 leading-relaxed relative z-10">
                    "{selectedRow.source_anchor}"
                  </blockquote>
                </div>

                <div className="bg-[#0f172a] border border-slate-800 p-8 rounded-3xl shadow-2xl">
                  <h3 className="text-[10px] font-black text-red-500 uppercase tracking-widest mb-4">Auditor Reasoning</h3>
                  <p className="text-xs text-slate-400 leading-relaxed mb-8 italic">
                    {selectedRow.auditor_reasoning}
                  </p>
                  
                  <div className="pt-6 border-t border-slate-800">
                    <div className="flex justify-between items-end mb-3">
                      <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Confidence Score</span>
                      <span className="text-2xl font-black text-white">{(selectedRow.confidence_score * 100).toFixed(0)}%</span>
                    </div>
                    <div className="h-2 w-full bg-slate-950 rounded-full border border-white/5 overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-red-600 to-orange-500 transition-all duration-500 ease-out"
                        style={{ width: `${selectedRow.confidence_score * 100}%` }}
                      ></div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </aside>
        </div>
      </main>
    </div>
  );
}