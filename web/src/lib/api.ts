import type { AnalysisResponse, HistoryEntry } from "@/lib/types";
import { createClient } from "@/lib/supabase/client";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** An error carrying the backend's own message, so the UI can show something
 *  more useful than "Request failed". */
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function toApiError(response: Response): Promise<ApiError> {
  let detail = response.statusText;
  try {
    const body = await response.json();
    // FastAPI puts the message in `detail`; validation errors make it an array.
    if (typeof body.detail === "string") detail = body.detail;
    else if (Array.isArray(body.detail) && body.detail[0]?.msg)
      detail = body.detail[0].msg;
  } catch {
    // Non-JSON error body — keep the status text.
  }
  if (response.status === 401) {
    detail = "Your session expired. Sign in again to continue.";
  }
  return new ApiError(detail, response.status);
}

/** The backend authenticates with the Supabase access token, not a cookie. */
async function authHeaders(): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session?.access_token) {
    throw new ApiError("You need to be signed in.", 401);
  }
  return { Authorization: `Bearer ${session.access_token}` };
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: { ...(await authHeaders()), ...init.headers },
  });
  if (!response.ok) throw await toApiError(response);
  return response.json() as Promise<T>;
}

export async function analyzeResume(
  file: File,
  jobDescription: string,
): Promise<AnalysisResponse> {
  const form = new FormData();
  form.append("resume", file);
  form.append("job_description", jobDescription);

  // No Content-Type header — the browser sets the multipart boundary itself.
  return request<AnalysisResponse>("/api/v1/analyze-resume", {
    method: "POST",
    body: form,
  });
}

export async function getHistory(): Promise<HistoryEntry[]> {
  return request<HistoryEntry[]>("/api/v1/history");
}

export async function deleteHistoryEntry(id: string): Promise<void> {
  await request(`/api/v1/history/${id}`, { method: "DELETE" });
}

/** Downloads a PDF report and hands back a blob for the caller to save. */
export async function downloadReport(
  analysis: AnalysisResponse,
): Promise<Blob> {
  const response = await fetch(`${BASE_URL}/api/v1/reports/pdf`, {
    method: "POST",
    headers: {
      ...(await authHeaders()),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(analysis),
  });
  if (!response.ok) throw await toApiError(response);
  return response.blob();
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BASE_URL}/api/v1/health`, {
      cache: "no-store",
    });
    return response.ok;
  } catch {
    return false;
  }
}
