(function () {
  // Skip entirely on touch/coarse-pointer devices -- there's no cursor to glow.
  if (window.matchMedia && window.matchMedia("(hover: none), (pointer: coarse)").matches) {
    return;
  }

  const glow = document.getElementById("cursor-glow");
  if (!glow) return;

  let targetX = window.innerWidth / 2;
  let targetY = window.innerHeight / 2;
  let currentX = targetX;
  let currentY = targetY;
  let raf = null;

  function loop() {
    // Lerp toward the pointer position so the glow trails slightly rather
    // than snapping instantly -- a small touch that reads as "designed"
    // rather than a raw mouse-position dump.
    currentX += (targetX - currentX) * 0.18;
    currentY += (targetY - currentY) * 0.18;
    glow.style.transform = `translate(${currentX}px, ${currentY}px)`;
    raf = requestAnimationFrame(loop);
  }

  document.addEventListener("mousemove", function (e) {
    targetX = e.clientX;
    targetY = e.clientY;
    glow.classList.add("visible");
    if (!raf) raf = requestAnimationFrame(loop);
  });

  document.addEventListener("mouseleave", function () {
    glow.classList.remove("visible");
  });

  const HOVER_SELECTOR = "a, button, .card, .kpi-card, .alert-row, select, input, .theme-btn";

  document.addEventListener("mouseover", function (e) {
    if (e.target.closest && e.target.closest(HOVER_SELECTOR)) {
      glow.classList.add("hovering");
    }
  });
  document.addEventListener("mouseout", function (e) {
    if (e.target.closest && e.target.closest(HOVER_SELECTOR)) {
      glow.classList.remove("hovering");
    }
  });
})();
