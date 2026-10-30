"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function JobBoardRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/jobs");
  }, [router]);

  return (
    <div className="py-24 flex flex-col items-center justify-center space-y-3 font-mono">
      <div className="w-10 h-10 border-4 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
      <p className="text-xs text-slate-600 dark:text-slate-400 font-bold">
        Redirecting to Unified Jobs Hub & Direct Apply Platform...
      </p>
    </div>
  );
}
