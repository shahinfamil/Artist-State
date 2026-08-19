document.addEventListener('DOMContentLoaded', function(){
  try {
    function shouldTicker(item) {
      if (!item || !item.textContent || !item.textContent.trim()) return false;

      var availableWidth = item.clientWidth || item.getBoundingClientRect().width || 0;
      if (!availableWidth) return false;

      var overflow = item.scrollWidth - availableWidth;
      return overflow > 2;
    }

    function getTextWidth(text, font) {
      var canvas = document.createElement('canvas');
      var context = canvas.getContext('2d');
      context.font = font || '14px Inter, "Segoe UI", sans-serif';
      return context.measureText(text).width;
    }

    function initTicker(item) {
      if (!item || item.querySelector('.track-album-ticker-wrap')) return;
      if (!shouldTicker(item)) return;

      item.style.direction = 'rtl';
      item.style.textAlign = 'right';

      var text = item.textContent.trim();
      var wrapper = document.createElement('span');
      wrapper.className = 'track-album-ticker-wrap';
      wrapper.style.direction = 'rtl';
      wrapper.style.textAlign = 'right';
      wrapper.style.width = '100%';

      var inner = document.createElement('span');
      inner.className = 'track-album-ticker-inner';
      inner.style.direction = 'rtl';
      inner.style.textAlign = 'right';
      inner.style.unicodeBidi = 'plaintext';
      inner.textContent = text;

      var font = window.getComputedStyle(item).font;
      var textWidth = getTextWidth(text, font);
      var forceWidth = Math.max(textWidth + 50, item.clientWidth + 40);
      inner.style.minWidth = forceWidth + 'px';
      inner.style.width = forceWidth + 'px';

      wrapper.appendChild(inner);
      item.textContent = '';
      item.appendChild(wrapper);

      var distance = forceWidth + 30;
      var speed = 22;
      var duration = Math.max(6, Math.round(distance / speed));
      inner.style.setProperty('--marquee-distance', distance + 'px');
      inner.style.setProperty('--marquee-duration', duration + 's');
      wrapper.classList.add('is-scrolling');
    }

    var items = document.querySelectorAll('.track-album');
    items.forEach(initTicker);

    var resizeTimer;
    window.addEventListener('resize', function(){
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(function(){
        items.forEach(function(item){
          if (item.querySelector('.track-album-ticker-wrap')) {
            if (!shouldTicker(item)) {
              item.innerHTML = item.querySelector('.track-album-ticker-inner')?.textContent || item.textContent || '';
            } else {
              initTicker(item);
            }
          } else {
            initTicker(item);
          }
        });
      }, 120);
    });
  } catch (e) { console.error('album ticker', e); }
});
