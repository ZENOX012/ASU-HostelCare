/**
 * ASU HostelCare — Authentication & Password Visibility Handlers
 */

// Universal Password Eye Toggle Handler
function setupPasswordToggles() {
  const eyeButtons = document.querySelectorAll(".eye-toggle-btn");
  eyeButtons.forEach((btn) => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      const targetId = this.getAttribute("data-target");
      const input = targetId ? document.getElementById(targetId) : this.previousElementSibling;
      if (!input) return;

      const isPassword = input.type === "password";
      input.type = isPassword ? "text" : "password";

      // Toggle SVG Eye Icon
      if (isPassword) {
        // Show slash / open eye
        this.innerHTML = `
          <svg viewBox="0 0 24 24">
            <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
            <line x1="1" y1="1" x2="23" y2="23"></line>
          </svg>
        `;
        this.setAttribute("title", "Hide password");
      } else {
        // Normal eye
        this.innerHTML = `
          <svg viewBox="0 0 24 24">
            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
        `;
        this.setAttribute("title", "Show password");
      }
    });
  });
}

// Redirect user based on authenticated role
function redirectByRole(role) {
  if (role === "warden") {
    window.location.href = "/admin/dashboard.html";
  } else if (role === "worker") {
    window.location.href = "/worker/dashboard.html";
  } else {
    window.location.href = "/student/dashboard.html";
  }
}

// Attach listeners once DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  setupPasswordToggles();

  // Check for session redirect if already logged in on login or register pages
  const token = getToken();
  const user = getUser();
  const isAuthPage = window.location.pathname.includes("login.html") || window.location.pathname.includes("register.html");
  if (token && user && isAuthPage) {
    redirectByRole(user.role);
  }
});
