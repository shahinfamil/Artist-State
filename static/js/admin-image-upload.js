function initializeImageUploadDropzones() {
  const dropzones = document.querySelectorAll('.image-url-dropzone');
  if (!dropzones.length) return;

  function findUploadUrl(dropzone) {
    const form = dropzone.closest('form');
    if (form && form.dataset.uploadUrl) {
      return form.dataset.uploadUrl;
    }
    if (dropzone.dataset.uploadUrl) {
      return dropzone.dataset.uploadUrl;
    }
    return '/admin/upload-media';
  }

  function setDropzoneState(dropzone, state) {
    dropzone.classList.toggle('dragover', state === 'over');
    const label = dropzone.querySelector('.image-url-dropzone-label');
    if (!label) return;
    if (state === 'over') {
      label.textContent = 'فایل را رها کنید تا آپلود شود';
    } else {
      label.textContent = 'فایل را بکشید و رها کنید یا کلیک کنید';
    }
  }

  function showUploadStatus(dropzone, message, isError) {
    const status = dropzone.querySelector('.image-upload-status');
    if (status) {
      status.textContent = message;
      status.classList.toggle('image-upload-status--error', isError);
      status.classList.toggle('image-upload-status--success', !isError);
      setTimeout(() => {
        status.textContent = '';
        status.classList.remove('image-upload-status--error', 'image-upload-status--success');
      }, 4000);
    }
  }

  function createHiddenFileInput(dropzone) {
    let input = dropzone.querySelector('input[type="file"]');
    if (!input) {
      input = document.createElement('input');
      input.type = 'file';
      input.accept = 'image/*';
      input.hidden = true;
      dropzone.appendChild(input);
    }
    return input;
  }

  function setImagePreview(dropzone, imageUrl) {
    const preview = dropzone.querySelector('.image-url-preview');
    if (!preview) return;

    if (!imageUrl) {
      preview.innerHTML = '';
      return;
    }

    const image = document.createElement('img');
    image.className = 'image-upload-preview';
    image.alt = 'پیش‌نمایش تصویر';
    image.src = imageUrl;
    image.onload = () => {
      preview.innerHTML = '';
      preview.appendChild(image);
    };
    image.onerror = () => {
      preview.innerHTML = '<span class="image-preview-error">قابل نمایش نیست</span>';
    };
  }

  function previewLocalFile(dropzone, file) {
    const preview = dropzone.querySelector('.image-url-preview');
    if (!preview) return;
    if (!file || !file.type.startsWith('image/')) {
      preview.innerHTML = '';
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const image = document.createElement('img');
      image.className = 'image-upload-preview';
      image.alt = 'پیش‌نمایش تصویر';
      image.src = reader.result;
      preview.innerHTML = '';
      preview.appendChild(image);
    };
    reader.readAsDataURL(file);
  }

  function findTextInput(dropzone) {
    const localInput = dropzone.querySelector('input[type="url"], input[type="text"]');
    if (localInput) return localInput;
    const targetName = dropzone.dataset.targetInput;
    if (targetName) {
      const form = dropzone.closest('form');
      if (form) {
        return form.querySelector(`input[name="${targetName}"]`);
      }
    }
    return null;
  }

  function updatePreviewFromInput(dropzone) {
    const input = findTextInput(dropzone);
    if (!input) return;
    const url = input.value.trim();
    if (url) {
      setImagePreview(dropzone, url);
    } else {
      setImagePreview(dropzone, null);
    }
  }

  function uploadImageFile(dropzone, file) {
    const uploadUrl = findUploadUrl(dropzone);
    const input = findTextInput(dropzone);
    const statusElement = dropzone.querySelector('.image-upload-status');

    if (!file || !input) return;

    previewLocalFile(dropzone, file);
    if (statusElement) {
      statusElement.textContent = '';
    }

    const formData = new FormData();
    formData.append('upload', file);
    formData.append('media_type', 'image');

    fetch(uploadUrl, {
      method: 'POST',
      body: formData,
    })
      .then((response) => response.json())
      .then((data) => {
        if (!data || !data.success || !data.url) {
          const message = data?.message || 'خطا در آپلود تصویر.';
          showUploadStatus(dropzone, message, true);
          return;
        }
        input.value = data.url;
        setImagePreview(dropzone, data.url);
        showUploadStatus(dropzone, 'تصویر با موفقیت آپلود شد.', false);
      })
      .catch((error) => {
        console.error('Image upload failed:', error);
        showUploadStatus(dropzone, 'خطا در ارتباط با سرور. دوباره تلاش کنید.', true);
      });
  }

  dropzones.forEach((dropzone) => {
    const fileInput = createHiddenFileInput(dropzone);
    const textInput = findTextInput(dropzone);

    if (!textInput) return;

    let statusElement = dropzone.querySelector('.image-upload-status');
    if (!statusElement) {
      statusElement = document.createElement('span');
      statusElement.className = 'image-upload-status';
      dropzone.appendChild(statusElement);
    }

    const openFilePicker = function () {
      fileInput.click();
    };

    dropzone.addEventListener('click', function (event) {
      openFilePicker();
    });

    dropzone.addEventListener('dragover', function (event) {
      event.preventDefault();
      setDropzoneState(dropzone, 'over');
      event.dataTransfer.dropEffect = 'copy';
    });

    dropzone.addEventListener('dragleave', function () {
      setDropzoneState(dropzone, 'normal');
    });

    dropzone.addEventListener('drop', function (event) {
      event.preventDefault();
      setDropzoneState(dropzone, 'normal');
      const file = event.dataTransfer.files && event.dataTransfer.files[0];
      if (!file) return;
      if (!file.type.startsWith('image/')) {
        showUploadStatus(dropzone, 'فقط فایل‌های تصویری قابل قبول هستند.', true);
        return;
      }
      uploadImageFile(dropzone, file);
    });

    dropzone.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openFilePicker();
      }
    });

    fileInput.addEventListener('change', function () {
      const file = fileInput.files && fileInput.files[0];
      if (!file) return;
      uploadImageFile(dropzone, file);
    });

    if (textInput) {
      textInput.addEventListener('input', function () {
        updatePreviewFromInput(dropzone);
      });
      updatePreviewFromInput(dropzone);
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initializeImageUploadDropzones);
} else {
  initializeImageUploadDropzones();
}
