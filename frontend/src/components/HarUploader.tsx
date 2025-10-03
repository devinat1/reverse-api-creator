"use client";

import { useState, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Upload, FileText, CheckCircle2, XCircle, Loader2, Link } from "lucide-react";
import { api } from "@/lib/api";
import { useJobStatus } from "@/lib/hooks";
import { useAppStore } from "@/lib/store";

export function HarUploader() {
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [url, setUrl] = useState("");

  const { jobId, fileName, totalRequests, setJobId } = useAppStore();
  const { data: status, error: statusError } = useJobStatus(jobId);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];

    if (!file) return;

    if (!file.name.endsWith(".har")) {
      setError("Please upload a .har file");
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      const result = await api.uploadHar(file);
      setJobId(result.job_id, file.name, 0);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }, [setJobId]);

  const handleUrlSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    if (!url.trim()) {
      setError("Please enter a URL");
      return;
    }

    // Basic URL validation
    try {
      new URL(url);
    } catch {
      setError("Please enter a valid URL (including http:// or https://)");
      return;
    }

    setError(null);
    setIsUploading(true);

    try {
      const result = await api.urlToHar(url);
      setJobId(result.job_id, url, 0);
      setUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "URL conversion failed");
    } finally {
      setIsUploading(false);
    }
  }, [url, setJobId]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/json": [".har"] },
    multiple: false,
  });

  const getStatusBadge = () => {
    if (!status) return null;

    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      pending: "secondary",
      processing: "default",
      completed: "default",
      failed: "destructive",
    };

    const icons = {
      pending: <Loader2 className="h-3 w-3 animate-spin" />,
      processing: <Loader2 className="h-3 w-3 animate-spin" />,
      completed: <CheckCircle2 className="h-3 w-3" />,
      failed: <XCircle className="h-3 w-3" />,
    };

    return (
      <Badge variant={variants[status.status]} className="flex items-center gap-1">
        {icons[status.status]}
        {status.status.charAt(0).toUpperCase() + status.status.slice(1)}
      </Badge>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Upload className="h-5 w-5" />
          Step 1: Upload HAR File or Enter URL
        </CardTitle>
        <CardDescription>
          Upload a .har file or enter a URL to capture network traffic
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!jobId ? (
          <Tabs defaultValue="file" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="file" className="flex items-center gap-2">
                <FileText className="h-4 w-4" />
                Upload File
              </TabsTrigger>
              <TabsTrigger value="url" className="flex items-center gap-2">
                <Link className="h-4 w-4" />
                Enter URL
              </TabsTrigger>
            </TabsList>
            <TabsContent value="file" className="mt-4">
              <div
                {...getRootProps()}
                className={`
                  border-2 border-dashed rounded-lg p-8 text-center cursor-pointer
                  transition-colors
                  ${isDragActive ? "border-primary bg-primary/5" : "border-muted-foreground/25"}
                  ${isUploading ? "opacity-50 pointer-events-none" : ""}
                `}
              >
                <input {...getInputProps()} />
                <div className="flex flex-col items-center gap-2">
                  {isUploading ? (
                    <>
                      <Loader2 className="h-10 w-10 animate-spin text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">Processing...</p>
                    </>
                  ) : (
                    <>
                      <FileText className="h-10 w-10 text-muted-foreground" />
                      <p className="text-sm">
                        {isDragActive
                          ? "Drop the .har file here"
                          : "Drag & drop a .har file, or click to browse"}
                      </p>
                    </>
                  )}
                </div>
              </div>
            </TabsContent>
            <TabsContent value="url" className="mt-4">
              <form onSubmit={handleUrlSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Input
                    type="url"
                    placeholder="https://example.com"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    disabled={isUploading}
                    className="w-full"
                  />
                  <p className="text-xs text-muted-foreground">
                    Enter a URL to load it in a browser and capture all network requests
                  </p>
                </div>
                <Button
                  type="submit"
                  disabled={isUploading || !url.trim()}
                  className="w-full"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Converting URL to HAR...
                    </>
                  ) : (
                    <>
                      <Link className="h-4 w-4 mr-2" />
                      Convert URL to HAR
                    </>
                  )}
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        ) : (
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="flex items-center gap-3">
                <FileText className="h-8 w-8 text-primary" />
                <div>
                  <p className="font-medium">{fileName}</p>
                  <p className="text-sm text-muted-foreground">
                    Job ID: {jobId.slice(0, 8)}...
                  </p>
                </div>
              </div>
              {getStatusBadge()}
            </div>

            {status?.status === "completed" && (
              <div className="p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
                <p className="text-sm text-green-800 dark:text-green-200">
                  ✓ Processing complete • {status.total_requests} requests found
                </p>
              </div>
            )}

            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setJobId(null, "", 0);
                setError(null);
              }}
            >
              Upload different file
            </Button>
          </div>
        )}

        {error && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {statusError && (
          <Alert variant="destructive">
            <XCircle className="h-4 w-4" />
            <AlertDescription>Failed to check status</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
