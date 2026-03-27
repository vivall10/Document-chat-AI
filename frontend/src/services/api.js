const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export async function uploadPdf(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Upload failed (${res.status})`);
  }

  return res.json();
}

export async function askQuestion(question, doc_id) {
  const res = await fetch(`${API_BASE_URL}/api/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, doc_id: doc_id || null }),
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Query failed (${res.status})`);
  }

  return res.json();
}

export function askQuestionStream({ question, doc_id, onSources, onDelta, onDone, onError }) {
  const params = new URLSearchParams();
  params.set("question", question);
  if (doc_id) params.set("doc_id", doc_id);

  const url = `${API_BASE_URL}/api/query/stream?${params.toString()}`;
  const es = new EventSource(url);

  es.addEventListener("sources", (e) => {
    try {
      onSources?.(JSON.parse(e.data));
    } catch {
      onSources?.(e.data);
    }
  });

  es.addEventListener("answer_delta", (e) => {
    try {
      const payload = JSON.parse(e.data);
      onDelta?.(payload.delta || "");
    } catch {
      // Fallback: treat raw as delta string.
      onDelta?.(e.data);
    }
  });

  es.addEventListener("done", (e) => {
    try {
      const payload = JSON.parse(e.data);
      onDone?.(payload);
    } catch {
      onDone?.({});
    }
    es.close();
  });

  es.addEventListener("error", (e) => {
    onError?.(e);
    es.close();
  });

  return es;
}

