window.TRACK_HISTORY = window.TRACK_HISTORY || {};

document.addEventListener('DOMContentLoaded', function () {
  const tabButtons = document.querySelectorAll('.video-tab-button');
  const tabPanels = document.querySelectorAll('.video-tab-panel');

  if (!tabButtons.length || !tabPanels.length) {
    return;
  }

  tabButtons.forEach((button) => {
    button.addEventListener('click', function () {
      const target = this.dataset.videoTab;
      tabButtons.forEach((btn) => btn.classList.toggle('active', btn === this));
      tabPanels.forEach((panel) => {
        panel.classList.toggle('active', panel.id === `video-tab-${target}`);
      });
    });
  });
});
