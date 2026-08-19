document.addEventListener('DOMContentLoaded', function(){
  try {
    document.querySelectorAll('.track-title').forEach(function(title){
      title.style.direction = 'ltr';
      title.style.textAlign = 'center';
      title.style.whiteSpace = 'normal';
      title.style.overflow = 'visible';
      title.style.textOverflow = 'clip';
      title.style.display = 'block';
      title.style.width = 'auto';
      title.style.maxWidth = '100%';
      title.style.minWidth = '0';
      title.style.animation = 'none';
      title.style.transform = 'none';
    });
  } catch (e) {
    console.error('Title marquee disabled', e);
  }
});
