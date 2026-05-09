"use client";

import React from "react";
import { motion } from "framer-motion";
import { CheckCircle2, Loader2, Clock } from "lucide-react";

export default function RAGProgress() {
  const pipelines = [
    {
      id: "EIC-2024-ACCELERATOR-01",
      title: "Project GreenLithium • €2.5M Request",
      status: "GENERATING",
      statusColor: "text-copper bg-copper/10",
      progress: 65,
      progressColor: "bg-copper",
      subtext: "Context Assembling (RAG)"
    },
    {
      id: "HORIZON-CL5-2024-D3-02",
      title: "NextGen SolarGrid • Consortium Lead",
      status: "READY",
      statusColor: "text-emerald-light bg-emerald/10",
      progress: 100,
      progressColor: "bg-emerald-light",
      subtext: "Review Phase"
    },
    {
      id: "DIGITAL-2024-AI-06",
      title: "GovTech AI Framework • Drafting Phase",
      status: "QUEUED",
      statusColor: "text-on-surface-variant bg-surface-variant/50",
      progress: 10,
      progressColor: "bg-on-surface-variant/30",
      subtext: "Awaiting Context Verification"
    }
  ];

  return (
    <div className="premium-card p-10 space-y-10">
      <div className="flex items-center justify-between">
        <h3 className="text-2xl font-bold flex items-center gap-3">
          <span className="text-copper">#</span>
          RAG Pipeline Progress
        </h3>
        <button className="text-xs font-bold text-emerald-light hover:underline tracking-widest uppercase">View All</button>
      </div>

      <div className="space-y-12">
        {pipelines.map((item, i) => (
          <div key={item.id} className="space-y-4 group">
            <div className="flex items-start justify-between">
              <div className="space-y-1">
                <p className="text-xs font-black tracking-widest text-on-surface-variant opacity-40">{item.id}</p>
                <h4 className="text-sm font-bold text-on-surface group-hover:text-emerald-light transition-colors">{item.title}</h4>
              </div>
              <div className={`px-3 py-1 rounded-md text-[10px] font-black tracking-widest flex items-center gap-2 border border-outline ${item.statusColor}`}>
                {item.status === "GENERATING" && <Loader2 size={10} className="animate-spin" />}
                {item.status === "READY" && <CheckCircle2 size={10} />}
                {item.status === "QUEUED" && <Clock size={10} />}
                {item.status}
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center text-[10px] font-bold text-on-surface-variant opacity-60">
                <span>{item.subtext}</span>
                <span>{item.progress}%</span>
              </div>
              <div className="h-1.5 w-full bg-outline rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${item.progress}%` }}
                  transition={{ duration: 1, delay: i * 0.2 }}
                  className={`h-full ${item.progressColor}`}
                />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
