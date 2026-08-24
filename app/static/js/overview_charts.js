(function () {
  const dataEl = document.getElementById("chart-data");
  if (!dataEl) return;

  const daily = JSON.parse(dataEl.dataset.daily || "[]");
  const categoryTrend = JSON.parse(dataEl.dataset.category || "[]");
  const signalTrend = JSON.parse(dataEl.dataset.signal || "[]");
  const categoryTotals = JSON.parse(dataEl.dataset.categoryTotals || "[]");
  const scatterData = JSON.parse(dataEl.dataset.scatter || "[]");

  // Read the current theme's text/border colors so Chart.js labels and grid
  // lines stay legible in dark/ambient mode instead of defaulting to
  // Chart.js's built-in near-black text.
  const styles = getComputedStyle(document.documentElement);
  const textMuted = styles.getPropertyValue("--color-text-muted").trim() || "#5b6472";
  const borderColor = styles.getPropertyValue("--color-border").trim() || "#e2e5ea";
  const accent = styles.getPropertyValue("--color-accent").trim() || "#2454ff";
  const surface = styles.getPropertyValue("--color-surface").trim() || "#ffffff";

  Chart.defaults.color = textMuted;
  Chart.defaults.borderColor = borderColor;
  Chart.defaults.font.family =
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif";

  const SIGNAL_COLORS = {
    critical: "#e0483d",
    high: "#d97a1f",
    medium: "#c9a227",
    low: "#3f9d6e",
    noise: "#8892a0",
  };

  const dailyCanvas = document.getElementById("dailyTrendChart");
  if (dailyCanvas && daily.length) {
    new Chart(dailyCanvas, {
      type: "line",
      data: {
        labels: daily.map((d) => d.date),
        datasets: [
          {
            label: "Changes detected",
            data: daily.map((d) => d.count),
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

  const categoryCanvas = document.getElementById("categoryTrendChart");
  if (categoryCanvas && categoryTrend.length) {
    const dates = [...new Set(categoryTrend.map((d) => d.date))].sort();
    const categories = [...new Set(categoryTrend.map((d) => d.category))];
    const palette = ["#2454ff", "#b3261e", "#b45309", "#8a6d00", "#2f6f4e", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#5b6472", "#c026d3"];

    const datasets = categories.map((cat, idx) => {
      const byDate = Object.fromEntries(
        categoryTrend.filter((d) => d.category === cat).map((d) => [d.date, d.count])
      );
      return {
        label: cat,
        data: dates.map((d) => byDate[d] || 0),
        backgroundColor: palette[idx % palette.length],
      };
    });

    new Chart(categoryCanvas, {
      type: "bar",
      data: { labels: dates, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
        plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 10 } } } },
      },
    });
  }

  const signalCanvas = document.getElementById("signalTrendChart");
  if (signalCanvas && signalTrend.length) {
    const dates = [...new Set(signalTrend.map((d) => d.date))].sort();
    const levels = ["critical", "high", "medium", "low", "noise"];

    const datasets = levels
      .filter((lvl) => signalTrend.some((d) => d.signal_level === lvl))
      .map((lvl) => {
        const byDate = Object.fromEntries(
          signalTrend.filter((d) => d.signal_level === lvl).map((d) => [d.date, d.count])
        );
        return {
          label: lvl,
          data: dates.map((d) => byDate[d] || 0),
          backgroundColor: SIGNAL_COLORS[lvl],
        };
      });

    new Chart(signalCanvas, {
      type: "bar",
      data: { labels: dates, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
        plugins: { legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 10 } } } },
      },
    });
  }

  // --- Category share donut: total mix of change types for the period ---
  const donutCanvas = document.getElementById("categoryDonutChart");
  if (donutCanvas && categoryTotals.length) {
    const palette = ["#2454ff", "#b3261e", "#b45309", "#8a6d00", "#2f6f4e", "#7c3aed", "#0891b2", "#db2777", "#65a30d", "#5b6472", "#c026d3"];
    new Chart(donutCanvas, {
      type: "doughnut",
      data: {
        labels: categoryTotals.map((d) => d.category),
        datasets: [
          {
            data: categoryTotals.map((d) => d.count),
            backgroundColor: categoryTotals.map((_, i) => palette[i % palette.length]),
            borderColor: surface,
            borderWidth: 2,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 10 } } },
        },
      },
    });
  }

  // --- Magnitude vs. signal score scatter: separates "big but irrelevant"
  // changes from "small but pointed" ones -- the two axes measure different
  // things in this model, so their relationship is itself an insight. ---
  const scatterCanvas = document.getElementById("magnitudeScoreScatter");
  if (scatterCanvas && scatterData.length) {
    const levels = ["critical", "high", "medium", "low", "noise"];
    const datasets = levels
      .filter((lvl) => scatterData.some((d) => d.signal_level === lvl))
      .map((lvl) => ({
        label: lvl,
        data: scatterData
          .filter((d) => d.signal_level === lvl)
          .map((d) => ({ x: d.magnitude, y: d.score, category: d.category })),
        backgroundColor: SIGNAL_COLORS[lvl],
        pointRadius: 4,
        pointHoverRadius: 6,
      }));

    new Chart(scatterCanvas, {
      type: "scatter",
      data: { datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { title: { display: true, text: "Change magnitude (%)" }, min: 0, max: 100 },
          y: { title: { display: true, text: "Signal score" }, min: 0, max: 100 },
        },
        plugins: {
          legend: { position: "bottom", labels: { boxWidth: 10, font: { size: 10 } } },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.raw.category}: magnitude ${ctx.raw.x}%, score ${ctx.raw.y}`,
            },
          },
        },
      },
    });
  }
})();
