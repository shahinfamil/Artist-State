/**
 * Discography Tabs & Pagination Manager
 */

(function () {
  function getItemsPerPage() {
    return window.matchMedia("(max-width: 600px)").matches ? 6 : 8;
  }

  const tabGroups = document.querySelectorAll(".discography-tabs");
  if (tabGroups.length === 0) return;

  const paginationContainers = document.querySelectorAll(".pagination");

  function attachSwipeNavigation(tabName) {
    const tabPanel = document.getElementById(`tab-${tabName}`);
    const paginationEl = document.getElementById(`pagination-${tabName}`);
    if (!tabPanel || !paginationEl) return;

    let startX = 0;
    let startY = 0;
    let deltaX = 0;

    tabPanel.addEventListener("touchstart", (event) => {
      if (window.innerWidth > 600) return;
      const touch = event.touches[0];
      startX = touch.clientX;
      startY = touch.clientY;
      deltaX = 0;
    }, { passive: true });

    tabPanel.addEventListener("touchmove", (event) => {
      if (window.innerWidth > 600) return;
      const touch = event.touches[0];
      deltaX = touch.clientX - startX;
      const deltaY = touch.clientY - startY;

      if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 12) {
        event.preventDefault();
      }
    }, { passive: false });

    tabPanel.addEventListener("touchend", (event) => {
      if (window.innerWidth > 600) return;
      if (!paginationEl.querySelector(".pagination-page")) return;

      const touch = event.changedTouches[0];
      const endX = touch.clientX;
      const endY = touch.clientY;
      const horizontalDistance = endX - startX;
      const verticalDistance = endY - startY;

      if (Math.abs(horizontalDistance) < 50 || Math.abs(horizontalDistance) < Math.abs(verticalDistance)) return;

      const activePageBtn = paginationEl.querySelector(".pagination-page.active");
      const currentPage = parseInt(activePageBtn?.dataset.page || "0");
      const totalPages = paginationEl.querySelectorAll(".pagination-page").length;

      if (horizontalDistance > 0 && currentPage < totalPages - 1) {
        goToPage(tabName, paginationEl.querySelector(".pagination-next"));
      } else if (horizontalDistance < 0 && currentPage > 0) {
        goToPage(tabName, paginationEl.querySelector(".pagination-prev"));
      }
    }, { passive: true });
  }

  // Initialize pagination for each tab
  function initPagination(tabElement) {
    const itemsCount = parseInt(tabElement.dataset.itemsCount) || 0;
    const tabName = tabElement.dataset.tabName;
    const paginationEl = document.getElementById(`pagination-${tabName}`);

    if (!paginationEl) return;

    const itemsPerPage = getItemsPerPage();

    // اگر کم از 9 آیتم است، pagination نشان نده
    if (itemsCount <= itemsPerPage) {
      paginationEl.style.display = "none";
      return;
    }

    // تعداد صفحات
    const totalPages = Math.ceil(itemsCount / itemsPerPage);

    // HTML pagination
    paginationEl.innerHTML = "";
    paginationEl.classList.add("pagination-container");

    // Previous button
    const prevBtn = document.createElement("button");
    prevBtn.className = "pagination-btn pagination-prev";
    prevBtn.innerHTML = "→ قبلی";
    prevBtn.disabled = true;
    prevBtn.dataset.page = "0";
    paginationEl.appendChild(prevBtn);

    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
      const pageBtn = document.createElement("button");
      pageBtn.className = "pagination-btn pagination-page";
      pageBtn.textContent = i;
      pageBtn.dataset.page = i - 1;
      if (i === 1) pageBtn.classList.add("active");
      paginationEl.appendChild(pageBtn);
    }

    // Next button
    const nextBtn = document.createElement("button");
    nextBtn.className = "pagination-btn pagination-next";
    nextBtn.innerHTML = "بعدی ←";
    nextBtn.dataset.page = "1";
    paginationEl.appendChild(nextBtn);

    // Add click listeners
    paginationEl.querySelectorAll(".pagination-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.preventDefault();
        goToPage(tabName, btn);
      });
    });

    // Show first page
    showPage(tabName, 0);
  }

  // Show specific page
  function showPage(tabName, pageIndex) {
    const gridElement = document.getElementById(`grid-${tabName}`);
    if (!gridElement) return;

    const cards = gridElement.querySelectorAll(".album-card");
    const paginationEl = document.getElementById(`pagination-${tabName}`);
    if (!paginationEl) return;

    const itemsPerPage = getItemsPerPage();
    const startIdx = pageIndex * itemsPerPage;
    const endIdx = startIdx + itemsPerPage;

    // Hide/show cards
    cards.forEach((card, idx) => {
      card.style.display = idx >= startIdx && idx < endIdx ? "block" : "none";
    });

    // Update pagination buttons
    const pageButtons = paginationEl.querySelectorAll(".pagination-page");
    const prevBtn = paginationEl.querySelector(".pagination-prev");
    const nextBtn = paginationEl.querySelector(".pagination-next");

    pageButtons.forEach((btn) => {
      btn.classList.toggle("active", parseInt(btn.dataset.page) === pageIndex);
    });

    // Update prev/next button states
    prevBtn.disabled = pageIndex === 0;
    nextBtn.disabled = pageIndex === pageButtons.length - 1;

    // Scroll to top
    // Scroll only when the grid/tab panel hasn't opted out
    try {
      if (!gridElement.dataset || gridElement.dataset.skipScroll !== "true") {
        gridElement.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    } catch (e) {
      // fallback: do nothing
    }
  }

  // Go to page handler
  function goToPage(tabName, btn) {
    const pageIndex = parseInt(btn.dataset.page);
    const paginationEl = document.getElementById(`pagination-${tabName}`);

    if (btn.classList.contains("pagination-prev")) {
      // Previous
      const currentActive = paginationEl.querySelector(".pagination-page.active");
      const currentPage = parseInt(currentActive.dataset.page);
      if (currentPage > 0) {
        showPage(tabName, currentPage - 1);
      }
    } else if (btn.classList.contains("pagination-next")) {
      // Next
      const currentActive = paginationEl.querySelector(".pagination-page.active");
      const currentPage = parseInt(currentActive.dataset.page);
      const totalPages = paginationEl.querySelectorAll(".pagination-page").length;
      if (currentPage < totalPages - 1) {
        showPage(tabName, currentPage + 1);
      }
    } else if (btn.classList.contains("pagination-page")) {
      // Direct page click
      showPage(tabName, pageIndex);
    }
  }

  // Tab switching
  tabGroups.forEach((tabGroup) => {
    const tabBtns = Array.from(tabGroup.querySelectorAll(".tab-btn"));
    const groupName = tabGroup.dataset.tabGroup || "default";
    const tabContents = Array.from(tabGroup.parentElement.querySelectorAll(".tab-content")).filter((content) => {
      return (content.dataset.tabGroup || "default") === groupName;
    });

    if (!tabBtns.length || !tabContents.length) return;

    tabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        try { btn.blur(); } catch (err) {}
        // temporarily opt-out of auto-scroll for grids inside this tab while switching
        try {
          const targetGrid = document.getElementById(`grid-${btn.dataset.tab}`);
          if (targetGrid) targetGrid.dataset.skipScroll = "true";
        } catch (e) {}

        const tabName = btn.dataset.tab;

        tabBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");

        tabContents.forEach((content) => content.classList.remove("active"));

        const selectedTab = document.getElementById(`tab-${tabName}`);
          if (selectedTab) {
            selectedTab.classList.add("active");
            window.dispatchEvent(new CustomEvent('track-album-ticker-refresh'));
            setTimeout(function () {
              window.dispatchEvent(new CustomEvent('track-album-ticker-refresh'));
            }, 80);

            if (selectedTab.querySelector('.pagination') || selectedTab.querySelector('.album-card')) {
              showPage(tabName, 0);
            }
          }

          // re-enable scrolling shortly after tab switch
          setTimeout(() => {
            try {
              const targetGrid = document.getElementById(`grid-${btn.dataset.tab}`);
              if (targetGrid) delete targetGrid.dataset.skipScroll;
            } catch (e) {}
          }, 100);
      });
    });
  });

  function sortTrackRows(list, mode = (list.dataset.sortMode || "views")) {
    const rows = Array.from(list.querySelectorAll(".track-row"));

    rows.sort((a, b) => {
      const left = mode === "growth" ? Number(b.dataset.growth || 0) : Number(b.dataset.total || 0);
      const right = mode === "growth" ? Number(a.dataset.growth || 0) : Number(a.dataset.total || 0);
      return left - right;
    });

    rows.forEach((row, index) => {
      list.appendChild(row);
      const rank = row.querySelector(".track-rank");
      if (rank) {
        rank.textContent = String(index + 1).padStart(2, "0");
      }

      const totalValue = row.querySelector(".track-total-value");
      const growthBadge = row.querySelector(".growth-badge");
      if (totalValue && growthBadge) {
        const showGrowth = mode === "growth";
        totalValue.style.display = showGrowth ? "none" : "inline-block";
        growthBadge.style.display = showGrowth ? "inline-flex" : "none";
      }
    });
  }

  function initTrackRevealMore() {
    document.querySelectorAll(".track-list[data-show-count]").forEach((list) => {
      const rows = Array.from(list.querySelectorAll(".track-row"));
      const btn = list.parentElement.querySelector(".track-show-more");
      if (!btn || rows.length <= 0) return;

      const showCount = parseInt(list.dataset.showCount || "10", 10);
      list.dataset.sortMode = list.dataset.sortMode || "views";
      list.dataset.expanded = "false";

      function updateRows() {
        const expanded = list.dataset.expanded === "true";
        sortTrackRows(list, list.dataset.sortMode || "views");

        const visibleRows = Array.from(list.querySelectorAll(".track-row"));

        visibleRows.forEach((row, index) => {
          const shouldShow = expanded || index < showCount;
          row.hidden = !shouldShow;
          row.style.display = shouldShow ? "grid" : "none";
        });

        const remaining = Math.max(visibleRows.length - showCount, 0);
        btn.textContent = expanded ? "پنهان کردن ترک‌های دیگر" : `نمایش دیگر ترک‌ها${remaining > 0 ? " (" + remaining + ")" : ""}`;
        btn.setAttribute("aria-expanded", String(expanded));
        btn.style.display = visibleRows.length > showCount ? "inline-flex" : "none";
      }

      btn.addEventListener("click", () => {
        list.dataset.expanded = String(list.dataset.expanded !== "true");
        updateRows();
      });

      const sortButtons = list.parentElement.querySelectorAll(".track-sort-btn");
      sortButtons.forEach((sortBtn) => {
        sortBtn.addEventListener("click", () => {
          list.dataset.sortMode = sortBtn.dataset.sort || "views";
          sortButtons.forEach((button) => button.classList.toggle("active", button === sortBtn));
          updateRows();
        });
      });

      updateRows();
    });
  }

  // Initialize pagination only for paginated tab groups
  tabGroups.forEach((tabGroup) => {
    const groupName = tabGroup.dataset.tabGroup || "default";
    const tabContents = Array.from(tabGroup.parentElement.querySelectorAll(".tab-content")).filter((content) => {
      return (content.dataset.tabGroup || "default") === groupName;
    });

    tabContents.forEach((tabElement) => {
      if (tabElement.dataset.firstPageOnly === "true") {
        // ensure only first page items are visible (hide others)
        const gridEl = tabElement.querySelector('.album-grid');
        if (gridEl) {
          const cards = Array.from(gridEl.querySelectorAll('.album-card'));
          const per = getItemsPerPage();
          cards.forEach((c, idx) => { c.style.display = idx < per ? 'block' : 'none'; });
        }
        // hide any existing pagination controls inside this tab content
        const pag = tabElement.querySelectorAll('.pagination');
        pag.forEach(p => { try { p.style.display = 'none'; } catch (e) {} });
        return;
      }

      if (tabElement.querySelector(".pagination") || tabElement.dataset.itemsCount) {
        initPagination(tabElement);
        attachSwipeNavigation(tabElement.dataset.tabName);
      }
    });
  });

  initTrackRevealMore();
})();
