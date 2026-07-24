document.addEventListener('DOMContentLoaded', function () {
  const loginForm = document.querySelector('.login-card');
  if (!loginForm) return;

  loginForm.addEventListener('submit', function () {
    const submitBtn = loginForm.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'در حال ورود...';
    }
  });
});
