import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import Dropzone from "../components/Dropzone.jsx";
import Spinner from "../components/Spinner.jsx";
import { uploadPdf } from "../services/api.js";

export default function UploadPage() {
  const navigate = useNavigate();

  const [status, setStatus] = useState("idle"); // idle | uploading | success | error
  const [error, setError] = useState("");
  const [docId, setDocId] = useState("");

  async function handleUpload(file) {
    setError("");
    setStatus("uploading");
    setDocId("");
    try {
      const res = await uploadPdf(file);
      setDocId(res.doc_id);
      setStatus("success");
      localStorage.setItem("selectedDocId", res.doc_id);
      navigate("/chat");
    } catch (e) {
      setStatus("error");
      setError(e?.message || "Upload failed.");
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-10">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Upload PDF</h1>
        <p className="mt-2 text-sm text-gray-600">
          Your document is chunked, embedded, and indexed locally for RAG.
        </p>
      </div>

      <Dropzone onFile={handleUpload} />

      {status === "uploading" ? (
        <div className="mt-4 flex items-center gap-2 text-sm text-gray-700">
          <Spinner />
          Indexing PDF...
        </div>
      ) : null}

      {status === "error" ? (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {status === "success" ? (
        <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
          Upload complete. Document id: <span className="font-mono">{docId}</span>
        </div>
      ) : null}
    </div>
  );
}

