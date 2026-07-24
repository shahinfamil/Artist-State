const AUTO_FONT_IGNORE_TAGS = ['SCRIPT', 'STYLE', 'SVG', 'PATH', 'IMG', 'CANVAS', 'VIDEO', 'AUDIO', 'IFRAME', 'NOSCRIPT', 'LINK', 'META'];
const AUTO_FONT_TEXT_SELECTORS = 'p, span, a, li, h1, h2, h3, h4, h5, h6, label, button, strong, em, b, small, div, td, th, option, pre, blockquote, figcaption, time';

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

function shouldSkipElement(element) {
  if (!element || element.nodeType !== 1) {
    return true;
  }

  if (element.hasAttribute('data-auto-font-ignore')) {
    return true;
  }

  const tagName = element.tagName.toUpperCase();
  if (AUTO_FONT_IGNORE_TAGS.includes(tagName)) {
    return true;
  }

  if (element.closest('.no-auto-font')) {
    return true;
  }

  return false;
}

function getAutoFontSource(element) {
  if (element.tagName && ['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName.toUpperCase())) {
    return element.value || element.getAttribute('placeholder') || '';
  }

  if (element.hasAttribute('title')) {
    return element.getAttribute('title') || '';
  }

  return element.textContent || '';
}

function applyAutoFontToElement(element) {
  if (shouldSkipElement(element)) {
    return;
  }

  const source = getAutoFontSource(element);
  const lang = detectTextLanguage(source);

  element.classList.toggle('font-en', lang === 'en');
  element.classList.toggle('font-fa', lang === 'fa');

  if (lang === 'en') {
    element.style.fontFamily = 'var(--font-en)';
  } else if (lang === 'fa') {
    element.style.fontFamily = 'var(--font-body)';
  } else {
    element.style.fontFamily = '';
  }
}

function processAutoFont(root = document) {
  if (!root || !root.querySelectorAll) {
    return;
  }

  const nodes = root.querySelectorAll(`${AUTO_FONT_TEXT_SELECTORS}, input, textarea, select`);
  nodes.forEach(applyAutoFontToElement);
}

function bindAutoFontEvents() {
  document.querySelectorAll('input, textarea, select').forEach(field => {
    ['input', 'keyup', 'paste', 'change'].forEach(eventName => {
      field.addEventListener(eventName, () => applyAutoFontToElement(field));
    });
  });
}

const autoFontObserver = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    if (mutation.type === 'childList') {
      mutation.addedNodes.forEach((node) => {
        if (node.nodeType === 1) {
          applyAutoFontToElement(node);
          processAutoFont(node);
        }
      });
    }

    if (mutation.type === 'characterData') {
      const parent = mutation.target.parentElement;
      if (parent) {
        applyAutoFontToElement(parent);
      }
    }
  });
});

function initAutoFont() {
  processAutoFont(document);
  bindAutoFontEvents();
  autoFontObserver.observe(document.body, {
    childList: true,
    subtree: true,
    characterData: true
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAutoFont);
} else {
  initAutoFont();
}
