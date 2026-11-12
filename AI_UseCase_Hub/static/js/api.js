// Einziger Zugang zur API. Schreibende Aufrufe tragen das Sitzungs-Token.

const token = document.querySelector('meta[name="hub-token"]').content;
const listeners = new Set();

export class ApiError extends Error {
  constructor(code, message, status, fields) {
    super(message);
    this.code = code;
    this.status = status;
    this.fields = fields || {};
  }
}

// Meldet "offline" (Hub antwortet nicht) und "token" (Hub wurde neu gestartet).
export function onConnectionProblem(listener) {
  listeners.add(listener);
}

function notify(kind) {
  for (const listener of listeners) listener(kind);
}

export async function api(method, path, body) {
  const options = { method, headers: {}, cache: "no-store" };
  if (method !== "GET") {
    options.headers["Content-Type"] = "application/json";
    options.headers["X-Hub-Token"] = token;
    options.body = JSON.stringify(body || {});
  }
  let response;
  try {
    response = await fetch(path, options);
  } catch (error) {
    notify("offline");
    throw new ApiError("offline", "Der Hub antwortet nicht.", 0);
  }
  let data = null;
  try {
    data = await response.json();
  } catch (error) {
    data = null;
  }
  if (!response.ok) {
    const info = (data && data.error) || {};
    if (info.code === "token") notify("token");
    throw new ApiError(info.code || "http", info.message || `Fehler ${response.status}`, response.status, info.fields);
  }
  return data;
}
