(function () {
  const dataEl = document.getElementById("site-chart-data");
  if (!dataEl) return;

  const styles = getComputedStyle(document.documentElement);
  const textMuted = styles.getPropertyValue("--color-text-muted").trim() || "#5b6472";
  const borderColor = styles.getPropertyValue("--color-border").trim() || "#e2e5ea";
  const accent = styles.getPropertyValue("--color-accent").trim() || "#2454ff";
  const surface = styles.getPropertyValue("--color-surface").trim() || "#ffffff";
  Chart.defaults.color = textMuted;
  Chart.defaults.borderColor = borderColor;

  const trend = JSON.parse(dataEl.dataset.trend || "[]");
  const canvas = document.getElementById("siteTrendChart");
  if (canvas && trend.length) {
    new Chart(canvas, {
      type: "line",
      data: {
        labels: trend.map((d) => d.date),
        datasets: [
          {
            label: "Changes",
            data: trend.map((d) => d.count),
            borderColor: accent,
            backgroundColor: accent + "22",
            fill: true,
            tension: 0.25,
            pointRadius: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  // category_counts arrives as a list of [category, count] pairs.
  const categories = JSON.parse(dataEl.dataset.categories || "[]");
  const donutCanvas = document.getElementById("siteCategoryDonut");
  if (donutCanvas && categories.length) {
    const palette = ["#2454ff", "#b3261e", "#b45309", "#8a6d00", "#2f6f4e", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#5b6472", "#c026d3"];
    new Chart(donutCanvas, {
      type: "doughnut",
      data: {
        labels: categories.map((c) => c[0]),
        datasets: [
          {
            data: categories.map((c) => c[1]),
            backgroundColor: categories.map((_, i) => palette[i % palette.length]),
            borderColor: surface,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 10 } } },
        },
      },
    });
  }
})();

