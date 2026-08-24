(function () {
  document.addEventListener("DOMContentLoaded", function () {
    // Stagger the entrance of top-level cards/KPI tiles so the page feels
    // like it's assembling itself rather than popping in all at once.
    const staggerTargets = document.querySelectorAll(
      ".kpi-card, .main > .card, .grid-2 > .card, .alert-row"
    );
    staggerTargets.forEach((el, i) => {
      el.style.setProperty("--stagger-index", Math.min(i, 14));
      el.classList.add("stagger-in");
    });

    // Animate KPI numbers counting up from 0 on first paint. Only applies to
    // plain integers/decimals -- text values (like organization names) are
    // left untouched.
    document.querySelectorAll(".kpi-value").forEach((el) => {
      const raw = el.textContent.trim();
      const match = raw.match(/^-?\d+(\.\d+)?$/);
      if (!match) return;

      const target = parseFloat(raw);
      const isDecimal = raw.includes(".");
      const duration = 700;
      const start = performance.now();

      function tick(now) {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
        const value = target * eased;
        el.textContent = isDecimal ? value.toFixed(1) : Math.round(value).toString();
        if (progress < 1) requestAnimationFrame(tick);
        else el.textContent = raw; // land exactly on the original formatted value
      }
      requestAnimationFrame(tick);
    });
  });
})();
