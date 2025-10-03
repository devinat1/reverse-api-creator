"use client";

import { useEffect, useState, useRef } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Loader2, AlertCircle, Database } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { useJobStatus } from "@/lib/hooks";
import { api } from "@/lib/api";
import type { RequestListItem } from "@/types";

type ColumnKey = "method" | "domain" | "path" | "status" | "type" | "duration";

interface ColumnWidths {
  method: number;
  domain: number;
  path: number;
  status: number;
  type: number;
  duration: number;
}

export function RequestsTable() {
  const { jobId } = useAppStore();
  const { data: status } = useJobStatus(jobId);
  const [requests, setRequests] = useState<RequestListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Column widths state
  const [columnWidths, setColumnWidths] = useState<ColumnWidths>({
    method: 80,
    domain: 150,
    path: 300,
    status: 70,
    type: 120,
    duration: 90,
  });

  const [resizingColumn, setResizingColumn] = useState<ColumnKey | null>(null);
  const [startX, setStartX] = useState(0);
  const [startWidth, setStartWidth] = useState(0);

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

  // Mouse event handlers for column resizing
  const handleMouseDown = (column: ColumnKey, e: React.MouseEvent) => {
    e.preventDefault();
    setResizingColumn(column);
    setStartX(e.clientX);
    setStartWidth(columnWidths[column]);
  };

  useEffect(() => {
    if (!resizingColumn) return;

    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - startX;
      const newWidth = Math.max(50, startWidth + diff); // Minimum width of 50px
      setColumnWidths((prev) => ({
        ...prev,
        [resizingColumn]: newWidth,
      }));
    };

    const handleMouseUp = () => {
      setResizingColumn(null);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [resizingColumn, startX, startWidth]);

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
          All requests found in the HAR file
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
                    <TableHead
                      className="relative group select-none"
                      style={{ width: columnWidths.method }}
                    >
                      Method
                      <div
                        className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/50 group-hover:bg-primary/30"
                        onMouseDown={(e) => handleMouseDown("method", e)}
                      />
                    </TableHead>
                    <TableHead
                      className="relative group select-none"
                      style={{ width: columnWidths.domain }}
                    >
                      Domain
                      <div
                        className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/50 group-hover:bg-primary/30"
                        onMouseDown={(e) => handleMouseDown("domain", e)}
                      />
                    </TableHead>
                    <TableHead
                      className="relative group select-none"
                      style={{ width: columnWidths.path }}
                    >
                      Path
                      <div
                        className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/50 group-hover:bg-primary/30"
                        onMouseDown={(e) => handleMouseDown("path", e)}
                      />
                    </TableHead>
                    <TableHead
                      className="relative group select-none"
                      style={{ width: columnWidths.status }}
                    >
                      Status
                      <div
                        className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/50 group-hover:bg-primary/30"
                        onMouseDown={(e) => handleMouseDown("status", e)}
                      />
                    </TableHead>
                    <TableHead
                      className="relative group select-none"
                      style={{ width: columnWidths.type }}
                    >
                      Type
                      <div
                        className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/50 group-hover:bg-primary/30"
                        onMouseDown={(e) => handleMouseDown("type", e)}
                      />
                    </TableHead>
                    <TableHead
                      className="relative group select-none"
                      style={{ width: columnWidths.duration }}
                    >
                      Duration
                      <div
                        className="absolute right-0 top-0 h-full w-1 cursor-col-resize hover:bg-primary/50 group-hover:bg-primary/30"
                        onMouseDown={(e) => handleMouseDown("duration", e)}
                      />
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {requests.map((request) => (
                    <TableRow key={request.id}>
                      <TableCell style={{ width: columnWidths.method }}>
                        <Badge variant="outline" className={getMethodColor(request.method)}>
                          {request.method}
                        </Badge>
                      </TableCell>
                      <TableCell
                        className="font-mono text-xs truncate"
                        style={{ width: columnWidths.domain, maxWidth: columnWidths.domain }}
                      >
                        {request.domain}
                      </TableCell>
                      <TableCell
                        className="font-mono text-xs truncate"
                        style={{ width: columnWidths.path, maxWidth: columnWidths.path }}
                      >
                        {request.path}
                      </TableCell>
                      <TableCell style={{ width: columnWidths.status }}>
                        {request.status_code && (
                          <Badge className={getStatusColor(request.status_code)}>
                            {request.status_code}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell
                        className="text-xs text-muted-foreground truncate"
                        style={{ width: columnWidths.type, maxWidth: columnWidths.type }}
                      >
                        {request.content_type || "-"}
                      </TableCell>
                      <TableCell
                        className="text-xs text-muted-foreground"
                        style={{ width: columnWidths.duration }}
                      >
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
