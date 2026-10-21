// Must match OAUTH_REDIRECT_URI host (Option B: 127.0.0.1 everywhere).
const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const defaultFetch = { credentials: "include" };

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, { ...defaultFetch, ...options });
  } catch (e) {
    throw new Error(
      "Cannot reach the TokCost server. Check that the backend is running.",
    );
  }
  if (!res.ok) {
    let detail = "Request failed (" + res.status + ")";
    try {
      const body = await res.json();
      if (typeof body.detail === "string") detail = body.detail;
      else if (Array.isArray(body.detail))
        detail = body.detail.map((d) => d.msg).join(", ");
    } catch (e) {
      /* keep default message */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export function getLoginUrl() {
  return BASE + "/auth/google/login";
}

export function authMe() {
  return request("/auth/me");
}

export function logout() {
  return request("/auth/logout", { method: "POST" });
}

export function estimate(prompt, files, contextMessages) {
  const form = new FormData();
  form.append("prompt", prompt);
  files.forEach((f) => form.append("files", f));
  if (contextMessages && contextMessages.length > 0) {
    form.append("context_json", JSON.stringify(contextMessages));
  }
  return request("/estimate", { method: "POST", body: form });
}

export function listSessions() {
  return request("/sessions");
}

export function getSession(id) {
  return request("/sessions/" + id);
}

export function updateSession(id, { title, pinned } = {}) {
  const body = {};
  if (title !== undefined) body.title = title;
  if (pinned !== undefined) body.pinned = pinned;
  return request("/sessions/" + id, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function renameSession(id, title) {
  return updateSession(id, { title });
}

export function pinSession(id, pinned) {
  return updateSession(id, { pinned });
}

export function deleteSession(id) {
  return request("/sessions/" + id, { method: "DELETE" });
}

export function adminStats() {
  return request("/admin/stats");
}

export function adminListUsers() {
  return request("/admin/users");
}

export function adminSetRole(userId, role) {
  return request("/admin/users/" + userId, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ role }),
  });
}

export function viewFromEstimate(data, prompt, files) {
  return {
    sessionId: data.session_id,
    saved: data.saved,
    userMessage: {
      text: prompt,
      files: files.map((f) => ({ filename: f.name })),
    },
    promptTokens: data.prompt.tokens,
    compression: data.compression,
    files: data.files,
    totals: data.totals,
    platforms: data.platforms,
    recommended: data.recommended,
    reason: data.reason,
    alternatives: data.alternatives || [],
    summary: data.summary,
    pricingLastVerified: data.pricing_last_verified,
  };
}

export function viewFromSession(s) {
  const meta = s.meta || {};
  const fallbackCompression = {
    compressed: s.compressed_prompt || "",
    raw_tokens: 0,
    compressed_tokens: 0,
    saved_tokens: 0,
    percent: 0,
    summary: "",
    context_messages_used: 0,
    retained_notes: [],
  };
  return {
    sessionId: s.id,
    saved: true,
    userMessage: {
      text: s.prompt_text === "(files only)" ? "" : s.prompt_text,
      files: (s.files || []).map((f) => ({ filename: f.filename })),
    },
    promptTokens: meta.prompt_tokens || {},
    compression: meta.compression || fallbackCompression,
    files: s.files || [],
    totals: meta.totals || {},
    platforms: meta.platforms || [],
    recommended: s.recommended_platform,
    reason: meta.reason || "",
    alternatives: meta.alternatives || [],
    summary: s.summary || "",
    pricingLastVerified: meta.pricing_last_verified || null,
  };
}
