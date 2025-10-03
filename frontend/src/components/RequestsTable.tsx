"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Loader2, AlertCircle, Database } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useJobStatus } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { RequestListItem } from "@/types";

export function RequestsTable() {
  const { jobId } = useAppStore();
  const { data: status } = useJobStatus(jobId);
  const [requests, setRequests] = useState<RequestListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Only fetch if job is completed
    if (!jobId || status?.status !== "completed") {
      setRequests([]);
      return;
    }

    const fetchRequests = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getJobRequests(jobId);
        setRequests(data.requests);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load requests");
      } finally {
        setIsLoading(false);
      }
    };

    fetchRequests();
  }, [jobId, status?.status]);

  // Helper to get status color
  const getStatusColor = (statusCode: number | null) => {
    if (!statusCode) return "bg-gray-500";
    if (statusCode >= 200 && statusCode < 300) return "bg-green-500";
    if (statusCode >= 300 && statusCode < 400) return "bg-blue-500";
    if (statusCode >= 400 && statusCode < 500) return "bg-yellow-500";
    return "bg-red-500";
  };

  // Helper to get method color
  const getMethodColor = (method: string) => {
    const colors: Record<string, string> = {
      GET: "bg-blue-500/10 text-blue-500 border-blue-500/20",
      POST: "bg-green-500/10 text-green-500 border-green-500/20",
      PUT: "bg-yellow-500/10 text-yellow-500 border-yellow-500/20",
      DELETE: "bg-red-500/10 text-red-500 border-red-500/20",
      PATCH: "bg-purple-500/10 text-purple-500 border-purple-500/20",
    };
    return colors[method.toUpperCase()] || "bg-gray-500/10 text-gray-500 border-gray-500/20";
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          Discovered Requests
        </CardTitle>
        <CardDescription>
          All HTTP requests found in the HAR file
        </CardDescription>
      </CardHeader>
      <CardContent>
        {/* No job uploaded yet */}
        {!jobId && (
          <div className="text-center py-12 text-muted-foreground">
            <Database className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-sm">Upload a HAR file to see discovered requests</p>
          </div>
        )}

        {/* Job is processing */}
        {jobId && status?.status === "processing" && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Processing HAR file...</span>
          </div>
        )}

        {/* Job is pending */}
        {jobId && status?.status === "pending" && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Waiting to process...</span>
          </div>
        )}

        {/* Job failed */}
        {jobId && status?.status === "failed" && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>HAR file processing failed</AlertDescription>
          </Alert>
        )}

        {/* Job completed - loading requests */}
        {jobId && status?.status === "completed" && isLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">Loading requests...</span>
          </div>
        )}

        {/* Error loading requests */}
        {jobId && status?.status === "completed" && error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* No requests found */}
        {jobId && status?.status === "completed" && !isLoading && !error && requests.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            No requests found in the HAR file
          </div>
        )}

        {/* Requests table */}
        {jobId && status?.status === "completed" && !isLoading && !error && requests.length > 0 && (
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">
              Found {requests.length} request{requests.length !== 1 ? "s" : ""}
            </div>
            <div className="rounded-md border max-h-[400px] lg:max-h-[calc(100vh-350px)] overflow-y-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-background z-10 border-b">
                  <TableRow>
                    <TableHead className="w-[80px]">Method</TableHead>
                    <TableHead className="w-[150px]">Domain</TableHead>
                    <TableHead>Path</TableHead>
                    <TableHead className="w-[70px]">Status</TableHead>
                    <TableHead className="w-[120px]">Type</TableHead>
                    <TableHead className="w-[90px]">Duration</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requests.map((request) => (
                    <TableRow key={request.id}>
                      <TableCell>
                        <Badge variant="outline" className={getMethodColor(request.method)}>
                          {request.method}
                        </Badge>
                      </TableCell>
                      <TableCell className="font-mono text-xs truncate max-w-[150px]">
                        {request.domain}
                      </TableCell>
                      <TableCell className="font-mono text-xs truncate max-w-[300px]">
                        {request.path}
                      </TableCell>
                      <TableCell>
                        {request.status_code && (
                          <Badge className={getStatusColor(request.status_code)}>
                            {request.status_code}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground truncate max-w-[120px]">
                        {request.content_type || "-"}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {request.duration_ms ? `${request.duration_ms}ms` : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
