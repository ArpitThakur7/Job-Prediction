"use client";

import React, { Suspense } from "react";
import JobDetailClient from "../[id]/JobDetailClient";

export default function JobDetailPage() {
  return (
    <Suspense
      fallback={
        <div className="py-24 flex flex-col items-center justify-center space-y-3">
          <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-xs font-mono text-slate-500 dark:text-slate-400">Loading job details...</span>
        </div>
      }
    >
      <JobDetailClient id="" />
    </Suspense>
  );
}
