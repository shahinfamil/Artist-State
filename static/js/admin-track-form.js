document.addEventListener('DOMContentLoaded', function () {
  const genreCheckboxes = document.querySelectorAll('.genre-checkbox-input');
  const customInput = document.getElementById('genre-custom-input');
  const resultInput = document.getElementById('genre-result');
  const musicVideoCheckboxes = document.querySelectorAll('input[name="youtube_url_is_music_video"], input[name="youtube_url_secondary_is_music_video"]');

  if (genreCheckboxes.length && customInput && resultInput) {
    function updateGenreResult() {
      const selectedGenres = Array.from(genreCheckboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value.trim());

      const customGenres = customInput.value
        .split(',')
        .map(g => g.trim())
        .filter(g => g);

      const allGenres = [...new Set([...selectedGenres, ...customGenres])];
      resultInput.value = allGenres.join(', ');
    }

    function syncMusicVideoCheckboxes(event) {
      if (!event.target.checked) return;
      musicVideoCheckboxes.forEach((checkbox) => {
        if (checkbox !== event.target) {
          checkbox.checked = false;
        }
      });
    }

    genreCheckboxes.forEach(checkbox => {
      checkbox.addEventListener('change', updateGenreResult);
    });

    customInput.addEventListener('input', updateGenreResult);

    musicVideoCheckboxes.forEach((checkbox) => {
      checkbox.addEventListener('change', syncMusicVideoCheckboxes);
    });

    updateGenreResult();
  }

  const lyricistChecklist = document.getElementById('lyricist-checklist');
  const lyricsInput = document.getElementById('lyrics-input');
  const newLyricistInput = document.getElementById('new-lyricist-input');
  const addLyricistBtn = document.getElementById('add-lyricist-btn');
  const lyricsStatusBadge = document.getElementById('lyrics-status-badge');
  const workTypeSelect = document.getElementById('work-type-select');
  const remixOfWrapper = document.getElementById('remix-of-wrapper');
  const remixTrackSearch = document.getElementById('remix-track-search');
  const remixTrackHidden = document.getElementById('remix_of_track_id');
  const remixResultsBox = document.getElementById('remix-track-results');
  const remixToggleBtn = document.getElementById('remix-toggle-btn');

  if (workTypeSelect && remixOfWrapper) {
    function syncWorkTypeFields() {
      const isRemix = workTypeSelect.value === 'remix';
      remixOfWrapper.style.display = isRemix ? 'block' : 'none';
      const lyricistPanel = document.getElementById('lyricist-panel');
      const lyricsPanel = document.getElementById('lyrics-panel');
      const remixSourceInfo = document.getElementById('remix-source-info');
      if (isRemix) {
        if (lyricistPanel) lyricistPanel.style.display = 'none';
        if (lyricsPanel) lyricsPanel.style.display = 'none';
        if (remixSourceInfo) remixSourceInfo.style.display = 'block';
      } else {
        if (lyricistPanel) lyricistPanel.style.display = '';
        if (lyricsPanel) lyricsPanel.style.display = '';
        if (remixSourceInfo) remixSourceInfo.style.display = 'none';
      }
      if (!isRemix && remixTrackHidden) {
        remixTrackHidden.value = '';
      }
      if (!isRemix && remixTrackSearch) {
        remixTrackSearch.value = '';
      }
    }

    workTypeSelect.addEventListener('change', syncWorkTypeFields);
    syncWorkTypeFields();
  }

  if (remixTrackSearch && remixTrackHidden && remixResultsBox) {
    const remixOptions = Array.from(document.querySelectorAll('.remix-result-item'));
    let visibleOptions = remixOptions.slice();
    let highlightedIndex = -1;

    function updateVisibleOptions() {
      const searchText = (remixTrackSearch.value || '').trim().toLowerCase();
      visibleOptions = [];
      remixOptions.forEach((option) => {
        const title = (option.dataset.title || '').trim().toLowerCase();
        const matches = !searchText || title.includes(searchText);
        option.style.display = matches ? 'block' : 'none';
        if (matches) visibleOptions.push(option);
        option.classList.remove('is-selected');
      });
      highlightedIndex = -1;
      const emptyState = document.getElementById('remix-empty-state');
      if (emptyState) {
        emptyState.style.display = visibleOptions.length ? 'none' : 'block';
      }
      // always open to show results or empty state when user types/focuses
      openRemixDropdown();
    }

    function openRemixDropdown() {
      remixResultsBox.classList.add('is-open');
      remixResultsBox.setAttribute('aria-expanded', 'true');
      remixResultsBox.style.display = 'block';
    }

    function closeRemixDropdown() {
      remixResultsBox.classList.remove('is-open');
      remixResultsBox.setAttribute('aria-expanded', 'false');
      highlightedIndex = -1;
      remixResultsBox.style.display = 'none';
    }

    function highlightOption(index) {
      if (!visibleOptions.length) return;
      if (highlightedIndex >= 0 && visibleOptions[highlightedIndex]) {
        visibleOptions[highlightedIndex].classList.remove('is-selected');
      }
      highlightedIndex = Math.max(0, Math.min(index, visibleOptions.length - 1));
      const el = visibleOptions[highlightedIndex];
      if (el) {
        el.classList.add('is-selected');
        el.scrollIntoView({ block: 'nearest' });
      }
    }

    function selectHighlighted() {
      if (highlightedIndex < 0 && visibleOptions.length) highlightedIndex = 0;
      if (highlightedIndex >= 0 && visibleOptions[highlightedIndex]) {
        selectRemixOption(visibleOptions[highlightedIndex]);
      }
    }

    function selectRemixOption(option) {
      if (!option) return;
      remixTrackSearch.value = option.dataset.title || '';
      remixTrackHidden.value = option.dataset.id || '';
      remixOptions.forEach((item) => item.classList.remove('is-selected'));
      option.classList.add('is-selected');
      closeRemixDropdown();
      // ensure the dropdown visually closes and input loses focus
      try { remixTrackSearch.blur(); } catch (e) {}
      // hide editable lyric fields when a remix source is chosen
      const lyricistPanel = document.getElementById('lyricist-panel');
      const lyricsPanel = document.getElementById('lyrics-panel');
      if (workTypeSelect && workTypeSelect.value === 'remix') {
        if (lyricistPanel) lyricistPanel.style.display = 'none';
        if (lyricsPanel) lyricsPanel.style.display = 'none';
      }
    }

    remixTrackSearch.addEventListener('input', updateVisibleOptions);
    remixTrackSearch.addEventListener('focus', updateVisibleOptions);
    // toggle button to open/close list
    if (remixToggleBtn) {
      remixToggleBtn.addEventListener('click', function (e) {
        e.preventDefault();
        if (remixResultsBox.classList.contains('is-open')) {
          closeRemixDropdown();
        } else {
          updateVisibleOptions();
          remixTrackSearch.focus();
        }
      });
    }

    remixOptions.forEach((option) => {
      option.addEventListener('mousedown', (event) => {
        event.preventDefault();
        selectRemixOption(option);
      });
    });

    remixTrackSearch.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (visibleOptions.length === 0) updateVisibleOptions();
        highlightOption((highlightedIndex + 1) % visibleOptions.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (visibleOptions.length === 0) updateVisibleOptions();
        highlightOption((highlightedIndex - 1 + visibleOptions.length) % visibleOptions.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        selectHighlighted();
      } else if (e.key === 'Escape') {
        closeRemixDropdown();
      }
    });

    document.addEventListener('click', (ev) => {
      if (!ev.target.closest('.remix-track-picker')) {
        closeRemixDropdown();
      }
    });

    // initial run: compute but keep closed
    updateVisibleOptions();
    closeRemixDropdown();
  }

  if (lyricistChecklist && lyricsInput && newLyricistInput && addLyricistBtn && lyricsStatusBadge) {
    const getLyricistCheckboxes = () => Array.from(lyricistChecklist.querySelectorAll('input[name="lyricist"]'));

    function syncLyricistFields() {
      const selectedValues = getLyricistCheckboxes().filter(cb => cb.checked).map(cb => cb.value.trim());
      const hasLyricist = selectedValues.length > 0;

      lyricsInput.disabled = !hasLyricist;
      lyricsStatusBadge.textContent = hasLyricist ? 'فعال' : 'غیرفعال';
      lyricsStatusBadge.classList.toggle('field-tag--muted', !hasLyricist);
      lyricsStatusBadge.classList.toggle('field-tag--success', hasLyricist);

      if (!hasLyricist) {
        lyricsInput.value = '';
      }
    }

    getLyricistCheckboxes().forEach((checkbox) => {
      checkbox.addEventListener('change', syncLyricistFields);
    });

    addLyricistBtn.addEventListener('click', function () {
      const name = newLyricistInput.value.trim();
      if (!name) {
        newLyricistInput.focus();
        return;
      }

      const existingCheckboxes = getLyricistCheckboxes();
      const matched = existingCheckboxes.find((checkbox) => checkbox.value.trim().toLowerCase() === name.toLowerCase());

      if (matched) {
        matched.checked = true;
      } else {
        const label = document.createElement('label');
        label.className = 'lyricist-checkbox-item';
        label.innerHTML = `
          <input type="checkbox" name="lyricist" value="${name}" checked>
          <span>${name}</span>
        `;
        lyricistChecklist.appendChild(label);
        label.querySelector('input').addEventListener('change', syncLyricistFields);
      }

      newLyricistInput.value = '';
      syncLyricistFields();
    });

    syncLyricistFields();
  }
});
