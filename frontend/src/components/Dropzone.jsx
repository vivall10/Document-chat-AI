import React, { useRef, useState } from "react";

export default function Dropzone({ onFile }) {
  const inputRef = useRef(null);
  const [isDragging, setIsDragging] = useState(false);

  return (
    <div
      className={`w-full rounded-lg border-2 border-dashed p-6 text-center transition ${
        isDragging ? "border-blue-500 bg-blue-50" : "border-gray-300 bg-white"
      }`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer?.files?.[0];
        if (file) onFile(file);
      }}
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") inputRef.current?.click();
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onFile(file);
        }}
      />
      <div className="text-base font-semibold text-gray-800">
        Drag & drop your PDF here
      </div>
      <div className="mt-1 text-sm text-gray-600">or click to browse</div>
    </div>
  );
}

