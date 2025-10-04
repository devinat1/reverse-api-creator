import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { MatchedRequest, ParameterOverrides, ExecutionSettings, ExecuteResponse } from "@/types";

interface AppState {
  // Hydration state
  _hasHydrated: boolean;

  // Upload state
  jobId: string | null;
  fileName: string | null;
  totalRequests: number;
  uploadProgress: number;

  // Generation state
  promptText: string;
  isGenerating: boolean;
  curlCommand: string | null;
  matchedRequest: MatchedRequest | null;
  selectedRequestId: number | null;
  modelUsed: string | null;

  // UI state
  activeDetailsTab: "auth" | "params" | "response" | "timing";
  activeParamsTab: "query" | "headers" | "body";
  activeResponseTab: "body" | "headers" | "timing";

  // Execution state
  overrides: ParameterOverrides;
  executionSettings: ExecutionSettings;
  executionCount: number;
  isExecuting: boolean;
  executionResult: ExecuteResponse | null;

  // Actions
  setJobId: (id: string | null, fileName: string | null, total: number) => void;
  setPromptText: (text: string) => void;
  setGenerationResult: (
    curl: string,
    request: MatchedRequest,
    requestId: number,
    model: string
  ) => void;
  updateOverrides: (
    type: "query" | "headers" | "body",
    data: Record<string, string> | string | null
  ) => void;
  resetOverrides: () => void;
  setActiveDetailsTab: (tab: "auth" | "params" | "response" | "timing") => void;
  setActiveParamsTab: (tab: "query" | "headers" | "body") => void;
  setActiveResponseTab: (tab: "body" | "headers" | "timing") => void;
  incrementExecutionCount: () => void;
  setExecutionSettings: (settings: Partial<ExecutionSettings>) => void;
  setIsExecuting: (isExecuting: boolean) => void;
  setExecutionResult: (result: ExecuteResponse | null) => void;
  resetState: () => void;
  setHasHydrated: (hasHydrated: boolean) => void;
}

const initialOverrides: ParameterOverrides = {
  queryParams: {},
  headers: {},
  body: null,
};

const initialExecutionSettings: ExecutionSettings = {
  timeout: 30,
  followRedirects: true,
};

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      // Initial state
      _hasHydrated: false,

      jobId: null,
      fileName: null,
      totalRequests: 0,
      uploadProgress: 0,

      promptText: "",
      isGenerating: false,
      curlCommand: null,
      matchedRequest: null,
      selectedRequestId: null,
      modelUsed: null,

      activeDetailsTab: "auth",
      activeParamsTab: "query",
      activeResponseTab: "body",

      overrides: initialOverrides,
      executionSettings: initialExecutionSettings,
      executionCount: 0,
      isExecuting: false,
      executionResult: null,

      // Actions
      setJobId: (id, fileName, total) =>
        set({ jobId: id, fileName, totalRequests: total }),

      setPromptText: (text) => set({ promptText: text }),

      setGenerationResult: (curl, request, requestId, model) =>
        set({
          curlCommand: curl,
          matchedRequest: request,
          selectedRequestId: requestId,
          modelUsed: model,
          isGenerating: false,
        }),

      updateOverrides: (type, data) =>
        set((state) => ({
          overrides: {
            ...state.overrides,
            [type === "query" ? "queryParams" : type === "headers" ? "headers" : "body"]:
              data,
          },
        })),

      resetOverrides: () => set({ overrides: initialOverrides }),

      setActiveDetailsTab: (tab) => set({ activeDetailsTab: tab }),

      setActiveParamsTab: (tab) => set({ activeParamsTab: tab }),

      setActiveResponseTab: (tab) => set({ activeResponseTab: tab }),

      incrementExecutionCount: () =>
        set((state) => ({ executionCount: state.executionCount + 1 })),

      setExecutionSettings: (settings) =>
        set((state) => ({
          executionSettings: { ...state.executionSettings, ...settings },
        })),

      setIsExecuting: (isExecuting) => set({ isExecuting }),

      setExecutionResult: (result) => set({ executionResult: result }),

      setHasHydrated: (hasHydrated) => set({ _hasHydrated: hasHydrated }),

      resetState: () =>
        set({
          jobId: null,
          fileName: null,
          totalRequests: 0,
          uploadProgress: 0,
          promptText: "",
          isGenerating: false,
          curlCommand: null,
          matchedRequest: null,
          selectedRequestId: null,
          modelUsed: null,
          activeDetailsTab: "auth",
          activeParamsTab: "query",
          activeResponseTab: "body",
          overrides: initialOverrides,
          executionSettings: initialExecutionSettings,
          executionCount: 0,
          isExecuting: false,
          executionResult: null,
        }),
    }),
    {
      name: "cloudcruise-storage",
      partialize: (state) => ({
        jobId: state.jobId,
        fileName: state.fileName,
        totalRequests: state.totalRequests,
        promptText: state.promptText,
        curlCommand: state.curlCommand,
        matchedRequest: state.matchedRequest,
        selectedRequestId: state.selectedRequestId,
        modelUsed: state.modelUsed,
        activeDetailsTab: state.activeDetailsTab,
        activeParamsTab: state.activeParamsTab,
        activeResponseTab: state.activeResponseTab,
        overrides: state.overrides,
        executionSettings: state.executionSettings,
        executionCount: state.executionCount,
        executionResult: state.executionResult,
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
