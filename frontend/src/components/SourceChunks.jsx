import React from "react";

function truncate(s, maxLen) {
  if (!s) return "";
  if (s.length <= maxLen) return s;
  return s.slice(0, maxLen) + "...";
}

export default function SourceChunks({ sources = [] }) {
  if (!sources?.length) return null;

  return (
    <div className="mt-3 rounded-lg border border-gray-200 bg-white p-3">
      <div className="mb-2 text-sm font-semibold text-gray-800">Top Sources</div>
      <div className="space-y-2">
        {sources.slice(0, 3).map((s, idx) => (
          <div key={s.chunk_id || idx} className="rounded-md bg-gray-50 p-2">
            <div className="mb-1 text-xs text-gray-600">
              Source {idx + 1} {s.page !== null && s.page !== undefined ? `| page ${s.page}` : ""}
            </div>
            <pre className="whitespace-pre-wrap break-words text-xs text-gray-800">
              {truncate(s.text, 600)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}

