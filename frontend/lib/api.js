const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api";

async function handle(res) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.error || `Request failed with status ${res.status}`);
  }
  return data;
}

export function getOrCreateSessionId() {
  if (typeof window === "undefined") return null;
  let sessionId = localStorage.getItem("mechanic_session_id");
  if (!sessionId) {
    sessionId =
      "sess_" + Date.now().toString(36) + Math.random().toString(36).slice(2);
    localStorage.setItem("mechanic_session_id", sessionId);
  }
  return sessionId;
}

export function resetSession() {
  if (typeof window === "undefined") return null;
  localStorage.removeItem("mechanic_session_id");
  return getOrCreateSessionId();
}

export async function sendChatMessage(sessionId, message) {
  const res = await fetch(`${API_BASE_URL}/chat/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  return handle(res);
}

export async function uploadMedia(sessionId, file, mediaType) {
  const formData = new FormData();
  formData.append("session_id", sessionId);
  formData.append("media_type", mediaType);
  formData.append("file", file);

  const res = await fetch(`${API_BASE_URL}/upload/`, {
    method: "POST",
    body: formData,
  });
  return handle(res);
}

export async function requestDiagnosis(conversationId) {
  const res = await fetch(`${API_BASE_URL}/diagnosis/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId }),
  });
  return handle(res);
}

export async function createBooking(payload) {
  const res = await fetch(`${API_BASE_URL}/booking/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return handle(res);
}

export async function getBooking(bookingId) {
  const res = await fetch(`${API_BASE_URL}/booking/${bookingId}/`);
  return handle(res);
}

export async function getConversation(sessionId) {
  const res = await fetch(`${API_BASE_URL}/conversation/${sessionId}/`);
  return handle(res);
}
