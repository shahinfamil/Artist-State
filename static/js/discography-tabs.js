/**
 * Discography Tabs & Pagination Manager
 */

(function () {
  const ITEMS_PER_PAGE = 8;

  const tabBtns = document.querySelectorAll(".tab-btn");
  const tabContents = document.querySelectorAll(".tab-content");
  const paginationContainers = document.querySelectorAll(".pagination");

  if (tabBtns.length === 0) return;

  // Initialize pagination for each tab
  function initPagination(tabElement) {
    const itemsCount = parseInt(tabElement.dataset.itemsCount) || 0;
    const tabName = tabElement.dataset.tabName;
    const paginationEl = document.getElementById(`pagination-${tabName}`);

    if (!paginationEl) return;

    // اگر کم از 9 آیتم است، pagination نشان نده
    if (itemsCount <= ITEMS_PER_PAGE) {
      paginationEl.style.display = "none";
      return;
    }

    // تعداد صفحات
    const totalPages = Math.ceil(itemsCount / ITEMS_PER_PAGE);

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
    const cards = gridElement.querySelectorAll(".album-card");
    const paginationEl = document.getElementById(`pagination-${tabName}`);

    const startIdx = pageIndex * ITEMS_PER_PAGE;
    const endIdx = startIdx + ITEMS_PER_PAGE;

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
    gridElement.scrollIntoView({ behavior: "smooth", block: "start" });
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
  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const tabName = btn.dataset.tab;

      // Remove active from all buttons
      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");

      // Hide all tabs
      tabContents.forEach((content) => content.classList.remove("active"));

      // Show selected tab
      const selectedTab = document.getElementById(`tab-${tabName}`);
      if (selectedTab) {
        selectedTab.classList.add("active");
        // Reset pagination to page 1
        showPage(tabName, 0);
      }
    });
  });

  // Initialize pagination for all tabs
  tabContents.forEach((tabElement) => {
    initPagination(tabElement);
  });
})();
