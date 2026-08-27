(function () {
  const STORAGE_KEY = "changelens-cookie-consent"; // "accepted" | "declined"
  const banner = document.getElementById("cookie-consent");
  if (!banner) return;

  function loadAnalytics() {
    const gaId = window.GA_MEASUREMENT_ID;
    if (!gaId) return; // Analytics not configured for this deployment -- nothing to load.
    if (document.getElementById("ga4-script")) return; // already loaded

    const script = document.createElement("script");
    script.id = "ga4-script";
    script.async = true;
    script.src = "https://www.googletagmanager.com/gtag/js?id=" + encodeURIComponent(gaId);
    document.head.appendChild(script);

    window.dataLayer = window.dataLayer || [];
    function gtag() {
      window.dataLayer.push(arguments);
    }
    gtag("js", new Date());
    gtag("config", gaId, { anonymize_ip: true });
    window.gtag = gtag;
  }

  let consent;
  try {
    consent = localStorage.getItem(STORAGE_KEY);
  } catch (e) {
    consent = null;
  }

  if (consent === "accepted") {
    loadAnalytics();
  } else if (consent === null) {
    // No decision recorded yet -- show the banner. If GA isn't configured at
    // all, there's nothing to consent to, so skip showing it entirely.
    if (window.GA_MEASUREMENT_ID) {
      banner.hidden = false;
    }
  }
  // consent === "declined": do nothing, banner stays hidden, no analytics load.

  document.addEventListener("DOMContentLoaded", function () {
    const acceptBtn = document.getElementById("cookie-accept");
    const declineBtn = document.getElementById("cookie-decline");

    if (acceptBtn) {
      acceptBtn.addEventListener("click", function () {
        try {
          localStorage.setItem(STORAGE_KEY, "accepted");
        } catch (e) {}
        loadAnalytics();
        banner.hidden = true;
      });
    }
    if (declineBtn) {
      declineBtn.addEventListener("click", function () {
        try {
          localStorage.setItem(STORAGE_KEY, "declined");
        } catch (e) {}
        banner.hidden = true;
      });
    }
  });
})();
