"use client";

import React, { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { FileText, Clock, CheckCircle, XCircle, Loader2 } from "lucide-react";

interface Document {
  id: number;
  file_name: str;
  status: "pending" | "processed" | "failed";
  created_at: string;
}

interface DocumentListProps {
  refreshKey: number;
}

export default function DocumentList({ refreshKey }: DocumentListProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchDocuments = async () => {
    try {
      const response = await apiFetch("/uploads/documents");
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      }
    } catch (error) {
      console.error("Failed to fetch documents:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
    // Poll for updates if there are pending documents
    const interval = setInterval(() => {
        if (documents.some(doc => doc.status === "pending")) {
            fetchDocuments();
        }
    }, 5000);
    
    return () => clearInterval(interval);
  }, [refreshKey, documents.some(doc => doc.status === "pending")]);

  if (isLoading && documents.length === 0) {
    return <div className="flex justify-center p-8"><Loader2 className="animate-spin h-8 w-8 text-gray-400" /></div>;
  }

  if (documents.length === 0) {
    return (
      <div className="text-center p-8 border-2 border-dashed border-gray-100 rounded-xl">
        <p className="text-gray-400 font-medium">No documents uploaded yet.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-black text-gray-900 mb-4">Uploaded Documents</h3>
      <div className="grid gap-3">
        {documents.map((doc) => (
          <div
            key={doc.id}
            className="flex items-center justify-between p-4 bg-white border-2 border-gray-100 rounded-xl hover:border-blue-100 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="bg-gray-50 p-2 rounded-lg">
                <FileText className="h-5 w-5 text-gray-500" />
              </div>
              <div>
                <p className="font-bold text-gray-900 text-sm">{doc.file_name}</p>
                <p className="text-xs text-gray-400 font-medium">
                  {new Date(doc.created_at).toLocaleDateString()} at {new Date(doc.created_at).toLocaleTimeString()}
                </p>
              </div>
            </div>
            
            <div className="flex items-center">
              {doc.status === "pending" && (
                <span className="flex items-center gap-1.5 bg-yellow-50 text-yellow-700 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider border border-yellow-100">
                  <Clock className="h-3 w-3" />
                  Processing
                </span>
              )}
              {doc.status === "processed" && (
                <span className="flex items-center gap-1.5 bg-green-50 text-green-700 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider border border-green-100">
                  <CheckCircle className="h-3 w-3" />
                  Analyzed
                </span>
              )}
              {doc.status === "failed" && (
                <span className="flex items-center gap-1.5 bg-red-50 text-red-700 px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider border border-red-100">
                  <XCircle className="h-3 w-3" />
                  Failed
                </span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
