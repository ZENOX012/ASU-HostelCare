/**
 * ASU HostelCare — Notifications Bell & Polling System
 */

async function updateUnreadBadge() {
  const token = getToken();
  if (!token) return;

  try {
    const data = await apiFetch("/api/notifications/unread-count");
    const badge = document.getElementById("bell-badge");
    if (badge) {
      if (data.unread_count > 0) {
        badge.textContent = data.unread_count > 9 ? "9+" : data.unread_count;
        badge.style.display = "flex";
      } else {
        badge.style.display = "none";
      }
    }
  } catch (err) {
    // Fail silently on polling
  }
}

async function loadNotificationsDropdown() {
  const listEl = document.getElementById("bell-notification-list");
  if (!listEl) return;

  listEl.innerHTML = '<div style="padding:1rem;text-align:center;color:var(--text-muted);">Loading alerts...</div>';

  try {
    const notifs = await apiFetch("/api/notifications");
    if (!notifs || notifs.length === 0) {
      listEl.innerHTML = '<div style="padding:1.5rem;text-align:center;color:var(--text-muted);font-size:0.85rem;">No notifications yet.</div>';
      return;
    }

    listEl.innerHTML = notifs.map((n) => `
      <a href="${n.link || '#'}" class="bell-item ${n.is_read ? '' : 'unread'}" onclick="handleNotificationClick(${n.id}, '${n.link || ''}')">
        <div style="font-weight:600;font-size:0.85rem;color:var(--text-primary);margin-bottom:2px;">${n.title}</div>
        <div style="font-size:0.78rem;color:var(--text-secondary);line-height:1.35;margin-bottom:4px;">${n.message}</div>
        <div style="font-size:0.7rem;color:var(--text-muted);">${formatDate(n.created_at)}</div>
      </a>
    `).join("");
  } catch (err) {
    listEl.innerHTML = '<div style="padding:1rem;text-align:center;color:#f87171;">Failed to load alerts.</div>';
  }
}

async function handleNotificationClick(id, link) {
  try {
    await apiFetch(`/api/notifications/${id}/read`, { method: "POST" });
    updateUnreadBadge();
  } catch (e) {}
  if (link && link !== "#") {
    window.location.href = link;
  }
}

async function markAllNotificationsRead() {
  try {
    await apiFetch("/api/notifications/mark-all-read", { method: "POST" });
    updateUnreadBadge();
    loadNotificationsDropdown();
    showToast("All notifications marked as read.", "success");
  } catch (err) {
    showToast("Could not mark all as read.", "error");
  }
}

// Setup dropdown toggling and polling
document.addEventListener("DOMContentLoaded", () => {
  const bellBtn = document.getElementById("bell-button");
  const bellDropdown = document.getElementById("bell-dropdown");

  if (bellBtn && bellDropdown) {
    bellBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      const isActive = bellDropdown.classList.contains("active");
      if (!isActive) {
        bellDropdown.classList.add("active");
        loadNotificationsDropdown();
      } else {
        bellDropdown.classList.remove("active");
      }
    });

    document.addEventListener("click", (e) => {
      if (!bellDropdown.contains(e.target) && e.target !== bellBtn) {
        bellDropdown.classList.remove("active");
      }
    });

    // Initial badge check & 15-sec auto-poll
    updateUnreadBadge();
    setInterval(updateUnreadBadge, 15000);
  }
});
