/**
 * ASU HostelCare — API Client & Session Manager
 */

const API_BASE = "";

function getToken() {
  return localStorage.getItem("asu_token");
}

function setToken(token) {
  localStorage.setItem("asu_token", token);
}

function getUser() {
  const userStr = localStorage.getItem("asu_user");
  try {
    return userStr ? JSON.parse(userStr) : null;
  } catch (e) {
    return null;
  }
}

function setUser(user) {
  localStorage.setItem("asu_user", JSON.stringify(user));
}

function logout() {
  localStorage.removeItem("asu_token");
  localStorage.removeItem("asu_user");
  window.location.href = "/login.html";
}

async function apiFetch(endpoint, options = {}) {
  const headers = options.headers || {};
  const token = getToken();

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  // Set default JSON Content-Type if body is stringified JSON and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  options.headers = headers;

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, options);

    if (res.status === 401) {
      // Don't auto-redirect if on login or public track page
      if (!window.location.pathname.includes("login") && 
          !window.location.pathname.includes("register") && 
          !window.location.pathname.includes("track") &&
          window.location.pathname !== "/") {
        localStorage.removeItem("asu_token");
        localStorage.removeItem("asu_user");
        window.location.href = "/login.html?expired=1";
      }
    }

    const contentType = res.headers.get("content-type") || "";
    let data;
    if (contentType.includes("application/json")) {
      data = await res.json();
    } else {
      data = await res.text();
    }

    if (!res.ok) {
      const errorMsg = data && data.detail ? data.detail : `Server error (${res.status})`;
      throw new Error(errorMsg);
    }

    return data;
  } catch (err) {
    console.error("API Request failed:", err);
    throw err;
  }
}
