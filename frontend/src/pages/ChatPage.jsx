import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Spinner from "../components/Spinner.jsx";
import ChatMessage from "../components/ChatMessage.jsx";
import { askQuestionStream } from "../services/api.js";

function uid() {
  return Math.random().toString(16).slice(2) + Date.now().toString(16);
}

export default function ChatPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef(null);
  const eventSourceRef = useRef(null);
  const assistantIdRef = useRef(null);

  const selectedDocId = useMemo(() => localStorage.getItem("selectedDocId") || "", []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    return () => {
      try {
        eventSourceRef.current?.close?.();
      } catch {
        // ignore
      }
    };
  }, []);

  function updateAssistantMessage(assistantId, patchFn) {
    setMessages((prev) =>
      prev.map((m) => {
        if (m.id !== assistantId) return m;
        return patchFn(m);
      }),
    );
  }

  async function handleSend(e) {
    e?.preventDefault?.();
    const q = question.trim();
    if (!q) {
      setError("Please type a question.");
      return;
    }
    setError("");

    if (loading) {
      try {
        eventSourceRef.current?.close?.();
      } catch {
        // ignore
      }
    }

    const userMsg = { id: uid(), role: "user", content: q };
    const assistantId = uid();
    assistantIdRef.current = assistantId;

    const assistantMsg = { id: assistantId, role: "assistant", content: "", sources: [] };

    setMessages((prev) => [...prev, userMsg, assistantMsg]);
    setQuestion("");
    setLoading(true);

    const es = askQuestionStream({
      question: q,
      doc_id: selectedDocId || null,
      onSources: (sources) => {
        updateAssistantMessage(assistantId, (m) => ({ ...m, sources: sources || [] }));
      },
      onDelta: (delta) => {
        updateAssistantMessage(assistantId, (m) => ({ ...m, content: (m.content || "") + (delta || "") }));
      },
      onDone: () => {
        setLoading(false);
      },
      onError: () => {
        setLoading(false);
        setError("Request failed. Check backend logs and your API key.");
      },
    });

    eventSourceRef.current = es;
  }

  return (
    <div className="mx-auto max-w-4xl px-4 py-8">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chat with your PDF</h1>
          <p className="mt-1 text-sm text-gray-600">
            Retrieval-Augmented Generation (FAISS + SentenceTransformers).
          </p>
          {selectedDocId ? (
            <p className="mt-2 text-xs text-gray-500">
              Searching: <span className="font-mono">{selectedDocId}</span>
            </p>
          ) : (
            <p className="mt-2 text-xs text-gray-500">No document selected yet.</p>
          )}
        </div>

        <button
          className="rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 hover:bg-gray-50"
          onClick={() => navigate("/upload")}
          type="button"
        >
          Upload new PDF
        </button>
      </div>

      <div className="h-[60vh] overflow-y-auto rounded-xl border border-gray-200 bg-white p-4">
        {messages.length === 0 ? (
          <div className="text-sm text-gray-600">
            Upload a PDF, then ask questions here. The answer will include the top 3 source chunks.
          </div>
        ) : null}

        <div className="space-y-4">
          {messages.map((m) => (
            <ChatMessage key={m.id} msg={m} />
          ))}
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Spinner />
              Generating answer...
            </div>
          ) : null}
          {error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">{error}</div>
          ) : null}
          <div ref={endRef} />
        </div>
      </div>

      <form className="mt-4 flex gap-2" onSubmit={handleSend}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your document..."
          className="flex-1 rounded-md border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 outline-none focus:border-blue-400"
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-gray-900 px-4 py-2 text-sm font-semibold text-white hover:bg-black disabled:opacity-60"
        >
          Send
        </button>
      </form>
    </div>
  );
}

