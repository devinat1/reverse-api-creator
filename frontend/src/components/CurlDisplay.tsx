"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Copy, Play, Check, Code2 } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useExecuteRequest } from "@/lib/hooks";
import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

export function CurlDisplay() {
  const {
    curlCommand,
    matchedRequest,
    modelUsed,
    selectedRequestId,
    setIsExecuting,
    setExecutionResult,
  } = useAppStore();
  const { trigger, isMutating } = useExecuteRequest();
  const [copied, setCopied] = useState(false);

  // Don't render if no curl command
  if (!curlCommand) return null;

  const handleCopy = async () => {
    await navigator.clipboard.writeText(curlCommand);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExecute = async () => {
    if (!selectedRequestId) return;

    setIsExecuting(true);
    setExecutionResult(null);

    try {
      const result = await trigger({
        requestId: selectedRequestId,
      });
      setExecutionResult(result);
    } catch (err) {
      console.error("Failed to execute request:", err);
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Code2 className="h-5 w-5" />
          Generated Curl Command
        </CardTitle>
        <CardDescription>
          Curl command ready to use or execute directly
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Matched Request Info */}
        {matchedRequest && (
          <Alert>
            <AlertDescription>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline">{matchedRequest.method}</Badge>
                <span className="text-sm font-mono truncate flex-1">
                  {matchedRequest.url}
                </span>
                <Badge variant="secondary">
                  {matchedRequest.status_code}
                </Badge>
              </div>
            </AlertDescription>
          </Alert>
        )}

        {/* Model Used */}
        {modelUsed && (
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              Generated using:
            </span>
            <Badge variant="outline">{modelUsed}</Badge>
          </div>
        )}

        {/* Curl Command Display */}
        <div className="relative">
          <SyntaxHighlighter
            language="bash"
            style={vscDarkPlus}
            customStyle={{
              borderRadius: "0.5rem",
              padding: "1rem",
              fontSize: "0.875rem",
            }}
          >
            {curlCommand}
          </SyntaxHighlighter>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button
            onClick={handleCopy}
            variant="outline"
            className="flex-1"
          >
            {copied ? (
              <>
                <Check className="mr-2 h-4 w-4" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="mr-2 h-4 w-4" />
                Copy to Clipboard
              </>
            )}
          </Button>

          <Button
            onClick={handleExecute}
            disabled={!selectedRequestId || isMutating}
            className="flex-1"
          >
            <Play className="mr-2 h-4 w-4" />
            {isMutating ? "Executing..." : "Execute Request"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
