document.addEventListener('DOMContentLoaded', function () {
  const grids = document.querySelectorAll('[data-paginate="true"]');
  if (!grids.length) return;

  grids.forEach((grid) => {
    const items = Array.from(grid.querySelectorAll('.album-card'));
    if (!items.length) return;

    function getItemsPerPage() {
      return window.matchMedia('(max-width: 600px)').matches ? 6 : 8;
    }

    let itemsPerPage = getItemsPerPage();
    let totalPages = Math.ceil(items.length / itemsPerPage);
    let currentPage = 0; // zero-based to match discography logic

    function buildControls() {
      let controls = grid.nextElementSibling;
      if (!controls || !controls.classList.contains('pagination')) {
        controls = document.createElement('div');
        controls.className = 'pagination';
        grid.parentNode.insertBefore(controls, grid.nextSibling);
      }

      controls.innerHTML = '';
      // If the grid is marked as first-page-only, do not build pagination controls
      if (grid.dataset.firstPageOnly === "true") return;
      if (totalPages <= 1) return;

      const prevBtn = document.createElement('button');
      prevBtn.className = 'pagination-btn pagination-prev';
      prevBtn.innerHTML = '→ قبلی';
      prevBtn.disabled = true;
      controls.appendChild(prevBtn);

      for (let i = 0; i < totalPages; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = 'pagination-btn pagination-page';
        pageBtn.textContent = String(i + 1);
        pageBtn.dataset.page = String(i);
        if (i === 0) pageBtn.classList.add('active');
        controls.appendChild(pageBtn);
      }

      const nextBtn = document.createElement('button');
      nextBtn.className = 'pagination-btn pagination-next';
      nextBtn.innerHTML = 'بعدی ←';
      controls.appendChild(nextBtn);

      controls.querySelectorAll('.pagination-btn').forEach((btn) => {
        btn.addEventListener('click', (e) => {
          e.preventDefault();
          try { btn.blur(); } catch (err) {}
          // Temporarily opt-out of automatic scroll for this grid
          try {
            grid.dataset.skipScroll = "true";
          } catch (err) {}

          if (btn.classList.contains('pagination-prev')) {
            showPage(currentPage - 1);
          } else if (btn.classList.contains('pagination-next')) {
            showPage(currentPage + 1);
          } else if (btn.classList.contains('pagination-page')) {
            showPage(parseInt(btn.dataset.page, 10));
          }

          // remove the flag shortly after to re-enable scroll for other interactions
          setTimeout(() => { try { delete grid.dataset.skipScroll; } catch (e) {} }, 60);
        });
      });
    }

    function showPage(pageIndex) {
      itemsPerPage = getItemsPerPage();
      totalPages = Math.ceil(items.length / itemsPerPage);
      currentPage = Math.max(0, Math.min(totalPages - 1, pageIndex));

      const start = currentPage * itemsPerPage;
      const end = start + itemsPerPage;
      items.forEach((item, idx) => {
        item.style.display = idx >= start && idx < end ? 'block' : 'none';
      });

      const controls = grid.nextElementSibling;
      if (!controls) return;
      const pageBtns = controls.querySelectorAll('.pagination-page');
      pageBtns.forEach((btn) => btn.classList.toggle('active', parseInt(btn.dataset.page, 10) === currentPage));

      const prevBtn = controls.querySelector('.pagination-prev');
      const nextBtn = controls.querySelector('.pagination-next');
      if (prevBtn) prevBtn.disabled = currentPage === 0;
      if (nextBtn) nextBtn.disabled = currentPage === totalPages - 1;

      // prevent browser auto-scroll caused by focus moving into pagination controls
      try {
        const active = document.activeElement;
        if (active && controls.contains(active)) {
          active.blur();
        }
      } catch (e) {}

      // Only scroll grid into view when not explicitly disabled on the grid element
      if (grid.dataset.skipScroll !== "true") {
        grid.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }

    // initial build
    buildControls();
    showPage(0);

    // rebuild on resize (responsive items per page)
    let resizeTimeout = null;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        const newPer = getItemsPerPage();
        if (newPer !== itemsPerPage) {
          itemsPerPage = newPer;
          totalPages = Math.ceil(items.length / itemsPerPage);
          buildControls();
          showPage(0);
        }
      }, 200);
    });
  });
});
