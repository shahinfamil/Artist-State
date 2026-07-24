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

function resetPageScroll() {
  window.scrollTo(0, 0);
  document.documentElement.scrollTop = 0;
  document.body.scrollTop = 0;
}

document.addEventListener("DOMContentLoaded", () => {
  const scrollToTopButton = document.getElementById('scroll-to-top');

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
