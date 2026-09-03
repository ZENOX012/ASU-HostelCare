/**
 * ASU HostelCare — Common Utilities & Formatting
 */

// Anti-Inspect, Anti-F12, Anti-RightClick Source Shield
(function() {
  document.addEventListener('contextmenu', function (e) {
    const tag = e.target && e.target.tagName ? e.target.tagName.toLowerCase() : '';
    if (tag === 'input' || tag === 'textarea') return true;
    e.preventDefault();
    return false;
  }, false);

  document.addEventListener('keydown', function (e) {
    if (e.key === 'F12' || e.keyCode === 123) { e.preventDefault(); return false; }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'I' || e.key === 'i' || e.keyCode === 73)) { e.preventDefault(); return false; }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'J' || e.key === 'j' || e.keyCode === 74)) { e.preventDefault(); return false; }
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && (e.key === 'C' || e.key === 'c' || e.keyCode === 67)) { e.preventDefault(); return false; }
    if ((e.ctrlKey || e.metaKey) && (e.key === 'U' || e.key === 'u' || e.keyCode === 85)) { e.preventDefault(); return false; }
    if ((e.ctrlKey || e.metaKey) && (e.key === 'S' || e.key === 's' || e.keyCode === 83)) { e.preventDefault(); return false; }
  }, false);
})();

function showToast(message, type = "info") {
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button style="background:none;border:none;color:#fff;cursor:pointer;margin-left:12px;font-weight:bold;" onclick="this.parentElement.remove()">✕</button>
  `;

  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    toast.style.transition = "all 0.3s ease";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

function formatDate(isoString) {
  if (!isoString) return "—";
  const date = new Date(isoString);
  return date.toLocaleString("en-IN", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function getPriorityBadge(priority) {
  const p = (priority || "Medium").toLowerCase();
  let badgeClass = "badge-medium";
  if (p === "emergency") badgeClass = "badge-emergency";
  else if (p === "high") badgeClass = "badge-high";
  else if (p === "low") badgeClass = "badge-low";

  return `<span class="badge ${badgeClass}">${priority || "Medium"}</span>`;
}

function getStatusBadge(status) {
  const s = (status || "Submitted").toLowerCase();
  let badgeClass = "badge-status-submitted";
  if (s.includes("assigned")) badgeClass = "badge-status-assigned";
  else if (s.includes("progress")) badgeClass = "badge-status-inprogress";
  else if (s.includes("awaiting")) badgeClass = "badge-status-awaiting";
  else if (s.includes("resolved")) badgeClass = "badge-status-resolved";
  else if (s.includes("reject")) badgeClass = "badge-status-rejected";

  return `<span class="badge ${badgeClass}">${status || "Submitted"}</span>`;
}

function openModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.add("active");
}

function closeModal(id) {
  const modal = document.getElementById(id);
  if (modal) modal.classList.remove("active");
}

function renderTopbar() {
  const user = getUser();
  if (!user) return;

  const nameEl = document.getElementById("topbar-user-name");
  const roomEl = document.getElementById("topbar-user-room");
  const avatarEl = document.getElementById("topbar-user-avatar");

  if (nameEl) nameEl.textContent = user.full_name;
  if (roomEl) {
    if (user.role === "student") {
      roomEl.textContent = `Block ${user.hostel_block || "—"}, Rm ${user.room_number || "—"}`;
    } else if (user.role === "worker") {
      roomEl.textContent = `${user.worker_specialization || "Staff"} • ${user.worker_shift || "Day"} Shift`;
    } else if (user.role === "admin") {
      roomEl.textContent = "Super Admin • Central Administration";
    } else {
      roomEl.textContent = "Hostel Warden • Residential Services";
    }
  }
  if (avatarEl && user.profile_photo) {
    avatarEl.src = user.profile_photo;
  }
}

// Global modal backdrop close
document.addEventListener("click", (e) => {
  if (e.target.classList && e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("active");
  }
});
