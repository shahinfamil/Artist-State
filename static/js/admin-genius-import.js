document.addEventListener('DOMContentLoaded', function () {
  const form = document.querySelector('.admin-form');
  if (!form) return;

  const submitBtn = form.querySelector('#import-submit-btn');
  if (!submitBtn) return;

  form.addEventListener('submit', function () {
    submitBtn.disabled = true;
    submitBtn.textContent = 'در حال دریافت از Genius… ممکن است چند دقیقه طول بکشد';
  });
});
