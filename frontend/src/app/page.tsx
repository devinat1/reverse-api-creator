"use client";

import { HarUploader } from "@/components/HarUploader";
import { ApiDescriptionInput } from "@/components/ApiDescriptionInput";
import { CurlDisplay } from "@/components/CurlDisplay";
import { ExecutionResults } from "@/components/ExecutionResults";
import { RequestsTable } from "@/components/RequestsTable";

export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-background to-muted/20">
      <div className="container mx-auto py-8 px-4 max-w-[1800px]">
        {/* HAR Uploader - Full Width */}
        <div className="mb-6">
          <HarUploader />
        </div>

        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
          {/* Left Column - Requests Table */}
          <div className="lg:sticky lg:top-6">
            <RequestsTable />
          </div>

          {/* Right Column - Other Components */}
          <div className="space-y-6">
            <ApiDescriptionInput />
            <CurlDisplay />
            <ExecutionResults />
          </div>
        </div>
      </div>
    </main>
  );
}
