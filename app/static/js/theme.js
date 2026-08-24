(function () {
  const STORAGE_KEY = "changelens-theme";
  const root = document.documentElement;

  function applyTheme(theme) {
    root.setAttribute("data-theme", theme);
    document.querySelectorAll(".theme-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.themeChoice === theme);
    });
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch (e) {
      /* localStorage may be unavailable (e.g. private mode) -- theme just
         won't persist across reloads, which is a harmless degradation. */
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const current = root.getAttribute("data-theme") || "light";
    applyTheme(current);

    document.querySelectorAll(".theme-btn").forEach((btn) => {
      btn.addEventListener("click", function () {
        applyTheme(btn.dataset.themeChoice);
      });
    });
  });
})();
