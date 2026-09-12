// JS extracted from templates/admin/growth.html
// Range navigation helpers removed (buttons not present)

function formatNumber(n) {
  if (n === null || n === undefined) return '0';
  const num = Number(n);
  if (Number.isNaN(num)) return String(n);
  return new Intl.NumberFormat('en-US').format(num);
}

function syncFilterState() {
  const currentPlatform = new URLSearchParams(window.location.search).get('platform') || '';
  document.querySelectorAll('.js-growth-platform-filter').forEach(function (button) {
    const expected = button.dataset.platform || '';
    const isActive = currentPlatform === expected;
    button.classList.toggle('is-active', isActive);
    button.setAttribute('aria-pressed', isActive ? 'true' : 'false');

    button.style.borderColor = isActive ? '' : 'rgba(255,255,255,0.12)';
    button.style.color = '#f2f1ed';
    button.style.background = isActive ? '' : 'rgba(255,255,255,0.02)';

    if (button.classList.contains('js-growth-platform-filter--spotify')) {
      button.style.borderColor = isActive ? '#34d399' : 'rgba(52, 211, 153, 0.45)';
      button.style.background = isActive ? 'rgba(52, 211, 153, 0.18)' : 'rgba(52, 211, 153, 0.06)';
    }
    if (button.classList.contains('js-growth-platform-filter--youtube')) {
      button.style.borderColor = isActive ? '#f87171' : 'rgba(248, 113, 113, 0.45)';
      button.style.background = isActive ? 'rgba(248, 113, 113, 0.18)' : 'rgba(248, 113, 113, 0.06)';
    }
    if (button.classList.contains('js-growth-platform-filter--soundcloud')) {
      button.style.borderColor = isActive ? '#fbbf24' : 'rgba(251, 191, 36, 0.45)';
      button.style.background = isActive ? 'rgba(251, 191, 36, 0.18)' : 'rgba(251, 191, 36, 0.06)';
    }
    if (button.classList.contains('js-growth-platform-filter--all')) {
      button.style.borderColor = isActive ? '#d8b46a' : 'rgba(216, 180, 106, 0.45)';
      button.style.background = isActive ? 'rgba(216, 180, 106, 0.18)' : 'rgba(216, 180, 106, 0.06)';
    }
  });
}

function renderSummary(data) {
  document.querySelectorAll('.admin-card-card-wrap').forEach(function (wrap) {
    const days = parseInt(wrap.dataset.windowDays || '1', 10);
    let value = 0, desc = '';
    if (days === 1) {
      value = data.aggregate_growth.growth_day_abs || 0;
      desc = data.growth_range_day || '';
      wrap.dataset.from = data.growth_from_day_iso || wrap.dataset.from;
      wrap.dataset.to = data.growth_to_day_iso || wrap.dataset.to;
    } else if (days === 7) {
      value = data.aggregate_growth.growth_week_abs || 0;
      desc = data.growth_range_week || '';
      wrap.dataset.from = data.growth_from_week_iso || wrap.dataset.from;
      wrap.dataset.to = data.growth_to_week_iso || wrap.dataset.to;
    } else if (days === 30) {
      value = data.aggregate_growth.growth_month_abs || 0;
      desc = data.growth_range_month || '';
      wrap.dataset.from = data.growth_from_month_iso || wrap.dataset.from;
      wrap.dataset.to = data.growth_to_month_iso || wrap.dataset.to;
    } else if (days === 365) {
      value = data.aggregate_growth.growth_year_abs || 0;
      desc = data.growth_range_year || '';
      wrap.dataset.from = data.growth_from_year_iso || wrap.dataset.from;
      wrap.dataset.to = data.growth_to_year_iso || wrap.dataset.to;
    }
    const valueEl = wrap.querySelector('.admin-stat-card__value');
    const descEl = wrap.querySelector('.admin-stat-card__description');
    if (valueEl) valueEl.textContent = formatNumber(value);
    if (descEl) descEl.textContent = desc;
  });
}

function renderTable(data) {
  const tbody = document.querySelector('.admin-growth-table tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  const rows = data.per_track_growth || [];
  if (rows.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td colspan="6" class="muted">هنوز داده‌ای برای رشد آهنگ‌ها ثبت نشده است.</td>';
    tbody.appendChild(tr);
    return;
  }
  const frag = document.createDocumentFragment();
  rows.forEach(function (item) {
    const tr = document.createElement('tr');
    // match template header order: Views, Yearly, Monthly, Weekly, Daily, Name
    tr.innerHTML = '<td class="font-en">' + formatNumber(item.latest || 0) + '</td>' +
      '<td><span class="growth-value ' + ((item.growth_year_abs >= 0) ? 'is-positive' : 'is-negative') + '">' + formatNumber(item.growth_year_abs || 0) + '</span></td>' +
      '<td><span class="growth-value ' + ((item.growth_month_abs >= 0) ? 'is-positive' : 'is-negative') + '">' + formatNumber(item.growth_month_abs || 0) + '</span></td>' +
      '<td><span class="growth-value ' + ((item.growth_week_abs >= 0) ? 'is-positive' : 'is-negative') + '">' + formatNumber(item.growth_week_abs || 0) + '</span></td>' +
      '<td><span class="growth-value ' + ((item.growth_day_abs >= 0) ? 'is-positive' : 'is-negative') + '">' + formatNumber(item.growth_day_abs || 0) + '</span></td>' +
      '<td>' + (item.title || '') + '</td>';
    frag.appendChild(tr);
  });
  tbody.appendChild(frag);
}

function fetchAndRender(url) {
  const parsed = new URL(url, window.location.href);
  const apiUrl = '/admin/growth.json?' + parsed.searchParams.toString();
  return fetch(apiUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(function (res) { if (!res.ok) throw new Error('fetch failed'); return res.json(); })
    .then(function (data) {
      renderSummary(data);
      renderTable(data);
      history.pushState({ path: url }, '', url);
      syncFilterState();
    })
    .catch(function () {
      window.location.href = url;
    });
}

function replaceGrowthContent(url) {
  const container = document.querySelector('.admin-container');
  // Build API URL based on requested query params
  const parsed = new URL(url, window.location.href);
  const apiUrl = '/admin/growth.json?' + parsed.searchParams.toString();
  fetch(apiUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
    .then(function (response) {
      if (!response.ok) throw new Error('Failed to load growth JSON');
      return response.json();
    })
    .then(function (data) {
      // Update summary cards values and descriptions
      document.querySelectorAll('.admin-card-card-wrap').forEach(function (wrap) {
        const days = parseInt(wrap.dataset.windowDays || '1', 10);
        let value = '';
        let desc = '';
        if (days === 1) {
          value = data.aggregate_growth.growth_day_abs || 0;
          desc = data.growth_range_day || '';
          wrap.dataset.from = data.growth_from_day_iso || wrap.dataset.from;
          wrap.dataset.to = data.growth_to_day_iso || wrap.dataset.to;
        } else if (days === 7) {
          value = data.aggregate_growth.growth_week_abs || 0;
          desc = data.growth_range_week || '';
          wrap.dataset.from = data.growth_from_week_iso || wrap.dataset.from;
          wrap.dataset.to = data.growth_to_week_iso || wrap.dataset.to;
        } else if (days === 30) {
          value = data.aggregate_growth.growth_month_abs || 0;
          desc = data.growth_range_month || '';
          wrap.dataset.from = data.growth_from_month_iso || wrap.dataset.from;
          wrap.dataset.to = data.growth_to_month_iso || wrap.dataset.to;
        } else if (days === 365) {
          value = data.aggregate_growth.growth_year_abs || 0;
          desc = data.growth_range_year || '';
          wrap.dataset.from = data.growth_from_year_iso || wrap.dataset.from;
          wrap.dataset.to = data.growth_to_year_iso || wrap.dataset.to;
        }
        const valueEl = wrap.querySelector('.admin-stat-card__value');
        const descEl = wrap.querySelector('.admin-stat-card__description');
        if (valueEl) valueEl.textContent = value;
        if (descEl) descEl.textContent = desc;
      });

      // Rebuild table body quickly from JSON
      if (container) {
        const tbody = container.querySelector('.admin-growth-table tbody');
        if (tbody) {
          tbody.innerHTML = '';
          const rows = data.per_track_growth || [];
          if (rows.length === 0) {
            const tr = document.createElement('tr');
            tr.innerHTML = '<td colspan="6" class="muted">هنوز داده‌ای برای رشد آهنگ‌ها ثبت نشده است.</td>';
            tbody.appendChild(tr);
          } else {
            rows.forEach(function (item) {
              const tr = document.createElement('tr');
              // match template header order: Views, Yearly, Monthly, Weekly, Daily, Name
              tr.innerHTML = '<td class="font-en">' + formatNumber(item.latest || 0) + '</td>' +
                        '<td><span class="growth-value ' + ((item.growth_year_abs >= 0) ? 'is-positive' : 'is-negative') + '">' + formatNumber(item.growth_year_abs || 0) + '</span></td>' +
                        '<td><span class="growth-value ' + ((item.growth_month_abs >= 0) ? 'is-positive' : 'is-negative') + '">' + formatNumber(item.growth_month_abs || 0) + '</span></td>' +
                        '<td><span class="growth-value ' + ((item.growth_week_abs >= 0) ? 'is-positive' : 'is-negative') + '">' + formatNumber(item.growth_week_abs || 0) + '</span></td>' +
                        '<td><span class="growth-value ' + ((item.growth_day_abs >= 0) ? 'is-positive' : 'is-negative') + '">' + formatNumber(item.growth_day_abs || 0) + '</span></td>' +
                        '<td>' + (item.title || '') + '</td>';
              tbody.appendChild(tr);
            });
          }
        }
      }

      // Update URL and UI state
      history.pushState({ path: url }, '', url);
      syncFilterState();
    })
    .catch(function () {
      // fallback to full page navigation on error
      window.location.href = url;
    });
}

window.addEventListener('popstate', function () {
  const currentUrl = window.location.href;
  fetchAndRender(currentUrl);
});

// Event delegation: platform filters
document.addEventListener('click', function (e) {
  const pf = e.target.closest('.js-growth-platform-filter');
  if (pf) {
    e.preventDefault();
    const url = pf.getAttribute('href');
    if (url) fetchAndRender(url);
    return;
  }
});

// Initialize UI state on DOM ready
document.addEventListener('DOMContentLoaded', function () {
  syncFilterState();
});
