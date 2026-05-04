"use client";

import React, { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileText, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

interface DocumentUploadProps {
  onUploadSuccess: () => void;
}

export default function DocumentUpload({ onUploadSuccess }: DocumentUploadProps) {
  const [isUploading, setIsUploading] = useState(false);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles.length === 0) return;

    setIsUploading(true);
    const file = acceptedFiles[0];
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await apiFetch("/uploads/company-document", {
        method: "POST",
        body: formData,
      });

      if (response.ok) {
        toast.success("Document uploaded successfully. Processing started.");
        onUploadSuccess();
      } else {
        const error = await response.json();
        toast.error(error.detail || "Failed to upload document");
      }
    } catch (error) {
      toast.error("An error occurred during upload");
      console.error(error);
    } finally {
      setIsUploading(false);
    }
  }, [onUploadSuccess]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/pdf": [".pdf"],
      "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
      "application/vnd.openxmlformats-officedocument.presentationml.presentation": [".pptx"],
    },
    maxFiles: 1,
    disabled: isUploading,
  });

  return (
    <div
      {...getRootProps()}
      className={`border-4 border-dashed p-8 rounded-xl transition-all cursor-pointer flex flex-col items-center justify-center text-center
        ${isDragActive ? "border-blue-500 bg-blue-50" : "border-gray-200 hover:border-blue-400 hover:bg-gray-50"}
        ${isUploading ? "opacity-50 cursor-not-allowed" : ""}
      `}
    >
      <input {...getInputProps()} />
      {isUploading ? (
        <div className="flex flex-col items-center">
          <Loader2 className="h-12 w-12 text-blue-500 animate-spin mb-4" />
          <p className="text-lg font-bold text-gray-700">Uploading your document...</p>
        </div>
      ) : (
        <>
          <div className="bg-blue-100 p-4 rounded-full mb-4">
            <Upload className="h-8 w-8 text-blue-600" />
          </div>
          <h3 className="text-xl font-black text-gray-900 mb-2">
            {isDragActive ? "Drop it here!" : "Upload Business Plan"}
          </h3>
          <p className="text-gray-500 font-medium max-w-xs">
            Drag and drop your PDF, DOCX, or PPTX here, or click to browse.
          </p>
          <div className="mt-4 flex gap-2">
             <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-bold border border-gray-200">PDF</span>
             <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-bold border border-gray-200">DOCX</span>
             <span className="bg-gray-100 text-gray-600 px-2 py-1 rounded text-xs font-bold border border-gray-200">PPTX</span>
          </div>
        </>
      )}
    </div>
  );
}
