import React from "react";
import SourceChunks from "./SourceChunks.jsx";

export default function ChatMessage({ msg }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] whitespace-pre-wrap break-words rounded-xl border p-3 ${
          isUser
            ? "border-blue-200 bg-blue-50 text-gray-900"
            : "border-gray-200 bg-white text-gray-900"
        }`}
      >
        <div className="text-xs font-semibold text-gray-600 mb-1">
          {isUser ? "You" : "Assistant"}
        </div>
        <div className="text-sm leading-relaxed">{msg.content}</div>

        {!isUser && msg.sources && msg.sources.length > 0 ? (
          <SourceChunks sources={msg.sources} />
        ) : null}
      </div>
    </div>
  );
}

