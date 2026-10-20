const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

export function getOwnerId() {
  let id = localStorage.getItem("tokcost_owner_id");
  if (!id) {
    id =
      window.crypto && window.crypto.randomUUID
        ? window.crypto.randomUUID()
        : "u-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("tokcost_owner_id", id);
  }
  return id;
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(BASE + path, options);
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
  return res.json();
}

export function estimate(ownerId, prompt, files) {
  const form = new FormData();
  form.append("prompt", prompt);
  files.forEach((f) => form.append("files", f));
  return request("/estimate", {
    method: "POST",
    headers: { "x-owner-id": ownerId },
    body: form,
  });
}

export function listSessions(ownerId) {
  return request("/sessions", { headers: { "x-owner-id": ownerId } });
}

export function getSession(ownerId, id) {
  return request("/sessions/" + id, { headers: { "x-owner-id": ownerId } });
}

export function deleteSession(ownerId, id) {
  return request("/sessions/" + id, {
    method: "DELETE",
    headers: { "x-owner-id": ownerId },
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
    summary: s.summary || "",
    pricingLastVerified: meta.pricing_last_verified || null,
  };
}
