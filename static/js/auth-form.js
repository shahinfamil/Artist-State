const authTabs = document.querySelectorAll('.auth-tab');
const authCard = document.getElementById('auth-card');
const loginFormPanel = document.getElementById('login-form-panel');
const registerFormPanel = document.getElementById('register-form-panel');
const loginForm = document.getElementById('auth-login-form');
const registerForm = document.getElementById('auth-register-form');
const loginUsernameInput = document.getElementById('login-username');
const loginPasswordInput = document.getElementById('login-password');
const registerUsernameInput = document.getElementById('register-username');
const registerEmailInput = document.getElementById('register-email');
const registerPasswordInput = document.getElementById('register-password');
const registerConfirmPasswordInput = document.getElementById('register-confirm-password');
const authFormSummary = document.getElementById('auth-form-summary');
const recoveryEmailInput = document.getElementById('forgot-email');
const recoveryStatus = document.getElementById('auth-recovery-status');
const passwordStrengthMeter = document.querySelectorAll('#register-password-strength-meter .auth-strength-segment');
const authValidationMessages = {
  username: '',
  email: '',
  password: '',
  confirm: ''
};
const passwordStrengthMeterContainer = document.getElementById('register-password-strength-meter');
const passwordStrengthText = document.getElementById('register-password-strength-text');

function detectTextLanguage(text) {
  const value = (text || '').toString().trim();
  if (!value) {
    return 'default';
  }

  if (/[\u0600-\u06FF]/.test(value)) {
    return 'fa';
  }

  if (/[A-Za-z]/.test(value) || /\d/.test(value)) {
    return 'en';
  }

  return 'default';
}

function applyAutoFontToElement(element) {
  if (!element) {
    return;
  }

  if (element.classList.contains('auth-field-password')) {
    element.classList.add('font-en');
    element.classList.remove('font-fa');
    element.style.fontFamily = 'var(--font-en)';
    return;
  }

  const source = element.value ?? element.textContent ?? element.innerText ?? element.getAttribute('placeholder') ?? '';
  const lang = detectTextLanguage(source);

  element.classList.toggle('font-en', lang === 'en');
  element.classList.toggle('font-fa', lang === 'fa');
}

function applyAutoFontToPage(root = document) {
  const scope = root.querySelectorAll ? root : document;
  const elements = scope.querySelectorAll ? scope.querySelectorAll('[data-auto-font="true"], .auth-field, .auth-field-feedback, .auth-strength-text, .auth-submit-button, .auth-tab, .auth-page-title, .auth-page-subtitle, .auth-error-message') : [];

  elements.forEach(applyAutoFontToElement);
}

function bindAutoFontToInputs() {
  document.querySelectorAll('.auth-field').forEach(field => {
    const apply = () => applyAutoFontToElement(field);
    field.addEventListener('input', apply);
    field.addEventListener('keyup', apply);
    field.addEventListener('paste', apply);
    field.addEventListener('change', apply);
  });
}

function resetRegistrationValidation() {
  Object.keys(authValidationMessages).forEach(key => {
    authValidationMessages[key] = '';
  });

  if (authFormSummary) {
    authFormSummary.innerHTML = '';
    authFormSummary.classList.remove('is-visible');
    authFormSummary.classList.remove('auth-form-summary--success');
  }

  if (passwordStrengthText) {
    passwordStrengthText.textContent = '';
    passwordStrengthText.className = 'auth-strength-text';
    applyAutoFontToElement(passwordStrengthText);
  }

  passwordStrengthMeter.forEach((segment) => {
    segment.classList.remove('filled', 'weak', 'medium', 'strong');
  });

  if (registerUsernameInput) {
    registerUsernameInput.setCustomValidity('');
  }
  if (registerEmailInput) {
    registerEmailInput.setCustomValidity('');
  }
  if (registerPasswordInput) {
    registerPasswordInput.setCustomValidity('');
  }
  if (registerConfirmPasswordInput) {
    registerConfirmPasswordInput.setCustomValidity('');
  }
}

function setAuthMode(mode, options = {}) {
  const preserveSummary = options.preserveSummary !== false;

  authTabs.forEach(tab => tab.classList.toggle('active', tab.dataset.action === mode));
  const isRegister = mode === 'register';

  authCard.classList.toggle('is-register', isRegister);

  if (!preserveSummary) {
    clearAuthFormSummary();
  }

  if (isRegister) {
    loginFormPanel.classList.remove('is-visible');
    registerFormPanel.classList.add('is-visible');
  } else {
    registerFormPanel.classList.remove('is-visible');
    loginFormPanel.classList.add('is-visible');
  }

  if (!isRegister && !preserveSummary) {
    registerForm.reset();
    resetRegistrationValidation();
  }

  applyAutoFontToPage(document);
}

if (authTabs.length) {
  authTabs.forEach(tab => {
    tab.addEventListener('click', () => setAuthMode(tab.dataset.action, { preserveSummary: false }));
  });
}

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

let usernameCheckTimer = null;
let loginUsernameCheckTimer = null;

function setFieldFeedback(element, message, type = '') {
  if (!element) {
    return;
  }

  element.textContent = message || '';
  element.className = 'auth-field-feedback';
  if (type === 'error') {
    element.classList.add('is-error');
  } else if (type === 'success') {
    element.classList.add('is-success');
  }
  applyAutoFontToElement(element);
}

function setFieldValidationState(field, state) {
  if (!field) {
    return;
  }

  field.classList.toggle('is-error', state === 'error');
  field.classList.toggle('is-success', state === 'success');
}

function clearFieldValidationState(field) {
  if (!field) {
    return;
  }

  field.classList.remove('is-error', 'is-success');
}

function updateAuthFormSummary() {
  if (!authFormSummary) {
    return;
  }

  const messages = Object.values(authValidationMessages).filter(Boolean);

  if (messages.length) {
    authFormSummary.innerHTML = messages.map(message => `<span>${message}</span>`).join('');
    authFormSummary.classList.add('is-visible');
    authFormSummary.classList.remove('auth-form-summary--success');
    return;
  }

  if (authFormSummary.innerHTML.trim()) {
    authFormSummary.classList.add('is-visible');
    authFormSummary.classList.toggle('auth-form-summary--success', authFormSummary.querySelector('.auth-form-summary__content--success') !== null);
    return;
  }

  authFormSummary.innerHTML = '';
  authFormSummary.classList.remove('is-visible');
  authFormSummary.classList.remove('auth-form-summary--success');
}

function clearAuthFormSummary() {
  if (!authFormSummary) {
    return;
  }

  authFormSummary.innerHTML = '';
  authFormSummary.classList.remove('is-visible');
  authFormSummary.classList.remove('auth-form-summary--success');
}

function showLoginFormSummary(message, type = 'error') {
  if (!authFormSummary) {
    return;
  }

  const icon = type === 'success' ? '✓' : '⚠';
  authFormSummary.innerHTML = `<span class="auth-form-summary__content auth-form-summary__content--${type}" role="alert"><span class="auth-form-summary__icon">${icon}</span> ${message}</span>`;
  authFormSummary.classList.add('is-visible');
  if (type === 'success') {
    authFormSummary.classList.add('auth-form-summary--success');
  } else {
    authFormSummary.classList.remove('auth-form-summary--success');
  }
}

function setRecoveryStatus(message, type = 'error') {
  if (!recoveryStatus) {
    return;
  }

  if (!message) {
    recoveryStatus.innerHTML = '';
    recoveryStatus.classList.remove('is-visible');
    return;
  }

  const icon = type === 'success' ? '✓' : '⚠';
  recoveryStatus.innerHTML = `
    <div class="auth-recovery-status__content auth-recovery-status__content--${type}" role="${type === 'success' ? 'status' : 'alert'}">
      <span class="auth-recovery-status__icon">${icon}</span>
      <span class="auth-recovery-status__text">${message}</span>
    </div>
  `;
  recoveryStatus.classList.add('is-visible');
}

function validateRecoveryEmail(value) {
  if (!recoveryEmailInput) {
    return false;
  }

  const normalizedValue = (value || '').trim();

  if (!normalizedValue) {
    recoveryEmailInput.setCustomValidity('');
    clearFieldValidationState(recoveryEmailInput);
    return false;
  }

  if (!isValidEmail(normalizedValue)) {
    recoveryEmailInput.setCustomValidity('فرمت ایمیل وارد شده صحیح نیست.');
    setRecoveryStatus('فرمت ایمیل وارد شده صحیح نیست. لطفاً ایمیل را درست وارد کنید.', 'error');
    setFieldValidationState(recoveryEmailInput, 'error');
    return false;
  }

  recoveryEmailInput.setCustomValidity('');
  setFieldValidationState(recoveryEmailInput, 'success');
  setRecoveryStatus('');
  return true;
}

function toggleRecoveryPopup(forceVisible) {
  const popup = document.getElementById('auth-recovery-popup');
  const recoveryTrigger = document.querySelector('[data-toggle-recovery-form]');
  if (!popup || !recoveryTrigger) {
    return;
  }

  const shouldShow = typeof forceVisible === 'boolean' ? forceVisible : popup.classList.contains('auth-recovery-popup--hidden');
  popup.classList.toggle('auth-recovery-popup--hidden', !shouldShow);
  popup.setAttribute('aria-hidden', shouldShow ? 'false' : 'true');
  recoveryTrigger.setAttribute('aria-expanded', shouldShow ? 'true' : 'false');

  document.body.classList.toggle('auth-modal-open', shouldShow);

  if (!shouldShow) {
    setRecoveryStatus('');
    if (recoveryEmailInput) {
      recoveryEmailInput.setCustomValidity('');
    }
    return;
  }

  if (recoveryEmailInput) {
    window.setTimeout(() => {
      validateRecoveryEmail(recoveryEmailInput.value);
    }, 0);
  }

  const focusable = Array.from(popup.querySelectorAll('input, button, [href], [tabindex]:not([tabindex="-1"])'))
    .filter(element => !element.hasAttribute('disabled') && element.getAttribute('aria-hidden') !== 'true');
  const firstFocusable = focusable[0];

  if (firstFocusable) {
    window.setTimeout(() => firstFocusable.focus(), 0);
  }
}

function attachRecoveryPopupInteractions() {
  const popup = document.getElementById('auth-recovery-popup');
  if (!popup) {
    return;
  }

  document.addEventListener('click', (event) => {
    const closeControl = event.target.closest('[data-close-recovery-popup]');
    if (!popup.classList.contains('auth-recovery-popup--hidden') && (closeControl || event.target === popup)) {
      event.preventDefault();
      event.stopPropagation();
      toggleRecoveryPopup(false);
    }
  }, true);
}

function handleRecoveryPopupKeydown(event) {
  const popup = document.getElementById('auth-recovery-popup');
  if (!popup || popup.classList.contains('auth-recovery-popup--hidden')) {
    return;
  }

  const focusable = Array.from(popup.querySelectorAll('input, button, [href], [tabindex]:not([tabindex="-1"])'))
    .filter(element => !element.hasAttribute('disabled') && element.getAttribute('aria-hidden') !== 'true');

  if (event.key === 'Escape') {
    event.preventDefault();
    toggleRecoveryPopup(false);
    return;
  }

  if (event.key === 'Tab' && focusable.length) {
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  }
}

const recoveryPopup = document.getElementById('auth-recovery-popup');
if (recoveryPopup) {
  document.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-toggle-recovery-form]');
    if (trigger) {
      event.preventDefault();
      toggleRecoveryPopup();
      return;
    }
  });

  attachRecoveryPopupInteractions();

  document.addEventListener('keydown', (event) => {
    const trigger = event.target.closest('[data-toggle-recovery-form]');
    if (trigger && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      toggleRecoveryPopup();
      return;
    }

    handleRecoveryPopupKeydown(event);
  });

  if (!recoveryPopup.classList.contains('auth-recovery-popup--hidden')) {
    recoveryPopup.setAttribute('aria-hidden', 'false');
    document.body.classList.add('auth-modal-open');
    const recoveryTrigger = document.querySelector('[data-toggle-recovery-form]');
    if (recoveryTrigger) {
      recoveryTrigger.setAttribute('aria-expanded', 'true');
    }

    window.setTimeout(() => {
      const focusable = Array.from(recoveryPopup.querySelectorAll('input, button, [href], [tabindex]:not([tabindex="-1"])'))
        .filter(element => !element.hasAttribute('disabled') && element.getAttribute('aria-hidden') !== 'true');
      if (focusable.length) {
        focusable[0].focus();
      }
    }, 0);
  }
}

function validateUsernameFormat(value) {
  const normalized = value.trim();
  const usernamePattern = /^[a-zA-Z0-9_]{3,20}$/;

  if (!normalized) {
    return { valid: false, message: 'نام کاربری را وارد کنید.', type: 'error' };
  }

  if (normalized.includes('@') || normalized.includes('.')) {
    return { valid: false, message: 'نام کاربری نمی‌تواند شبیه ایمیل باشد؛ فقط از حروف، عدد و زیرخط استفاده کنید.', type: 'error' };
  }

  if (!usernamePattern.test(normalized)) {
    return { valid: false, message: 'نام کاربری باید بین ۳ تا ۲۰ کاراکتر باشد و فقط شامل حروف، عدد و _ باشد.', type: 'error' };
  }

  return { valid: true, message: '', type: '' };
}

function checkUsernameAvailability() {
  const value = registerUsernameInput.value.trim();

  if (!value) {
    authValidationMessages.username = '';
    updateAuthFormSummary();
    registerUsernameInput.setCustomValidity('');
    clearFieldValidationState(registerUsernameInput);
    return;
  }

  const formatCheck = validateUsernameFormat(value);

  if (!formatCheck.valid) {
    registerUsernameInput.setCustomValidity(formatCheck.message);
    authValidationMessages.username = formatCheck.message;
    setFieldValidationState(registerUsernameInput, 'error');
    updateAuthFormSummary();
    return;
  }

  registerUsernameInput.setCustomValidity('');
  authValidationMessages.username = '';
  updateAuthFormSummary();

  if (usernameCheckTimer) {
    clearTimeout(usernameCheckTimer);
  }

  usernameCheckTimer = setTimeout(() => {
    fetch(`/check-username?username=${encodeURIComponent(value)}`)
      .then(response => response.json())
      .then(data => {
        if (data.taken) {
          registerUsernameInput.setCustomValidity('این نام کاربری انتخاب شده است.');
          authValidationMessages.username = data.message || 'این نام کاربری انتخاب شده است.';
          setFieldValidationState(registerUsernameInput, 'error');
        } else {
          registerUsernameInput.setCustomValidity('');
          authValidationMessages.username = '';
          setFieldValidationState(registerUsernameInput, 'success');
        }
        updateAuthFormSummary();
      })
      .catch(() => {
        registerUsernameInput.setCustomValidity('امکان بررسی نام کاربری وجود ندارد.');
        authValidationMessages.username = 'امکان بررسی نام کاربری وجود ندارد.';
        updateAuthFormSummary();
      });
  }, 300);
}

function checkLoginUsernameAvailability() {
  if (!loginUsernameInput) {
    return;
  }

  const value = loginUsernameInput.value.trim();

  if (!value) {
    loginUsernameInput.setCustomValidity('');
    clearAuthFormSummary();
    return;
  }

  loginUsernameInput.setCustomValidity('');

  if (loginUsernameCheckTimer) {
    clearTimeout(loginUsernameCheckTimer);
  }

  loginUsernameCheckTimer = setTimeout(() => {
    fetch(`/check-username?username=${encodeURIComponent(value)}`)
      .then(response => response.json())
      .then(data => {
        if (data.taken) {
          loginUsernameInput.setCustomValidity('');
          clearAuthFormSummary();
        } else {
          loginUsernameInput.setCustomValidity('چنین کاربری در سیستم ثبت نشده است.');
          showLoginFormSummary('چنین کاربری در سیستم ثبت نشده است.', 'error');
        }
      })
      .catch(() => {
        loginUsernameInput.setCustomValidity('امکان بررسی نام کاربری وجود ندارد.');
        showLoginFormSummary('امکان بررسی نام کاربری وجود ندارد.', 'error');
      });
  }, 250);
}

function updateRegisterEmailValidation() {
  const value = registerEmailInput.value.trim();
  applyAutoFontToElement(registerEmailInput);

  if (!value) {
    registerEmailInput.setCustomValidity('');
    authValidationMessages.email = '';
    clearFieldValidationState(registerEmailInput);
    updateAuthFormSummary();
    return;
  }
  if (!isValidEmail(value)) {
    registerEmailInput.setCustomValidity('فرمت آدرس ایمیل معتبر نیست. لطفاً مانند username@example.com وارد کنید.');
    authValidationMessages.email = 'فرمت آدرس ایمیل معتبر نیست. لطفاً مانند username@example.com وارد کنید.';
    setFieldValidationState(registerEmailInput, 'error');
  } else {
    registerEmailInput.setCustomValidity('');
    authValidationMessages.email = '';
    setFieldValidationState(registerEmailInput, 'success');
  }

  updateAuthFormSummary();
}

function attachRecoveryFormHandlers() {
  if (!recoveryEmailInput) {
    return;
  }

  recoveryEmailInput.addEventListener('input', () => {
    validateRecoveryEmail(recoveryEmailInput.value);
  });

  recoveryEmailInput.addEventListener('blur', () => {
    validateRecoveryEmail(recoveryEmailInput.value);
  });

  const recoveryForm = document.getElementById('auth-recovery-form');
  if (recoveryForm) {
    recoveryForm.addEventListener('submit', (event) => {
      event.preventDefault();

      const emailValue = recoveryEmailInput.value.trim();
      if (!validateRecoveryEmail(emailValue)) {
        return;
      }

      setRecoveryStatus('در حال ارسال درخواست...', 'success');

      fetch('/forgot-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: new URLSearchParams({
          email: emailValue,
        })
      })
      .then(response => {
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          return response.json();
        }
        return response.text().then(() => ({
          success: false,
          recovery_error: 'پاسخ سرور نامعتبر است. تلاش مجدد کنید.',
          show_recovery_popup: true,
        }));
      })
      .then(data => {
        toggleRecoveryPopup(false);
        if (data && data.recovery_error) {
          showLoginFormSummary(data.recovery_error, 'error');
          return;
        }

        if (data && data.recovery_message) {
          showLoginFormSummary(data.recovery_message, 'success');
          return;
        }

        showLoginFormSummary('خطایی رخ داد. لطفاً دوباره تلاش کنید.', 'error');
      })
      .catch(() => {
        toggleRecoveryPopup(false);
        showLoginFormSummary('امکان برقراری ارتباط با سرور وجود ندارد. لطفاً دوباره تلاش کنید.', 'error');
      });
    });
  }
}

function assessPasswordStrength(value) {
  const strength = {
    score: 0,
    label: 'ضعیف',
    colorClass: 'error'
  };

  if (!value) {
    return strength;
  }

  const lengthScore = Math.min(4, Math.floor(value.length / 2));
  const upper = /[A-Z]/.test(value);
  const lower = /[a-z]/.test(value);
  const number = /[0-9]/.test(value);
  const special = /[^A-Za-z0-9]/.test(value);

  strength.score = lengthScore + (upper ? 1 : 0) + (lower ? 1 : 0) + (number ? 1 : 0) + (special ? 1 : 0);

  if (strength.score >= 7) {
    strength.label = 'قوی';
    strength.colorClass = 'success';
  } else if (strength.score >= 5) {
    strength.label = 'متوسط';
    strength.colorClass = '';
  } else {
    strength.label = 'ضعیف';
    strength.colorClass = 'error';
  }

  return strength;
}

function updatePasswordStrength() {
  applyAutoFontToElement(registerPasswordInput);
  const value = registerPasswordInput.value.trim();
  const strength = assessPasswordStrength(value);
  const meterLevel = Math.min(4, Math.max(0, Math.ceil(strength.score / 2)));

  passwordStrengthMeter.forEach((segment, index) => {
    segment.classList.toggle('filled', index < meterLevel);
    segment.classList.toggle('weak', index < meterLevel && strength.label === 'ضعیف');
    segment.classList.toggle('medium', index < meterLevel && strength.label === 'متوسط');
    segment.classList.toggle('strong', index < meterLevel && strength.label === 'قوی');
  });

  if (!value) {
    registerPasswordInput.setCustomValidity('');
    passwordStrengthText.textContent = '';
    passwordStrengthText.className = 'auth-strength-text';
    authValidationMessages.password = '';
    applyAutoFontToElement(passwordStrengthText);
    clearFieldValidationState(registerPasswordInput);
    updateAuthFormSummary();
    return;
  }

  let message = '';
  let messageClass = '';

  if (strength.score < 7) {
    registerPasswordInput.setCustomValidity('برای ثبت نام، رمز باید حداقل ۶ کاراکتر و شامل حروف بزرگ، حروف کوچک، عدد و یک کاراکتر ویژه باشد.');
    message = 'رمز عبور ضعیف است. بهتر است از ترکیبی از حروف و اعداد و نمادها استفاده کنید.';
    messageClass = 'error';
    setFieldValidationState(registerPasswordInput, 'error');
  } else if (value.length < 6) {
    registerPasswordInput.setCustomValidity('رمز عبور باید حداقل ۶ کاراکتر باشد.');
    message = 'رمز عبور خیلی کوتاه است.';
    messageClass = 'error';
    setFieldValidationState(registerPasswordInput, 'error');
  } else {
    registerPasswordInput.setCustomValidity('');
    messageClass = strength.label === 'قوی' ? 'success' : '';
    setFieldValidationState(registerPasswordInput, 'success');
  }

  passwordStrengthText.textContent = strength.label === 'قوی' ? 'رمز عبور شما قوی است.' : strength.label === 'متوسط' ? 'رمز عبور متوسط است.' : 'رمز عبور ضعیف است.';
  passwordStrengthText.className = `auth-strength-text ${messageClass}`;
  authValidationMessages.password = message || '';

  applyAutoFontToElement(passwordStrengthText);
  updateAuthFormSummary();
}

if (loginUsernameInput) {
  loginUsernameInput.addEventListener('input', () => {
    if (!loginUsernameInput.value.trim()) {
      clearAuthFormSummary();
      // login validation color feedback removed per user request
    } else {
      checkLoginUsernameAvailability();
    }
  });
  // removed blur success coloring for login username
}

if (loginPasswordInput) {
  loginPasswordInput.addEventListener('input', () => {
    if (!loginPasswordInput.value.trim()) {
      clearAuthFormSummary();
      // login validation color feedback removed per user request
    } else {
      // keep behavior but no color change for login password
    }
  });
  // removed blur validation color for login password
}

registerUsernameInput.addEventListener('input', checkUsernameAvailability);
registerEmailInput.addEventListener('input', updateRegisterEmailValidation);
registerPasswordInput.addEventListener('input', () => {
  updatePasswordStrength();
  validateConfirmPassword();
});
registerConfirmPasswordInput.addEventListener('input', validateConfirmPassword);

function validateConfirmPassword() {
  const password = registerPasswordInput.value;
  const confirmPassword = registerConfirmPasswordInput.value;

  if (!confirmPassword) {
    registerConfirmPasswordInput.setCustomValidity('');
    authValidationMessages.confirm = '';
    clearFieldValidationState(registerConfirmPasswordInput);
    updateAuthFormSummary();
    return;
  }

  if (confirmPassword !== password) {
    registerConfirmPasswordInput.setCustomValidity('تکرار رمز عبور با رمز عبور مطابقت ندارد');
    authValidationMessages.confirm = 'تکرار رمز عبور با رمز عبور یکسان نیست.';
    setFieldValidationState(registerConfirmPasswordInput, 'error');
  } else {
    registerConfirmPasswordInput.setCustomValidity('');
    authValidationMessages.confirm = '';
    setFieldValidationState(registerConfirmPasswordInput, 'success');
  }

  updateAuthFormSummary();
}

function setPasswordMaskData(input, value) {
  input.dataset.rawValue = value || '';
  const visible = input.dataset.maskVisible === '1';
  input.value = visible ? input.dataset.rawValue : '*'.repeat(input.dataset.rawValue.length);
}

function updatePasswordMask(input) {
  if (!input || input.dataset.starMask !== '1') return;
  const visible = input.dataset.maskVisible === '1';
  input.value = visible ? input.dataset.rawValue : '*'.repeat((input.dataset.rawValue || '').length);
}

function onPasswordBeforeInput(event) {
  const input = event.target;
  if (input.dataset.starMask !== '1') return;

  const raw = input.dataset.rawValue || '';
  const start = input.selectionStart ?? raw.length;
  const end = input.selectionEnd ?? raw.length;
  let newRaw = raw;
  let caret = start;

  switch (event.inputType) {
    case 'insertText':
    case 'insertCompositionText':
      if (event.data == null) return;
      newRaw = raw.slice(0, start) + event.data + raw.slice(end);
      caret = start + event.data.length;
      break;
    case 'deleteContentBackward':
      if (start !== end) {
        newRaw = raw.slice(0, start) + raw.slice(end);
        caret = start;
      } else if (start > 0) {
        newRaw = raw.slice(0, start - 1) + raw.slice(end);
        caret = start - 1;
      }
      break;
    case 'deleteContentForward':
      if (start !== end) {
        newRaw = raw.slice(0, start) + raw.slice(end);
      } else {
        newRaw = raw.slice(0, start) + raw.slice(end + 1);
      }
      caret = start;
      break;
    case 'deleteByCut':
      newRaw = raw.slice(0, start) + raw.slice(end);
      caret = start;
      break;
    default:
      return;
  }

  event.preventDefault();
  setPasswordMaskData(input, newRaw);
  setTimeout(() => {
    const pos = Math.max(0, Math.min(newRaw.length, caret));
    input.setSelectionRange(pos, pos);
  }, 0);
}

function onPasswordPaste(event) {
  const input = event.target;
  if (input.dataset.starMask !== '1') return;

  event.preventDefault();
  const paste = event.clipboardData?.getData('text/plain') || '';
  const raw = input.dataset.rawValue || '';
  const start = input.selectionStart ?? raw.length;
  const end = input.selectionEnd ?? raw.length;
  const newRaw = raw.slice(0, start) + paste + raw.slice(end);

  setPasswordMaskData(input, newRaw);
  setTimeout(() => {
    const pos = start + paste.length;
    input.setSelectionRange(pos, pos);
  }, 0);
}

function enableStarMask(input) {
  if (!input || input.dataset.starMask === '1') return;
  input.dataset.starMask = '1';
  input.dataset.maskVisible = '0';
  input.dataset.rawValue = input.value || '';
  input.type = 'text';
  input.autocomplete = 'new-password';
  input.addEventListener('beforeinput', onPasswordBeforeInput);
  input.addEventListener('paste', onPasswordPaste);
  input.addEventListener('focus', () => updatePasswordMask(input));
  input.addEventListener('blur', () => updatePasswordMask(input));
  const form = input.closest('form');
  if (form) {
    form.addEventListener('submit', () => {
      if (input.dataset.starMask === '1') {
        input.value = input.dataset.rawValue || '';
      }
    });
  }
  updatePasswordMask(input);
}

document.querySelectorAll('.auth-field-password').forEach(enableStarMask);

document.querySelectorAll('.password-toggle').forEach(toggle => {
  toggle.addEventListener('click', () => {
    const targetInput = document.getElementById(toggle.dataset.target);
    if (!targetInput) return;

    if (targetInput.dataset.starMask === '1') {
      const isVisible = targetInput.dataset.maskVisible === '1';
      targetInput.dataset.maskVisible = isVisible ? '0' : '1';
      updatePasswordMask(targetInput);
      toggle.innerHTML = isVisible ? '👁' : '🙈';
      toggle.setAttribute('aria-label', isVisible ? 'نمایش رمز عبور' : 'مخفی کردن رمز عبور');
      return;
    }

    const isHidden = targetInput.type === 'password';
    targetInput.type = isHidden ? 'text' : 'password';
    targetInput.classList.toggle('auth-field-password', targetInput.type === 'password');
    toggle.innerHTML = isHidden ? '🙈' : '👁';
    toggle.setAttribute('aria-label', isHidden ? 'مخفی کردن رمز عبور' : 'نمایش رمز عبور');
  });
});

registerForm.addEventListener('submit', (event) => {
  checkUsernameAvailability();
  updateRegisterEmailValidation();
  updatePasswordStrength();
  validateConfirmPassword();
  if (registerConfirmPasswordInput.value !== registerPasswordInput.value) {
    registerConfirmPasswordInput.setCustomValidity('تکرار رمز عبور با رمز عبور مطابقت ندارد');
    event.preventDefault();
  }
  if (!registerForm.checkValidity()) {
    event.preventDefault();
  }
});

loginForm.addEventListener('submit', (event) => {
  if (!loginForm.checkValidity()) {
    event.preventDefault();
    if (loginUsernameInput && !loginUsernameInput.value.trim()) {
      showLoginFormSummary('نام کاربری را وارد کنید.', 'error');
    } else if (loginPasswordInput && !loginPasswordInput.value.trim()) {
      showLoginFormSummary('رمز عبور را وارد کنید.', 'error');
    }
  }
});

applyAutoFontToPage(document);
bindAutoFontToInputs();
attachRecoveryFormHandlers();
updateAuthFormSummary();
setAuthMode('login', { preserveSummary: true });
