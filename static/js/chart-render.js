(function () {
  const data = window.TRACK_HISTORY || { spotify: [], youtube: [], soundcloud: [] };
  const chartRoot = document.getElementById("historyChart");
  if (!chartRoot) return;

  const colors = {
    spotify: "#1db954",
    youtube: "#ff3b30",
    soundcloud: "#ff7a18",
  };
  const labels = {
    spotify: "اسپاتیفای",
    youtube: "یوتیوب",
    soundcloud: "ساندکلود",
  };
  const platformOrder = ["spotify", "youtube", "soundcloud"];
  const filterButtons = Array.from(document.querySelectorAll(".history-chip"));
  let selectedPlatform = "all";

  function getDailySeries(platform) {
    const points = (data[platform] || []).slice().sort((a, b) => a.date.localeCompare(b.date));
    return points.map((point) => ({
      date: point.date,
      value: Number(point.value ?? point.views ?? point.total ?? 0) || 0,
      label: point.label || point.date,
      increase: Number(point.increase ?? 0) || 0,
      total: Number(point.total ?? 0) || 0,
    }));
  }

  function formatDayLabel(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
      return value;
    }
    return new Intl.DateTimeFormat("en", {
      month: "short",
      day: "numeric",
      year: "2-digit",
    }).format(date);
  }

  function escapeTooltipText(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderChart() {
    const selectedPlatforms = selectedPlatform === "all" ? platformOrder : [selectedPlatform];
    const allDates = new Set();

    selectedPlatforms.forEach((platform) => {
      getDailySeries(platform).forEach((point) => allDates.add(point.date));
    });

    const sortedDates = Array.from(allDates).sort();
    if (!sortedDates.length) {
      chartRoot.innerHTML = '<div class="history-empty">هنوز داده‌ای برای نمایش وجود ندارد.</div>';
      return;
    }

    const datasets = selectedPlatforms.map((platform) => {
      const series = getDailySeries(platform);
      const map = Object.fromEntries(series.map((point) => [point.date, point]));
      return {
        label: labels[platform],
        color: colors[platform],
        points: sortedDates.map((date) => ({
          date,
          value: Number(map[date]?.value ?? 0),
          increase: Number(map[date]?.increase ?? 0),
          total: Number(map[date]?.total ?? 0),
          label: map[date]?.label || date,
        })),
      };
    });

    const maxValue = Math.max(1, ...datasets.flatMap((dataset) => dataset.points.map((point) => point.value)));
    const width = 960;
    const height = 300;
    const padding = { top: 24, right: 24, bottom: 46, left: 48 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const stepX = sortedDates.length > 1 ? chartWidth / (sortedDates.length - 1) : chartWidth;
    const yAxisLevels = [];
    const primarySeries = datasets[0]?.points || [];
    const lastPoint = primarySeries[primarySeries.length - 1];
    const firstPoint = primarySeries[0];
    const summaryValue = lastPoint ? Number(lastPoint.value || 0) : 0;
    const summaryChange = firstPoint && firstPoint.value ? ((summaryValue - firstPoint.value) / firstPoint.value) * 100 : 0;
    const visibleDates = sortedDates.length > 1 ? [sortedDates[0], sortedDates[sortedDates.length - 1]] : sortedDates;

    let svg = '<div class="history-summary-card">';
    svg += '<div class="history-summary-title">تاریخچه ویوها</div>';
    svg += '<div class="history-summary-row">';
    svg += '<div class="history-metric-value">' + summaryValue.toLocaleString('en-US') + '</div>';
    svg += '<div class="history-metric-badge">▲ ' + Math.abs(summaryChange).toFixed(1) + '%</div>';
    svg += '</div>';
    svg += '<div class="history-summary-date">به‌روزرسانی: ' + (lastPoint?.label ? formatDayLabel(lastPoint.label) : '—') + '</div>';
    svg += '</div>';
    svg += '<div class="history-chart-stage">';
    svg += '<svg viewBox="0 0 ' + width + ' ' + height + '" class="history-svg">';
    svg += '<defs>';
    datasets.forEach((dataset) => {
      const gradientId = 'history-gradient-' + dataset.label.replace(/\s+/g, '-').toLowerCase();
      svg += '<linearGradient id="' + gradientId + '" x1="0" x2="0" y1="0" y2="1">';
      svg += '<stop offset="0%" stop-color="' + dataset.color + '" stop-opacity="0.28"></stop>';
      svg += '<stop offset="100%" stop-color="' + dataset.color + '" stop-opacity="0.02"></stop>';
      svg += '</linearGradient>';
    });
    svg += '</defs>';
    svg += '<rect x="0" y="0" width="' + width + '" height="' + height + '" rx="18" fill="rgba(255,255,255,0.015)"></rect>';

    for (let i = 0; i <= 4; i += 1) {
      const y = padding.top + (chartHeight / 4) * i;
      const value = Math.round(maxValue - (maxValue / 4) * i);
      yAxisLevels.push({ y, value });
      svg += '<line x1="' + padding.left + '" y1="' + y + '" x2="' + (width - padding.right) + '" y2="' + y + '" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4 4"></line>';
    }

    datasets.forEach((dataset) => {
      const points = dataset.points.map((point, index) => {
        const x = padding.left + stepX * index;
        const y = padding.top + chartHeight - (point.value / maxValue) * chartHeight;
        return { x, y, value: point.value, date: point.date, increase: point.increase, total: point.total, label: point.label };
      });

      if (points.length > 1) {
        const linePath = points.map((point, index) => (index === 0 ? 'M' : 'L') + point.x + ' ' + point.y).join(' ');
        const firstX = points[0].x;
        const lastX = points[points.length - 1].x;
        const baselineY = padding.top + chartHeight;
        const areaPath = linePath + ' L ' + lastX + ' ' + baselineY + ' L ' + firstX + ' ' + baselineY + ' Z';
        const gradientId = 'history-gradient-' + dataset.label.replace(/\s+/g, '-').toLowerCase();
        svg += '<path d="' + areaPath + '" fill="url(#' + gradientId + ')" opacity="0.9"></path>';
        svg += '<path d="' + linePath + '" fill="none" stroke="' + dataset.color + '" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"></path>';
      }

      points.forEach((point) => {
        const increaseText = point.increase !== null && point.increase !== undefined && point.increase > 0
          ? point.increase.toLocaleString('en-US') + ' '
          : '0 ';
        svg += '<circle class="history-point" data-label="' + escapeTooltipText(formatDayLabel(point.label)) + '" data-total="' + point.total.toLocaleString('en-US') + '" data-increase="' + increaseText + '" cx="' + point.x + '" cy="' + point.y + '" r="6" fill="' + dataset.color + '" stroke="#0f1115" stroke-width="2" style="cursor:pointer; pointer-events:all;"></circle>';
      });
    });

    visibleDates.forEach((date) => {
      const index = sortedDates.indexOf(date);
      const x = padding.left + stepX * index;
      svg += '<text x="' + x + '" y="' + (height - 10) + '" text-anchor="middle" fill="#fff" font-size="18" font-weight="700" font-family="Vazirmatn">' + formatDayLabel(date) + '</text>';
    });

    svg += '</svg>';
    svg += '<div class="history-tooltip"></div>';
    svg += '</div>';
    svg += '<div class="history-legend">';
    datasets.forEach((dataset) => {
      svg += '<span class="history-legend-item"><span class="history-legend-dot" style="background:' + dataset.color + '"></span>' + dataset.label + '</span>';
    });
    svg += '</div>';
    chartRoot.innerHTML = svg;

    const chartStage = chartRoot.querySelector('.history-chart-stage');
    const svgElement = chartStage.querySelector('.history-svg');
    const tooltip = chartStage.querySelector('.history-tooltip');
    const tooltipCard = document.createElement('div');
    const axisLabelsLayer = document.createElement('div');
    axisLabelsLayer.className = 'history-axis-labels';
    const pointsLayer = document.createElement('div');
    pointsLayer.className = 'history-points-layer';
    chartStage.appendChild(axisLabelsLayer);
    chartStage.appendChild(pointsLayer);
    tooltipCard.className = 'history-tooltip-card';
    tooltip.appendChild(tooltipCard);

    const svgRect = svgElement.getBoundingClientRect();
    const svgScaleX = svgRect.width / width;
    const svgScaleY = svgRect.height / height;

    (function adjustSvgTextSize() {
      const desiredPx = 18;
      const scale = svgScaleY || svgScaleX || 1;
      const userUnits = Math.max(10, Math.round(desiredPx / scale));
      const texts = svgElement.querySelectorAll('text');
      texts.forEach((t) => t.setAttribute('font-size', userUnits));
    })();

    yAxisLevels.forEach(({ y, value }) => {
      const label = document.createElement('div');
      label.className = 'history-axis-label';
      label.textContent = value.toLocaleString('en-US');
      label.style.top = (y * svgScaleY) + 'px';
      axisLabelsLayer.appendChild(label);
    });

    const updateTooltip = (point) => {
      const total = point.getAttribute('data-total') || '0';
      const label = point.getAttribute('data-label') || '—';
      tooltipCard.innerHTML = '<div>' + total + '</div><div class="tooltip-meta">' + label + '</div>';

      const stageRect = chartStage.getBoundingClientRect();
      const pointRect = point.getBoundingClientRect();
      const left = pointRect.left - stageRect.left + pointRect.width / 2;
      const top = pointRect.top - stageRect.top - 12;

      tooltip.style.left = left + 'px';
      tooltip.style.top = top + 'px';
      tooltip.classList.add('visible');
    };

    const hideTooltip = () => {
      tooltip.classList.remove('visible');
    };

    chartStage.querySelectorAll('.history-point').forEach((point) => {
      const hit = document.createElement('div');
      hit.className = 'history-point-hit';
      hit.setAttribute('data-total', point.getAttribute('data-total') || '');
      hit.setAttribute('data-label', point.getAttribute('data-label') || '');
      hit.setAttribute('data-increase', point.getAttribute('data-increase') || '');
      const x = Number(point.getAttribute('cx') || 0);
      const y = Number(point.getAttribute('cy') || 0);
      hit.style.left = (x * svgScaleX) + 'px';
      hit.style.top = (y * svgScaleY) + 'px';
      hit.addEventListener('mouseenter', () => updateTooltip(hit));
      hit.addEventListener('mousemove', () => updateTooltip(hit));
      hit.addEventListener('click', () => updateTooltip(hit));
      hit.addEventListener('mouseleave', hideTooltip);
      pointsLayer.appendChild(hit);
    });

    const firstPointHit = pointsLayer.querySelector('.history-point-hit');
    if (firstPointHit) {
      hideTooltip();
    }
  }

  filterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      selectedPlatform = button.dataset.platform || "all";
      filterButtons.forEach((chip) => chip.classList.toggle("active", chip === button));
      renderChart();
    });
  });

  renderChart();
})();
