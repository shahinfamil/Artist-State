(function () {
  const root = document.querySelector('.admin-container');
  if (!root) return;

  const reorderUrl = root.dataset.reorderUrl;
  const tabs = document.querySelectorAll('.admin-sidebar__tab');
  const panels = document.querySelectorAll('.admin-tab-panel');
  const searchInput = document.getElementById('contentLiveSearch');
  const albumBlocks = document.querySelectorAll('.album-block');

  function setupTrackReordering() {
    if (!reorderUrl) return;

    const tables = Array.from(document.querySelectorAll('.admin-table tbody'));
    if (!tables.length) return;

    let draggedId = null;

    tables.forEach((tbody) => {
      tbody.addEventListener('dragover', (event) => {
        event.preventDefault();
      });

      tbody.addEventListener('drop', async (event) => {
        event.preventDefault();
        const targetRow = event.target.closest('.admin-track-row');
        if (!draggedId || !targetRow) return;

        const targetId = targetRow.getAttribute('data-track-id');
        const draggedRow = document.querySelector(`.admin-track-row[data-track-id="${draggedId}"]`);
        if (!draggedRow || !targetId || draggedId === targetId) return;

        const rowsContainer = targetRow.parentElement;
        if (!rowsContainer || rowsContainer !== tbody) return;

        const fromIndex = Array.from(rowsContainer.children).indexOf(draggedRow);
        const toIndex = Array.from(rowsContainer.children).indexOf(targetRow);
        if (fromIndex === -1 || toIndex === -1) return;

        rowsContainer.insertBefore(draggedRow, targetRow);

        try {
          const response = await fetch(reorderUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({
              track_id: draggedId,
              target_id: targetId,
              position: toIndex
            })
          });
          if (!response.ok) {
            window.location.reload();
          }
        } catch (error) {
          window.location.reload();
        }
      });
    });

    document.querySelectorAll('.admin-track-row').forEach((row) => {
      row.addEventListener('dragstart', (event) => {
        draggedId = row.getAttribute('data-track-id');
        row.classList.add('is-dragging');
        if (event.dataTransfer) {
          event.dataTransfer.effectAllowed = 'move';
          event.dataTransfer.setData('text/plain', draggedId || '');
        }
      });

      row.addEventListener('dragend', () => {
        row.classList.remove('is-dragging');
        draggedId = null;
      });
    });
  }

  function formatNumber(value) {
    if (value === null || value === undefined || value === '') {
      return '—';
    }

    const parsed = Number(value);
    if (Number.isNaN(parsed)) {
      return String(value);
    }

    return new Intl.NumberFormat('en-US').format(parsed);
  }

  function setupTrackToggles() {
    document.querySelectorAll('.js-track-toggle').forEach((checkbox) => {
      checkbox.addEventListener('change', async (e) => {
        const cb = e.target;
        const url = cb.dataset.toggleUrl;
        const row = cb.closest('.admin-track-row');
        const newState = cb.checked;
        cb.disabled = true;
        try {
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
            body: JSON.stringify({ is_active: newState }),
          });
          const payload = await res.json();
          if (payload && payload.success) {
            row.classList.toggle('is-inactive', !payload.is_active);
          } else {
            cb.checked = !newState;
            alert('خطا در تغییر وضعیت');
          }
        } catch (err) {
          cb.checked = !newState;
          alert('خطا در ارتباط با سرور');
        } finally {
          cb.disabled = false;
        }
      });
    });
  }

  function setActiveTab(target) {
    tabs.forEach((item) => {
      const active = item.getAttribute('data-tab-target') === target;
      item.classList.toggle('is-active', active);
      item.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    panels.forEach((panel) => {
      const active = panel.getAttribute('data-tab-panel') === target;
      panel.classList.toggle('is-active', active);
      panel.hidden = !active;
    });
  }

  function initializeAnalyticsControls() {
    const analyticsForm = document.getElementById('analyticsFiltersForm');
    const dateFrom = document.getElementById('dateFrom');
    const dateTo = document.getElementById('dateTo');

    if (dateFrom && dateTo) {
      const applyDateBounds = () => {
        const minDate = dateFrom.getAttribute('min') || '';
        const maxDate = dateTo.getAttribute('max') || '';

        if (minDate) {
          dateFrom.min = minDate;
          dateTo.min = minDate;
        }
        if (maxDate) {
          dateFrom.max = maxDate;
          dateTo.max = maxDate;
        }

        if (dateFrom.value && minDate && dateFrom.value < minDate) {
          dateFrom.value = minDate;
        }
        if (dateTo.value && maxDate && dateTo.value > maxDate) {
          dateTo.value = maxDate;
        }
        if (dateFrom.value && dateTo.value && dateFrom.value > dateTo.value) {
          dateTo.value = dateFrom.value;
        }
      };

      applyDateBounds();
      dateFrom.addEventListener('change', applyDateBounds);
      dateTo.addEventListener('change', applyDateBounds);
    }

    const clearAnalyticsButton = document.querySelector('[data-analytics-action="clear"]');
    const trackInput = document.getElementById('trackAnalyticsInput');
    const trackHidden = document.getElementById('trackFilter');
    const trackSuggestions = document.getElementById('trackAnalyticsSuggestions');
    const trackSuggestionButtons = trackSuggestions ? Array.from(trackSuggestions.querySelectorAll('.analytics-track-suggestion')) : [];

    async function applyAnalyticsFilters() {
      if (!analyticsForm) return;

      const formData = new FormData(analyticsForm);
      const params = new URLSearchParams(window.location.search);
      ['platform', 'track_id', 'date_from', 'date_to', 'partial', 'tab'].forEach((key) => params.delete(key));

      formData.forEach((value, key) => {
        if (value) {
          params.set(key, value);
        }
      });

      params.set('partial', '1');
      params.set('tab', 'analytics');

      const targetUrl = `${window.location.pathname}?${params.toString()}`;
      const nextHash = '#analytics';
      window.history.pushState({}, '', `${targetUrl}${nextHash}`);

      const response = await fetch(targetUrl, {
        headers: {
          'X-Requested-With': 'XMLHttpRequest',
        },
      });
      const html = await response.text();
      const analyticsPanel = document.querySelector('.analytics-panel');
      if (analyticsPanel) {
        analyticsPanel.innerHTML = html;
        initializeAnalyticsControls();
      }
    }

    if (analyticsForm) {
      analyticsForm.addEventListener('submit', (event) => {
        event.preventDefault();
        applyAnalyticsFilters();
      });
    }

    if (clearAnalyticsButton && analyticsForm) {
      clearAnalyticsButton.addEventListener('click', () => {
        analyticsForm.reset();
        if (trackHidden) trackHidden.value = '';
        if (trackInput) trackInput.value = '';
        trackSuggestionButtons.forEach((button) => {
          button.classList.remove('is-selected');
          button.style.display = '';
        });
        applyAnalyticsFilters();
      });
    }

    if (trackInput && trackHidden && trackSuggestions) {
      const openSuggestions = () => trackSuggestions.classList.add('is-open');
      const closeSuggestions = () => trackSuggestions.classList.remove('is-open');

      const updateSuggestions = () => {
        const query = (trackInput.value || '').trim().toLowerCase();
        let visibleCount = 0;
        trackSuggestionButtons.forEach((button) => {
          const title = (button.getAttribute('data-track-title') || '').toLowerCase();
          const matches = !query || title.includes(query);
          button.style.display = matches ? '' : 'none';
          if (matches) visibleCount += 1;
        });
        if (visibleCount) {
          openSuggestions();
        } else {
          closeSuggestions();
        }
      };

      trackInput.addEventListener('focus', updateSuggestions);
      trackInput.addEventListener('input', updateSuggestions);
      trackInput.addEventListener('click', updateSuggestions);

      trackSuggestionButtons.forEach((button) => {
        button.addEventListener('click', () => {
          trackInput.value = button.getAttribute('data-track-title') || '';
          trackHidden.value = button.getAttribute('data-track-id') || '';
          trackSuggestionButtons.forEach((item) => item.classList.toggle('is-selected', item === button));
          closeSuggestions();
        });
      });

      document.addEventListener('click', (event) => {
        if (!trackInput.contains(event.target) && !trackSuggestions.contains(event.target)) {
          closeSuggestions();
        }
      });
    }
  }

  if (!tabs.length || !panels.length) return;

  setupTrackReordering();
  setupTrackToggles();

  tabs.forEach((tab) => {
    if (tab.dataset.pageUrl) {
      return;
    }
    tab.addEventListener('click', () => {
      const target = tab.getAttribute('data-tab-target');
      setActiveTab(target);
      const nextHash = target ? `#${target}` : '';
      const url = new URL(window.location.href);
      url.hash = nextHash;
      window.history.replaceState({}, '', url.toString());
    });
  });

  const initialHash = window.location.hash.replace('#', '');
  const path = window.location.pathname;
  const defaultTab = path.includes('/admin/analytics')
    ? 'analytics'
    : path.includes('/admin/users')
    ? 'users'
    : path.includes('/admin/content')
    ? 'content'
    : 'overview';
  const initialTab = Array.from(tabs).some((tab) => tab.getAttribute('data-tab-target') === initialHash)
    ? initialHash
    : defaultTab;
  if (!window.location.pathname.includes('/admin/artist') && !window.location.pathname.includes('/admin/wikipedia-info')) {
    setActiveTab(initialTab);
  }

  window.addEventListener('hashchange', () => {
    const target = window.location.hash.replace('#', '');
    if (Array.from(tabs).some((tab) => tab.getAttribute('data-tab-target') === target)) {
      setActiveTab(target);
    }
  });

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const query = searchInput.value.trim().toLowerCase();

      albumBlocks.forEach((block) => {
        const albumTitle = (block.getAttribute('data-album-title') || '').toLowerCase();
        const trackTitles = Array.from(block.querySelectorAll('.admin-track-row'))
          .map((row) => (row.getAttribute('data-track-title') || '').toLowerCase())
          .join(' ');
        const haystack = `${albumTitle} ${trackTitles}`;
        const isMatch = !query || haystack.includes(query);

        block.style.display = isMatch ? '' : 'none';
      });
    });
  }

  document.querySelectorAll('.js-update-views-form').forEach((form) => {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();

      const button = form.querySelector('.js-update-views-btn');
      if (!button) return;

      const platform = button.getAttribute('data-platform');
      const originalLabel = button.getAttribute('data-label') || button.textContent;
      const row = form.closest('.admin-track-row');
      const valueEl = row ? row.querySelector(`.platform-stat-value[data-platform="${platform}"]`) : null;

      button.classList.add('is-loading');
      button.disabled = true;
      button.setAttribute('aria-busy', 'true');
      button.innerHTML = '<span class="spinner"></span><span class="btn-label"></span>';

      try {
        const response = await fetch(form.action, {
          method: 'POST',
          headers: {
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json'
          },
          body: new URLSearchParams(new FormData(form))
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.success) {
          throw new Error(data.message || 'به‌روزرسانی انجام نشد.');
        }

        const formattedValue = data.latest_stats && data.latest_stats[platform] !== null && data.latest_stats[platform] !== undefined
          ? formatNumber(data.latest_stats[platform])
          : '—';

        if (valueEl) {
          valueEl.textContent = formattedValue;
        }

        button.classList.remove('is-error');
        button.innerHTML = `<span class="btn-label">${originalLabel}</span>`;
      } catch (error) {
        button.classList.add('is-error');
        button.innerHTML = '<span class="btn-label">خطا</span>';
        setTimeout(() => {
          button.classList.remove('is-error');
          button.innerHTML = `<span class="btn-label">${originalLabel}</span>`;
        }, 1400);
      } finally {
        button.classList.remove('is-loading');
        button.disabled = false;
        button.setAttribute('aria-busy', 'false');
      }
    });
  });

  initializeAnalyticsControls();
})();
