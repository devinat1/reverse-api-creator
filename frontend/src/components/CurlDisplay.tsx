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
    _hasHydrated,
  } = useAppStore();
  const { trigger, isMutating } = useExecuteRequest();
  const [copied, setCopied] = useState(false);

  // Don't render if not hydrated or no curl command
  if (!_hasHydrated || !curlCommand) return null;

  const handleCopy = async () => {
    setCopied(true);
    try {
      await navigator.clipboard.writeText(curlCommand);
    } catch (err) {
      console.error("Failed to copy:", err);
      setCopied(false);
      return;
    }
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
          <Alert className="overflow-hidden">
            <AlertDescription className="overflow-x-auto min-w-0">
              <div className="flex items-center gap-2 min-w-max">
                <Badge variant="outline" className="shrink-0">{matchedRequest.method}</Badge>
                <span className="text-sm font-mono whitespace-nowrap">
                  {matchedRequest.url}
                </span>
                <Badge variant="secondary" className="shrink-0">
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
        <div className="relative w-full overflow-hidden">
          <Button
            onClick={handleCopy}
            variant="secondary"
            size="icon"
            className="absolute top-2 right-2 z-10 h-8 w-8"
          >
            {copied ? (
              <Check className="h-4 w-4" />
            ) : (
              <Copy className="h-4 w-4" />
            )}
          </Button>
          <div className="overflow-x-auto">
            <SyntaxHighlighter
              language="bash"
              style={vscDarkPlus}
              wrapLines={false}
              wrapLongLines={false}
              PreTag="div"
              customStyle={{
                borderRadius: "0.5rem",
                padding: "1rem",
                paddingRight: "3rem",
                fontSize: "0.875rem",
                margin: 0,
                whiteSpace: "pre",
              }}
              codeTagProps={{
                style: {
                  whiteSpace: "pre",
                  wordBreak: "normal",
                  overflowWrap: "normal",
                }
              }}
            >
              {curlCommand}
            </SyntaxHighlighter>
          </div>
        </div>

        {/* Execute Button */}
        <Button
          onClick={handleExecute}
          disabled={!selectedRequestId || isMutating}
          className="w-full"
        >
          <Play className="mr-2 h-4 w-4" />
          {isMutating ? "Executing..." : "Execute Request"}
        </Button>
      </CardContent>
    </Card>
  );
}
