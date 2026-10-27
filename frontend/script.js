const API = window.location.port === "5000" ? "/api" : "http://127.0.0.1:5000/api";
const TOKEN_KEY = "zt_token";
const $ = (id) => document.getElementById(id);

let mode = "login"; // "login" | "register"
let currentUser = null;
let toastTimer = null;

// ---------- Helpers ----------
function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("show"), 3000);
}

function setConnection(online) {
  $("connectionText").textContent = online ? "API connected" : "API unreachable";
}

/**
 * Fetch wrapper. Returns { status, ok, data }.
 * Only a 401 on an authenticated call logs the user out.
 * 403 (forbidden) and network errors never do.
 */
async function api(path, { method = "GET", body, auth = true } = {}) {
  const headers = { "Content-Type": "application/json" };
  const token = localStorage.getItem(TOKEN_KEY);
  if (auth && token) headers.Authorization = `Bearer ${token}`;

  let res;
  try {
    res = await fetch(API + path, {
      method,
      headers,
      body: body ? JSON.stringify(body) : undefined
    });
  } catch (err) {
    setConnection(false);
    throw new Error("Cannot reach the server");
  }
  setConnection(true);

  let data = null;
  try { data = await res.json(); } catch (_) { /* empty body */ }

  if (res.status === 401 && auth) {
    logout("Session expired. Please sign in again.");
  }
  return { status: res.status, ok: res.ok, data };
}

// ---------- Auth screen ----------
function setMode(newMode) {
  mode = newMode;
  const isLogin = mode === "login";
  $("authEyebrow").textContent = isLogin ? "WELCOME BACK" : "GET STARTED";
  $("authTitle").textContent = isLogin ? "Sign in to your account" : "Create your account";
  $("authDescription").textContent = isLogin
    ? "Enter your credentials to access the security dashboard."
    : "Choose a username and password to register.";
  $("authSubmit").innerHTML = isLogin ? "Sign in <span>→</span>" : "Create account <span>→</span>";
  $("password").autocomplete = isLogin ? "current-password" : "new-password";
  $("switchText").firstChild.textContent = isLogin
    ? "Don't have an account? "
    : "Already have an account? ";
  $("switchAuth").textContent = isLogin ? "Create account" : "Sign in";
  showAuthMessage("");
}

function showAuthMessage(text) {
  $("authMessage").textContent = text;
}

$("switchAuth").addEventListener("click", () => setMode(mode === "login" ? "register" : "login"));

$("authForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = $("username").value.trim();
  const password = $("password").value;
  const button = $("authSubmit");

  button.disabled = true;
  showAuthMessage("");
  try {
    const { ok, data } = await api(mode === "login" ? "/login" : "/register", {
      method: "POST",
      body: { username, password },
      auth: false
    });
    if (!ok) {
      showAuthMessage((data && data.error) || "Something went wrong");
      return;
    }
    localStorage.setItem(TOKEN_KEY, data.token);
    $("authForm").reset();
    showApp(data.user);
  } catch (err) {
    showAuthMessage(err.message);
  } finally {
    button.disabled = false;
  }
});

// ---------- Screens ----------
function showAuth(message = "") {
  currentUser = null;
  $("appScreen").classList.add("hidden");
  $("authScreen").classList.remove("hidden");
  setMode("login");
  showAuthMessage(message);
}

function showApp(user) {
  currentUser = user;
  const isAdmin = user.role === "admin";
  const initial = user.username.charAt(0).toUpperCase();

  $("welcomeName").textContent = user.username;
  $("profileName").textContent = user.username;
  $("profileRole").textContent = user.role.toUpperCase();
  $("roleCount").textContent = user.role.toUpperCase();
  $("avatar").textContent = initial;
  $("topAvatar").textContent = initial;
  document.querySelectorAll(".admin-only").forEach((el) => el.classList.toggle("hidden", !isAdmin));

  $("authScreen").classList.add("hidden");
  $("appScreen").classList.remove("hidden");
  navigate("overview");
  loadStats();
}

function logout(message = "") {
  localStorage.removeItem(TOKEN_KEY);
  showAuth(message);
}

$("logoutButton").addEventListener("click", () => logout("You have been signed out."));

// ---------- Navigation ----------
const PAGES = {
  overview: { section: "overviewPage", title: "Security overview", crumb: "Overview" },
  services: { section: "servicesPage", title: "Microservices", crumb: "Microservices" },
  logs: { section: "logsPage", title: "Audit logs", crumb: "Audit logs" }
};

function navigate(page) {
  if (page === "logs" && (!currentUser || currentUser.role !== "admin")) {
    toast("Audit logs are admin only");
    page = "overview";
  }
  const info = PAGES[page];
  Object.values(PAGES).forEach((p) => $(p.section).classList.add("hidden"));
  $(info.section).classList.remove("hidden");
  $("pageTitle").textContent = info.title;
  $("breadcrumbPage").textContent = info.crumb;
  document.querySelectorAll(".nav-item").forEach((btn) =>
    btn.classList.toggle("active", btn.dataset.page === page)
  );
  if (page === "logs") loadLogs();
}

document.querySelectorAll(".nav-item").forEach((btn) =>
  btn.addEventListener("click", () => navigate(btn.dataset.page))
);

// ---------- Stats ----------
async function loadStats() {
  try {
    const { ok, data } = await api("/stats");
    if (ok) {
      $("allowedCount").textContent = String(data.allowed).padStart(2, "0");
      $("deniedCount").textContent = String(data.denied).padStart(2, "0");
    }
  } catch (err) {
    toast(err.message);
  }
}

$("refreshButton").addEventListener("click", async () => {
  await loadStats();
  toast("Summary refreshed");
});

// ---------- Service tests ----------
document.querySelectorAll(".service-action").forEach((btn) =>
  btn.addEventListener("click", () => callService(btn))
);

async function callService(btn) {
  const service = btn.dataset.service; // "users" | "orders"
  const onServicesPage = btn.closest("section").id === "servicesPage";
  const panel = $(onServicesPage ? "serviceResultPanel" : "resultPanel");
  const title = $(onServicesPage ? "serviceResultTitle" : "resultTitle");
  const output = $(onServicesPage ? "serviceResultOutput" : "resultOutput");

  btn.disabled = true;
  try {
    const { status, ok, data } = await api(`/services/${service}`);
    title.textContent = `${service === "users" ? "User" : "Order"} Service · ${ok ? "ALLOWED" : "DENIED"}`;
    output.textContent = `HTTP ${status}\n\n${JSON.stringify(data, null, 2)}`;
    panel.classList.remove("hidden");
    loadStats();
  } catch (err) {
    toast(err.message);
  } finally {
    btn.disabled = false;
  }
}

$("closeResult").addEventListener("click", () => $("resultPanel").classList.add("hidden"));
$("closeServiceResult").addEventListener("click", () => $("serviceResultPanel").classList.add("hidden"));

// ---------- Audit logs ----------
function cell(text, className) {
  const td = document.createElement("td");
  td.textContent = text;
  if (className) td.className = className;
  return td;
}

function messageRow(text) {
  const tr = document.createElement("tr");
  const td = cell(text, "empty-cell");
  td.colSpan = 5;
  tr.appendChild(td);
  return tr;
}

async function loadLogs() {
  const body = $("logsBody");
  try {
    const { ok, status, data } = await api("/logs");
    body.innerHTML = "";
    if (!ok) {
      body.appendChild(messageRow(status === 403 ? "Admin access required" : "Could not load logs"));
      return;
    }
    if (data.logs.length === 0) {
      body.appendChild(messageRow("No access events yet"));
      return;
    }
    data.logs.forEach((log) => {
      const tr = document.createElement("tr");
      tr.appendChild(cell(log.identity));
      tr.appendChild(cell(log.service));
      tr.appendChild(cell(log.decision, `decision ${log.decision.toLowerCase()}`));
      tr.appendChild(cell(log.reason));
      tr.appendChild(cell(new Date(log.time).toLocaleString()));
      body.appendChild(tr);
    });
  } catch (err) {
    toast(err.message);
  }
}

$("logsRefreshButton").addEventListener("click", loadLogs);

// ---------- Startup: restore session ----------
(async function init() {
  setMode("login");
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return;
  try {
    const { ok, data } = await api("/me");
    if (ok) showApp(data.user);
    // on 401, api() already called logout()
  } catch (err) {
    showAuth(err.message);
  }
})();