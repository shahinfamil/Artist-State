document.addEventListener('DOMContentLoaded', function () {
  const genreCheckboxes = document.querySelectorAll('.genre-checkbox-input');
  const customInput = document.getElementById('genre-custom-input');
  const resultInput = document.getElementById('genre-result');
  const musicVideoCheckboxes = document.querySelectorAll('input[name="youtube_url_is_music_video"], input[name="youtube_url_secondary_is_music_video"]');

  if (!genreCheckboxes.length || !customInput || !resultInput) return;

  function updateGenreResult() {
    const selectedGenres = Array.from(genreCheckboxes)
      .filter(cb => cb.checked)
      .map(cb => cb.value.trim());

    const customGenres = customInput.value
      .split(',')
      .map(g => g.trim())
      .filter(g => g);

    const allGenres = [...new Set([...selectedGenres, ...customGenres])];
    resultInput.value = allGenres.join(', ');
  }

  function syncMusicVideoCheckboxes(event) {
    if (!event.target.checked) return;
    musicVideoCheckboxes.forEach((checkbox) => {
      if (checkbox !== event.target) {
        checkbox.checked = false;
      }
    });
  }

  genreCheckboxes.forEach(checkbox => {
    checkbox.addEventListener('change', updateGenreResult);
  });

  customInput.addEventListener('input', updateGenreResult);

  musicVideoCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener('change', syncMusicVideoCheckboxes);
  });

  updateGenreResult();
});
