"use client";

import { HarUploader } from "@/components/HarUploader";
import { ApiDescriptionInput } from "@/components/ApiDescriptionInput";
import { CurlDisplay } from "@/components/CurlDisplay";
import { ExecutionResults } from "@/components/ExecutionResults";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto py-8 px-4 max-w-6xl">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold tracking-tight mb-2">
            🌩️ CloudCruise
          </h1>
          <p className="text-muted-foreground">
            HAR Reverse Engineering - Analyze, generate curl, and execute API requests
          </p>
        </div>

        <div className="space-y-6">
          <HarUploader />
          <ApiDescriptionInput />
          <CurlDisplay />
          <ExecutionResults />
        </div>
      </div>
    </main>
  );
}
