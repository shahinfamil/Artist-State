document.addEventListener('DOMContentLoaded', function () {
  const cells = document.querySelectorAll('.release-calendar__cell');
  if (!cells.length) return;

  const closeAll = () => {
    cells.forEach((cell) => cell.classList.remove('is-open'));
  };

  cells.forEach((cell) => {
    const toggle = cell.querySelector('.release-calendar__cell-toggle');
    if (!toggle) return;

    toggle.addEventListener('click', function (event) {
      event.preventDefault();
      event.stopPropagation();
      const isOpen = cell.classList.contains('is-open');
      closeAll();
      if (!isOpen) {
        cell.classList.add('is-open');
      }
    });
  });

  document.addEventListener('click', function (event) {
    const clickedInside = Array.from(cells).some((cell) => cell.contains(event.target));
    if (!clickedInside) {
      closeAll();
    }
  });

  document.addEventListener('keydown', function (event) {
    if (event.key === 'Escape') {
      closeAll();
    }
  });
  
  // Genre card cover stack randomizer (moved from inline template)
  document.querySelectorAll('.genre-card-cover-stack').forEach(function (stack) {
    const images = Array.from(stack.querySelectorAll('img'));
    if (!images.length) return;

    const activeIndex = Math.floor(Math.random() * images.length);
    images.forEach(function (img, index) {
      const isActive = index === activeIndex;
      img.classList.toggle('is-active', isActive);
      img.style.opacity = '1';
      img.style.filter = isActive ? 'saturate(1.1) contrast(1.04)' : 'blur(0.5px) brightness(0.62)';
      img.style.transform = isActive ? 'translate(0, 0) scale(1.02) rotate(0deg)' : img.style.transform;
    });
  });

});
