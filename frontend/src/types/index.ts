export interface UploadResponse {
  job_id: string;
  message: string;
  status: string;
}

export interface StatusResponse {
  job_id: string;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed";
  total_requests: number;
  upload_timestamp: string;
}

export interface MatchedRequest {
  url: string;
  method: string;
  domain: string;
  path: string;
  status_code: number;
  content_type: string;
}

export interface CurlResponse {
  curl_command: string;
  matched_request: MatchedRequest;
  request_id: number;
  model_used: string;
}

export interface AuthenticationInfo {
  detected: boolean;
  type: string | null;
  header_name: string | null;
  value_pattern: string | null;
}

export interface QueryParam {
  name: string;
  value: string;
}

export interface HeaderParam {
  name: string;
  value: string;
  is_auth: boolean;
}

export interface ParametersInfo {
  query: QueryParam[];
  headers: HeaderParam[];
  body: any;
  body_type: string | null;
}

export interface ResponseInfo {
  status_code: number;
  content_type: string;
  size_bytes: number;
  body_preview: string;
  headers: Record<string, string>;
}

export interface TimingInfo {
  total_ms: number;
  dns_ms?: number;
  connect_ms?: number;
  send_ms?: number;
  wait_ms?: number;
  receive_ms?: number;
}

export interface RequestDetailsResponse {
  request_id: number;
  url: string;
  method: string;
  domain: string;
  path: string;
  authentication: AuthenticationInfo;
  parameters: ParametersInfo;
  response_info: ResponseInfo;
  timing: TimingInfo;
}

export interface ExecutionRequest {
  url: string;
  method: string;
  headers?: Record<string, string>;
}

export interface ExecutionResponse {
  status_code: number;
  status_text: string;
  headers: Record<string, string>;
  body: string;
  size_bytes: number;
}

export interface ExecutionTiming {
  execution_time_ms: number;
  dns_time_ms?: number;
  connect_time_ms?: number;
}

export interface ExecutionError {
  type: string;
  message: string;
  details: string;
  suggestions: string[];
}

export interface ExecuteResponse {
  success: boolean;
  request: ExecutionRequest;
  response?: ExecutionResponse;
  timing: ExecutionTiming;
  error?: ExecutionError;
}

export interface ParameterOverrides {
  queryParams: Record<string, string>;
  headers: Record<string, string>;
  body: string | null;
}

export interface ExecutionSettings {
  timeout: number;
  followRedirects: boolean;
}
