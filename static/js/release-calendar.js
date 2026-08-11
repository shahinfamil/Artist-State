document.addEventListener('DOMContentLoaded', function () {
  const cells = document.querySelectorAll('.release-calendar__cell');
  if (cells.length) {
    const closeAll = () => cells.forEach((cell) => cell.classList.remove('is-open'));

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
  }

  const clockValue = document.getElementById('todayClockValue');
  if (clockValue) {
    const pad = (num) => num.toString().padStart(2, '0');
    const updateClock = () => {
      const now = new Date();
      const year = now.getFullYear();
      const shortYear = pad(year % 100);
      const month = pad(now.getMonth() + 1);
      const day = pad(now.getDate());
      const hours = pad(now.getHours());
      const minutes = pad(now.getMinutes());
      const seconds = pad(now.getSeconds());

      const yearElement = document.getElementById('todayClockDateYear');
      const monthElement = document.getElementById('todayClockDateMonth');
      const dayElement = document.getElementById('todayClockDateDay');
      const hourElement = document.getElementById('todayClockHour');
      const minuteElement = document.getElementById('todayClockMinute');
      const secondElement = document.getElementById('todayClockSecond');

      if (yearElement) yearElement.textContent = shortYear;
      if (monthElement) monthElement.textContent = month;
      if (dayElement) dayElement.textContent = day;
      if (hourElement) hourElement.textContent = hours;
      if (minuteElement) minuteElement.textContent = minutes;
      if (secondElement) secondElement.textContent = seconds;
    };

    updateClock();
    setInterval(updateClock, 1000);
  }
});
