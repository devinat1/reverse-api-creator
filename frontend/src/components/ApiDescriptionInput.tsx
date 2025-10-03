"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Loader2 } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useCurlGeneration } from "@/lib/hooks";

const EXAMPLE_PROMPTS = [
  "Get the weather forecast for San Francisco",
  "Can you reverse engineer the API that gives me recipes for a given portion and calorie count?",
  "Can you give me a curl command to get info about the LockheedC-130H Hercules HERBLK?",
];

export function ApiDescriptionInput() {
  const { jobId, promptText, setPromptText, setGenerationResult, _hasHydrated } = useAppStore();
  const { trigger, isMutating, error } = useCurlGeneration();

  const handleGenerate = async () => {
    if (!jobId || !promptText.trim()) return;

    try {
      const result = await trigger({
        jobId,
        prompt: promptText,
        maxCandidates: 10,
      });

      setGenerationResult(
        result.curl_command,
        result.matched_request,
        result.request_id,
        result.model_used
      );
    } catch (err) {
      console.error("Failed to generate curl:", err);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="h-5 w-5" />
          Step 2: Describe the API
        </CardTitle>
        <CardDescription>
          Describe what API request you want to find in natural language
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Textarea
            placeholder="e.g., Get the weather forecast for San Francisco"
            value={_hasHydrated ? promptText : ""}
            onChange={(e) => setPromptText(e.target.value)}
            className="min-h-[100px] resize-none"
            disabled={!jobId || isMutating}
            suppressHydrationWarning
          />
          <div className="flex items-center justify-between">
            <p className="text-xs text-muted-foreground">
              {promptText.length} characters
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <p className="text-sm font-medium">Example prompts:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((example) => (
              <Badge
                key={example}
                variant="outline"
                className="cursor-pointer hover:bg-secondary"
                onClick={() => setPromptText(example)}
              >
                {example}
              </Badge>
            ))}
          </div>
        </div>

        <Button
          onClick={handleGenerate}
          disabled={!jobId || !promptText.trim() || isMutating}
          className="w-full"
        >
          {isMutating ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Generating...
            </>
          ) : (
            "Generate Curl Command"
          )}
        </Button>

        {error && (
          <p className="text-sm text-destructive">{error.message}</p>
        )}
      </CardContent>
    </Card>
  );
}
