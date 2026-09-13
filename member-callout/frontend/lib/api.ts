const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8080";

const TOKEN_KEY = "crewlink_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  window.localStorage.removeItem(TOKEN_KEY);
}

// The API reports problems in three different shapes depending on where they
// come from: {"detail": "..."} from views, {"non_field_errors": [...]} from
// serializer-level validation, and {"field": [...]} from field validation.
function messageFrom(body: unknown, status: number): string {
  if (body && typeof body === "object") {
    const record = body as Record<string, unknown>;
    if (typeof record.detail === "string") return record.detail;
    if (Array.isArray(record.non_field_errors)) return record.non_field_errors.join(" ");
    const first = Object.entries(record)[0];
    if (first && Array.isArray(first[1])) return `${first[0]}: ${first[1].join(" ")}`;
  }
  return `Request failed (${status})`;
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, body: unknown) {
    super(messageFrom(body, status));
    this.status = status;
  }
}

export async function api<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown; token?: string | null } = {},
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;

  // No credentials/cookies: the API sets CORS_ALLOW_CREDENTIALS = False, so the
  // bearer header is the only way in.
  const res = await fetch(`${API_BASE}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
  });

  // A malformed UUID in the path never reaches a view, so Django answers with an
  // HTML 404 page rather than JSON. Parsing has to tolerate that.
  const text = await res.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = { detail: `Unexpected response (${res.status})` };
    }
  }

  if (!res.ok) throw new ApiError(res.status, data);
  return data as T;
}

// Reads the claims the login endpoint puts in the token (full_name, role,
// local_id) so the screen can greet the leader. Display only -- the signature is
// never checked here, the server does that on every request.
export function decodeJwt(token: string): Record<string, string> {
  const payload = token.split(".")[1];
  const json = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
  return JSON.parse(json);
}
