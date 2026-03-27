import React from "react";

export default function Spinner({ className = "" }) {
  return (
    <div className={`inline-flex items-center ${className}`}>
      <div className="h-5 w-5 animate-spin rounded-full border-2 border-gray-300 border-t-gray-900" />
    </div>
  );
}

