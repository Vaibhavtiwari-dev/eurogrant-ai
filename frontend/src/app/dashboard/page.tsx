"use client";

import React, { useState, useEffect } from "react";
import DocumentUpload from "@/components/DocumentUpload";
import DocumentList from "@/components/DocumentList";
import CompanyProfile from "@/components/CompanyProfile";
import { apiFetch } from "@/lib/api";

export default function DashboardPage() {
  const [refreshKey, setRefreshKey] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleUploadSuccess = () => {
    setRefreshKey(prev => prev + 1);
    setIsProcessing(true);
  };

  // Check if any documents are still pending
  const checkProcessingStatus = async () => {
    try {
      const response = await apiFetch("/uploads/documents");
      if (response.ok) {
        const docs = await response.json();
        const pending = docs.some((doc: any) => doc.status === "pending");
        
        if (!pending && isProcessing) {
            // Processing finished, refresh the profile
            setIsProcessing(false);
            setRefreshKey(prev => prev + 1);
        } else if (pending) {
            setIsProcessing(true);
        }
      }
    } catch (error) {
      console.error("Failed to check processing status:", error);
    }
  };

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isProcessing) {
      interval = setInterval(checkProcessingStatus, 5000);
    }
    return () => clearInterval(interval);
  }, [isProcessing]);

  return (
    <div className="min-h-screen bg-gray-50 p-6 md:p-12">
      <div className="max-w-5xl mx-auto">
        <header className="mb-12 flex justify-between items-end">
          <div>
            <h1 className="text-4xl font-black text-gray-900 mb-2 tracking-tight">
                Organization Dashboard
            </h1>
            <p className="text-gray-500 font-medium text-lg">
                Manage your company profile and documentation.
            </p>
          </div>
          {isProcessing && (
            <div className="flex items-center gap-2 bg-blue-50 text-blue-600 px-4 py-2 rounded-xl border border-blue-100 animate-pulse">
                <span className="w-2 h-2 bg-blue-600 rounded-full animate-ping"></span>
                <span className="font-black text-xs uppercase tracking-widest">AI Analysis in Progress</span>
            </div>
          )}
        </header>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="md:col-span-2 space-y-8">
            <section className="bg-white p-8 rounded-3xl border-2 border-gray-100 shadow-sm relative overflow-hidden">
                <div className="absolute top-0 right-0 p-8 opacity-5">
                    <SparkleBG />
                </div>
                <h2 className="text-2xl font-black text-gray-900 mb-8 flex items-center gap-3">
                    <span className="bg-blue-600 w-3 h-8 rounded-full"></span>
                    Company Profile
                </h2>
                <CompanyProfile refreshKey={refreshKey} />
            </section>

            <section className="bg-white p-8 rounded-3xl border-2 border-gray-100 shadow-sm">
                <DocumentList refreshKey={refreshKey} />
            </section>
          </div>

          <aside className="space-y-8">
            <section className="bg-white p-8 rounded-3xl border-2 border-gray-100 shadow-sm">
                <h3 className="text-xl font-black text-gray-900 mb-6 uppercase tracking-tight">Upload Documents</h3>
                <DocumentUpload onUploadSuccess={handleUploadSuccess} />
                <p className="mt-4 text-xs text-gray-400 font-bold leading-relaxed">
                    Upload your business plan, pitch deck, or financials. Our AI will extract key metrics for grant matching.
                </p>
            </section>

            <section className="bg-black p-8 rounded-3xl shadow-2xl text-white relative overflow-hidden group cursor-pointer">
                <div className="absolute top-0 right-0 -mt-4 -mr-4 w-24 h-24 bg-blue-600 rounded-full blur-3xl opacity-50 group-hover:opacity-80 transition-opacity"></div>
                <h3 className="text-xl font-black mb-1">Growth Plan</h3>
                <p className="text-blue-400 font-bold text-sm mb-6 uppercase tracking-wider">Active Subscription</p>
                <div className="space-y-4 mb-8">
                    <div className="flex justify-between items-end">
                        <span className="text-sm font-bold opacity-60">Monthly Limit</span>
                        <span className="text-lg font-black">5/5 Proposals</span>
                    </div>
                    <div className="w-full bg-gray-800 h-2 rounded-full overflow-hidden">
                        <div className="bg-blue-500 h-full w-full"></div>
                    </div>
                </div>
                <button className="w-full bg-white text-black font-black py-4 rounded-2xl hover:bg-blue-50 transition-colors uppercase tracking-widest text-xs">
                    Manage Billing
                </button>
            </section>
          </aside>
        </div>
      </div>
    </div>
  );
}

function SparkleBG() {
    return (
        <svg width="120" height="120" viewBox="0 0 120 120" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M60 0L64.5 55.5L120 60L64.5 64.5L60 120L55.5 64.5L0 60L55.5 55.5L60 0Z" fill="currentColor"/>
        </svg>
    );
}
