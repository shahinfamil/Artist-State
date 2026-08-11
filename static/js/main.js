// رفتار اسکرول نرم برای لینک‌های داخلی
document.querySelectorAll('a[href^="#"]').forEach((link) => {
  link.addEventListener("click", (e) => {
    const target = document.querySelector(link.getAttribute("href"));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
});

const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');
const searchForm = document.querySelector('.header-search');
let searchTimeout;

function setSearchLoading(isLoading) {
  searchForm?.classList.toggle('is-searching', isLoading);
}

if (searchInput && searchResults) {
  searchInput.addEventListener('input', function() {
    clearTimeout(searchTimeout);
    const query = this.value.trim();

    if (query.length < 2) {
      setSearchLoading(false);
      searchResults.style.display = 'none';
      return;
    }

    setSearchLoading(true);
    searchResults.innerHTML = '<div style="padding: 0.85rem 1rem; color: #aaa; text-align: center;">در حال جستجو…</div>';
    searchResults.style.display = 'block';
    searchTimeout = setTimeout(() => {
      fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
          setSearchLoading(false);
          if (data.length === 0) {
            searchResults.innerHTML = '<div style="padding: 1rem; text-align: center; color: #aaa;">نتیجه‌ای پیدا نشد</div>';
            searchResults.style.display = 'block';
            return;
          }

          const html = data.map(track => `
            <a href="${track.url}" style="display: flex; align-items: center; padding: 0.75rem 1rem; color: white; text-decoration: none; border-bottom: 1px solid rgba(255,255,255,0.1); transition: background 0.2s;">
              <img src="${track.cover_url}" alt="" style="width: 40px; height: 40px; border-radius: 4px; margin-left: 0.75rem; object-fit: cover;">
              <div style="flex: 1;">
                <div style="font-size: 0.9rem; font-weight: 500;">${track.title}</div>
                <div style="font-size: 0.8rem; color: #aaa;">${track.album}</div>
              </div>
            </a>
          `).join('');

          searchResults.innerHTML = html;
          searchResults.style.display = 'block';
        })
        .catch(error => {
          setSearchLoading(false);
          console.error('Search error:', error);
        });
    }, 300);
  });

  document.addEventListener('click', function(event) {
    if (!event.target.closest('.header-search')) {
      searchResults.style.display = 'none';
    }
  });

  searchInput.addEventListener('focus', function() {
    this.setAttribute('placeholder', 'نام آهنگ را به فینگلیش سرچ کنید');
    if (this.value.trim().length >= 2) {
      searchResults.style.display = 'block';
    }
  });

  searchInput.addEventListener('blur', function() {
    if (!this.value.trim()) {
      this.setAttribute('placeholder', 'جستجو');
    }
  });
}

function resetPageScroll() {
  window.scrollTo(0, 0);
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
}

document.addEventListener("DOMContentLoaded", () => {
  const scrollToTopButton = document.getElementById('scroll-to-top');
  const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
  const mobileSearchToggle = document.querySelector('.mobile-search-toggle');
  const mainNav = document.querySelector('#main-navigation');
  const searchForm = document.querySelector('.header-search');
  const styleRows = document.querySelectorAll('.genre-grid');

  styleRows.forEach((row) => {
    let isDragging = false;
    let startX = 0;
    let startScrollLeft = 0;

    const stopDragging = () => {
      if (!isDragging) return;
      isDragging = false;
      row.classList.remove('is-dragging');
      document.body.style.userSelect = '';
      document.body.style.webkitUserSelect = '';
    };

    const startDragging = (clientX) => {
      isDragging = true;
      row.classList.add('is-dragging');
      startX = clientX;
      startScrollLeft = row.scrollLeft;
      document.body.style.userSelect = 'none';
      document.body.style.webkitUserSelect = 'none';
    };

    const drag = (clientX) => {
      if (!isDragging) return;
      const deltaX = clientX - startX;
      row.scrollLeft = startScrollLeft - deltaX;
    };

    row.addEventListener('mousedown', (event) => {
      event.preventDefault();
      startDragging(event.clientX);
    });

    row.addEventListener('mousemove', (event) => {
      if (!isDragging) return;
      event.preventDefault();
      drag(event.clientX);
    });

    row.addEventListener('mouseleave', stopDragging);
    window.addEventListener('mouseup', stopDragging);

    row.addEventListener('touchstart', (event) => {
      if (event.touches.length !== 1) return;
      startDragging(event.touches[0].clientX);
    }, { passive: false });

    row.addEventListener('touchmove', (event) => {
      if (!isDragging || event.touches.length !== 1) return;
      event.preventDefault();
      drag(event.touches[0].clientX);
    }, { passive: false });

    row.addEventListener('touchend', stopDragging);
    row.addEventListener('touchcancel', stopDragging);
  });

  function closeMobilePanels() {
    searchForm?.classList.remove('is-mobile-open');
    mainNav?.classList.remove('is-open');
    mobileSearchToggle?.setAttribute('aria-expanded', 'false');
    mobileSearchToggle?.setAttribute('aria-label', 'جستجو');
    mobileMenuToggle?.setAttribute('aria-expanded', 'false');
    mobileMenuToggle?.setAttribute('aria-label', 'باز کردن منو');
  }

  if (mobileMenuToggle && mainNav) {
    mobileMenuToggle.addEventListener('click', (event) => {
      event.stopPropagation();
      const isExpanded = mobileMenuToggle.getAttribute('aria-expanded') === 'true';
      const nextExpanded = !isExpanded;
      mobileMenuToggle.setAttribute('aria-expanded', String(nextExpanded));
      mobileMenuToggle.setAttribute('aria-label', nextExpanded ? 'بستن منو' : 'باز کردن منو');

      if (nextExpanded) {
        closeMobilePanels();
        mainNav.classList.add('is-open');
        mobileMenuToggle.setAttribute('aria-expanded', 'true');
        mobileMenuToggle.setAttribute('aria-label', 'بستن منو');
      } else {
        mainNav.classList.remove('is-open');
      }
    });

    document.addEventListener('click', (event) => {
      const clickedInsideMenu = mainNav.contains(event.target);
      const clickedToggle = mobileMenuToggle.contains(event.target);
      if (!clickedInsideMenu && !clickedToggle && mainNav.classList.contains('is-open')) {
        mainNav.classList.remove('is-open');
        mobileMenuToggle.setAttribute('aria-expanded', 'false');
        mobileMenuToggle.setAttribute('aria-label', 'باز کردن منو');
      }
    });
  }

  if (mobileSearchToggle && searchForm) {
    mobileSearchToggle.addEventListener('click', () => {
      const isExpanded = mobileSearchToggle.getAttribute('aria-expanded') === 'true';
      const nextExpanded = !isExpanded;
      mobileSearchToggle.setAttribute('aria-expanded', String(nextExpanded));
      mobileSearchToggle.setAttribute('aria-label', nextExpanded ? 'بستن جستجو' : 'جستجو');

      if (nextExpanded) {
        closeMobilePanels();
        searchForm.classList.add('is-mobile-open');
        mobileSearchToggle.setAttribute('aria-expanded', 'true');
        mobileSearchToggle.setAttribute('aria-label', 'بستن جستجو');
        const input = searchForm.querySelector('input');
        input?.focus();
      } else {
        searchForm.classList.remove('is-mobile-open');
      }
    });
  }

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.header-mobile-tools') && !event.target.closest('.header-search')) {
      closeMobilePanels();
    }
  });

  if ('scrollRestoration' in history) {
    history.scrollRestoration = 'manual';
  }

  resetPageScroll();
  window.addEventListener('load', resetPageScroll);
  window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
      resetPageScroll();
    }
  });
  window.addEventListener('beforeunload', resetPageScroll);

  const toggleScrollButton = () => {
    if (!scrollToTopButton) return;
    if (window.scrollY > 400) {
      scrollToTopButton.classList.add('visible');
    } else {
      scrollToTopButton.classList.remove('visible');
    }
  };

  toggleScrollButton();
  window.addEventListener('scroll', toggleScrollButton, { passive: true });

  scrollToTopButton?.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
});
