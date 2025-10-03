"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Separator } from "@/components/ui/separator";
import { CheckCircle2, XCircle, Loader2, Clock, AlertCircle } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

export function ExecutionResults() {
  const { isExecuting, executionResult } = useAppStore();

  // Don't render if not executing and no result
  if (!isExecuting && !executionResult) return null;

  // Executing state
  if (isExecuting) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Loader2 className="h-5 w-5 animate-spin" />
            Executing Request...
          </CardTitle>
          <CardDescription>Please wait while the request is being executed</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  // Must have result at this point
  if (!executionResult) return null;

  const { success, request, response, timing, error } = executionResult;

  // Helper to determine status color
  const getStatusColor = (statusCode: number) => {
    if (statusCode >= 200 && statusCode < 300) return "bg-green-500";
    if (statusCode >= 300 && statusCode < 400) return "bg-blue-500";
    if (statusCode >= 400 && statusCode < 500) return "bg-yellow-500";
    return "bg-red-500";
  };

  // Helper to format JSON
  const formatJSON = (str: string) => {
    try {
      return JSON.stringify(JSON.parse(str), null, 2);
    } catch {
      return str;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {success ? (
            <>
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              Request Executed Successfully
            </>
          ) : (
            <>
              <XCircle className="h-5 w-5 text-red-500" />
              Request Failed
            </>
          )}
        </CardTitle>
        <CardDescription>
          {request.method} {request.url}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Success Response */}
        {success && response && (
          <>
            {/* Status Badge */}
            <div className="flex items-center gap-2">
              <Badge className={getStatusColor(response.status_code)}>
                {response.status_code} {response.status_text}
              </Badge>
              <div className="flex items-center gap-1 text-sm text-muted-foreground">
                <Clock className="h-3 w-3" />
                {timing.execution_time_ms}ms
              </div>
              <Badge variant="outline">{response.size_bytes} bytes</Badge>
            </div>

            {/* Tabbed Content */}
            <Tabs defaultValue="body" className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="body">Response Body</TabsTrigger>
                <TabsTrigger value="headers">Headers</TabsTrigger>
              </TabsList>

              <TabsContent value="body" className="mt-4">
                <div className="relative">
                  <SyntaxHighlighter
                    language={response.headers["content-type"]?.includes("json") ? "json" : "text"}
                    style={vscDarkPlus}
                    customStyle={{
                      borderRadius: "0.5rem",
                      padding: "1rem",
                      fontSize: "0.875rem",
                      maxHeight: "400px",
                    }}
                  >
                    {response.headers["content-type"]?.includes("json")
                      ? formatJSON(response.body)
                      : response.body}
                  </SyntaxHighlighter>
                </div>
              </TabsContent>

              <TabsContent value="headers" className="mt-4">
                <div className="space-y-2">
                  {Object.entries(response.headers).map(([key, value]) => (
                    <div key={key} className="flex flex-col gap-1 p-2 border rounded">
                      <span className="text-sm font-medium font-mono">{key}</span>
                      <span className="text-sm text-muted-foreground font-mono break-all">
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="timing" className="mt-4">
                <div className="space-y-2">
                  <div className="flex justify-between p-2 border rounded">
                    <span className="text-sm font-medium">Total Execution Time</span>
                    <span className="text-sm font-mono">{timing.execution_time_ms}ms</span>
                  </div>
                  {timing.dns_time_ms !== undefined && (
                    <div className="flex justify-between p-2 border rounded">
                      <span className="text-sm font-medium">DNS Lookup</span>
                      <span className="text-sm font-mono">{timing.dns_time_ms}ms</span>
                    </div>
                  )}
                  {timing.connect_time_ms !== undefined && (
                    <div className="flex justify-between p-2 border rounded">
                      <span className="text-sm font-medium">Connection Time</span>
                      <span className="text-sm font-mono">{timing.connect_time_ms}ms</span>
                    </div>
                  )}
                </div>
              </TabsContent>
            </Tabs>
          </>
        )}

        {/* Error Response */}
        {!success && error && (
          <div className="space-y-4">
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{error.type}</Badge>
                  </div>
                  <p className="font-medium">{error.message}</p>
                  {error.details && (
                    <p className="text-sm opacity-90">{error.details}</p>
                  )}
                </div>
              </AlertDescription>
            </Alert>

            {/* Suggestions */}
            {error.suggestions && error.suggestions.length > 0 && (
              <div className="space-y-2">
                <p className="text-sm font-medium">Suggestions:</p>
                <ul className="list-disc list-inside space-y-1">
                  {error.suggestions.map((suggestion, idx) => (
                    <li key={idx} className="text-sm text-muted-foreground">
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Timing even on error */}
            {timing.execution_time_ms && (
              <>
                <Separator />
                <div className="flex items-center gap-1 text-sm text-muted-foreground">
                  <Clock className="h-3 w-3" />
                  Failed after {timing.execution_time_ms}ms
                </div>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
