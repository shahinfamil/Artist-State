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
});
