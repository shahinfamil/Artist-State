document.addEventListener('DOMContentLoaded', function () {
  var collapsibleSection = document.querySelector('.wiki-biography-section[data-collapsible]');
  if (!collapsibleSection) return;

  var content = collapsibleSection.querySelector('.wiki-biography-content');
  var toggleButton = collapsibleSection.querySelector('.wiki-biography-collapse-toggle');
  if (!content || !toggleButton) return;

  var collapsedHeight = 280;
  if (content.scrollHeight <= collapsedHeight + 8) {
    toggleButton.style.display = 'none';
    return;
  }

  toggleButton.addEventListener('click', function () {
    var isExpanded = collapsibleSection.classList.toggle('is-expanded');
    toggleButton.textContent = isExpanded ? 'بستن' : 'نمایش بیشتر';
    toggleButton.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
  });
});
