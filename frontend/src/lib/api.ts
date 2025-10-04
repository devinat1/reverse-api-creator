import type {
  UploadResponse,
  StatusResponse,
  CurlResponse,
  RequestDetailsResponse,
  ExecuteResponse,
  RequestListResponse,
} from "@/types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = {
  uploadHar: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_BASE}/upload-har`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: "Upload failed" }));
      throw new Error(error.detail || "Upload failed");
    }

    return res.json();
  },

  urlToHar: async (url: string): Promise<UploadResponse> => {
    const res = await fetch(`${API_BASE}/url-to-har`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: "URL to HAR conversion failed" }));
      throw new Error(error.detail || "URL to HAR conversion failed");
    }

    return res.json();
  },

  getStatus: async (jobId: string): Promise<StatusResponse> => {
    const res = await fetch(`${API_BASE}/status/${jobId}`);

    if (!res.ok) {
      throw new Error("Failed to fetch status");
    }

    return res.json();
  },

  getJobRequests: async (jobId: string): Promise<RequestListResponse> => {
    const res = await fetch(`${API_BASE}/job/${jobId}/requests`);

    if (!res.ok) {
      throw new Error("Failed to fetch job requests");
    }

    return res.json();
  },

  generateCurl: async (
    jobId: string,
    prompt: string,
    maxCandidates: number = 10
  ): Promise<CurlResponse> => {
    const res = await fetch(`${API_BASE}/generate-curl`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: jobId,
        prompt,
        max_candidates: maxCandidates,
      }),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: "Failed to generate curl" }));
      throw new Error(error.detail || "Failed to generate curl");
    }

    return res.json();
  },

  getRequestDetails: async (
    requestId: number
  ): Promise<RequestDetailsResponse> => {
    const res = await fetch(`${API_BASE}/request/${requestId}/details`);

    if (!res.ok) {
      throw new Error("Failed to fetch request details");
    }

    return res.json();
  },

  executeRequest: async (
    requestId: number,
    overrides?: {
      query_params?: Record<string, string>;
      headers?: Record<string, string>;
      body?: string | null;
    },
    settings?: {
      timeout?: number;
      follow_redirects?: boolean;
    }
  ): Promise<ExecuteResponse> => {
    const res = await fetch(`${API_BASE}/execute-request`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        request_id: requestId,
        overrides,
        timeout: settings?.timeout,
        follow_redirects: settings?.follow_redirects,
      }),
    });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: "Failed to execute request" }));
      throw new Error(error.detail || "Failed to execute request");
    }

    return res.json();
  },
};

// Fetcher function for SWR
export const fetcher = async (url: string) => {
  const res = await fetch(`${API_BASE}${url}`);
  if (!res.ok) throw new Error("Failed to fetch");
  return res.json();
};
