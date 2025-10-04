import useSWR from "swr";
import useSWRMutation from "swr/mutation";
import { api, fetcher } from "./api";
import type {
  StatusResponse,
  RequestDetailsResponse,
  CurlResponse,
  ExecuteResponse,
} from "@/types";

// Poll job status every 2 seconds until completed
export function useJobStatus(jobId: string | null) {
  return useSWR<StatusResponse>(
    jobId ? `/status/${jobId}` : null,
    fetcher,
    {
      refreshInterval: (data) =>
        data?.status === "completed" || data?.status === "failed" ? 0 : 2000,
      revalidateOnFocus: false,
    }
  );
}

// Fetch request details (cached)
export function useRequestDetails(requestId: number | null) {
  return useSWR<RequestDetailsResponse>(
    requestId ? `/request/${requestId}/details` : null,
    fetcher,
    {
      revalidateOnFocus: false,
    }
  );
}

// Generate curl command (mutation)
export function useCurlGeneration() {
  return useSWRMutation<
    CurlResponse,
    Error,
    string,
    { jobId: string; prompt: string; maxCandidates?: number }
  >(
    "/generate-curl",
    async (url, { arg }) => {
      return api.generateCurl(arg.jobId, arg.prompt, arg.maxCandidates);
    }
  );
}

// Execute request (mutation, no cache)
export function useExecuteRequest() {
  return useSWRMutation<
    ExecuteResponse,
    Error,
    string,
    {
      requestId: number;
      overrides?: {
        query_params?: Record<string, string>;
        headers?: Record<string, string>;
        body?: string | null;
      };
      settings?: {
        timeout?: number;
        follow_redirects?: boolean;
      };
    }
  >(
    "/execute-request",
    async (url, { arg }) => {
      return api.executeRequest(arg.requestId, arg.overrides, arg.settings);
    }
  );
}
