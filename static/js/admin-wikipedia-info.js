function initAdminWikipediaInfo() {
  const form = document.getElementById('wikipedia-info-form');
  if (!form) return;

  const container = document.getElementById('infobox-rows');
  const addButton = document.getElementById('add-infobox-row');
  const messageBox = document.getElementById('wikipedia-info-message');
  const titleElement = document.querySelector('.wiki-summary-value--title');
  const imageElement = document.getElementById('wiki-summary-image');
  const refreshStatus = document.getElementById('social-refresh-status');
  const refreshButtons = document.querySelectorAll('.refresh-social-counts');
  const refreshAllButton = document.querySelector('.refresh-all-social-counts');
  const editButtons = document.querySelectorAll('.edit-social');
  const refreshUrl = form.dataset.refreshUrl || '';
  const uploadMediaUrl = form.dataset.uploadUrl || '/admin/wikipedia-info/upload-media';
const wikipediaImageUploadInput = document.getElementById('wikipedia-image-upload-input');
    const wikipediaImageUrlInput = form.querySelector('input[name="wikipedia_image_url"]');
    const imageUrlDropZone = document.getElementById('wikipedia-image-drop-area');

  function showMessage(text, type = 'success') {
    if (!messageBox) return;
    messageBox.textContent = text;
    messageBox.className = 'wiki-info-message wiki-info-message--' + type;
    window.setTimeout(() => {
      messageBox.textContent = '';
      messageBox.className = 'wiki-info-message';
    }, 4000);
  }

  function updatePreview(data) {
    if (titleElement && data.title !== undefined) {
      titleElement.textContent = data.title || '—';
    }
    if (imageElement) {
      if (data.image_url) {
        imageElement.src = data.image_url;
        imageElement.style.display = 'block';
      } else {
        imageElement.style.display = 'none';
      }
    }
  }


  function setRefreshStatus(message, isError) {
    if (!refreshStatus) return;
    refreshStatus.textContent = message;
    refreshStatus.className = isError ? 'form-hint form-hint--error' : 'form-hint form-hint--success';
    window.setTimeout(() => {
      refreshStatus.textContent = '';
      refreshStatus.className = 'form-hint';
    }, 4000);
  }

  function setRowDisplayValue(field, value) {
    const row = document.querySelector(`.social-row[data-field="${field}"]`);
    const display = row && row.querySelector('.social-count-display');
    const hidden = form.querySelector(`input[name="${field}"]`);
    if (display) {
      display.textContent = value !== null && value !== undefined ? value : '';
    }
    if (hidden) {
      hidden.value = value !== null && value !== undefined ? value : '';
    }
  }

  function setRowStatus(field, message, statusType) {
    const row = document.querySelector(`.social-row[data-field="${field}"]`);
    const status = row && row.querySelector('.social-status');
    if (!status) return;
    status.textContent = message;
    status.className = 'social-status';
    if (message && statusType) {
      status.classList.add(`social-status--${statusType}`);
    }
  }

  function clearRowStatus(field) {
    setRowStatus(field, '', false);
  }

  function clearAllRowStatuses() {
    [
      'instagram_followers',
      'youtube_subscribers',
      'facebook_followers',
      'spotify_followers',
      'soundcloud_followers',
      'x_followers',
      'tiktok_followers',
    ].forEach(clearRowStatus);
  }

  function updateSocialInputs(data) {
    if (!data) return;
    [
      'instagram_followers',
      'youtube_subscribers',
      'facebook_followers',
      'spotify_followers',
      'soundcloud_followers',
      'x_followers',
      'tiktok_followers',
    ].forEach((key) => {
      if (data[key] !== undefined) {
        setRowDisplayValue(key, data[key]);
      }
    });
  }

  function parseSocialCount(value) {
    if (value === null || value === undefined) return null;
    const text = String(value).trim();
    if (!text) return null;
    const normalized = text.replace(/,/g, '').replace(/[^0-9\-]/g, '');
    return normalized === '' ? null : Number(normalized);
  }

  function formatDelta(value) {
    if (value === null || value === undefined || Number.isNaN(value)) return '';
    const sign = value > 0 ? '+' : '';
    return sign + Math.abs(value).toLocaleString('en-US');
  }

  function showUploadError(message) {
    showMessage(message, 'error');
  }

  async function uploadWikipediaImage(file) {
    if (!file || !wikipediaImageUploadInput || !wikipediaImageUrlInput) return;
    const formData = new FormData();
    formData.append('upload', file);
    formData.append('media_type', 'image');

    try {
      const response = await fetch(uploadMediaUrl, {
        method: 'POST',
        body: formData,
      });
      const data = await response.json();
      if (!response.ok || !data || !data.url) {
        console.error('Upload failed', data);
        showUploadError(data.message || 'خطا در آپلود تصویر.');
        return;
      }

      wikipediaImageUrlInput.value = data.url;
      wikipediaImageUrlInput.dispatchEvent(new Event('input', { bubbles: true }));
      showMessage('تصویر با موفقیت آپلود شد و لینک آن تنظیم شد.');
    } catch (error) {
      console.error('Upload error', error);
      showUploadError('خطا در انتقال تصویر به سرور. دوباره تلاش کنید.');
    }
  }

  function setupWikipediaImageUpload() {
    if (!wikipediaImageUploadInput) return;

    const openFilePicker = () => wikipediaImageUploadInput.click();
    const setDropzoneState = (isOver) => {
      if (!imageUrlDropZone) return;
      imageUrlDropZone.classList.toggle('dragover', isOver);
    };

    if (imageUrlDropZone) {
      imageUrlDropZone.addEventListener('click', function () {
        openFilePicker();
      });

      imageUrlDropZone.addEventListener('dragover', function (event) {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
        setDropzoneState(true);
      });

      imageUrlDropZone.addEventListener('dragleave', function () {
        setDropzoneState(false);
      });

      imageUrlDropZone.addEventListener('drop', function (event) {
        event.preventDefault();
        setDropzoneState(false);
        const file = event.dataTransfer.files && event.dataTransfer.files[0];
        if (!file) return;
        if (!file.type.startsWith('image/')) {
          showUploadError('فقط فایل‌های تصویری قابل قبول هستند.');
          return;
        }
        uploadWikipediaImage(file);
      });

      imageUrlDropZone.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openFilePicker();
        }
      });
    }

    wikipediaImageUploadInput.addEventListener('change', function (event) {
      const file = event.target.files && event.target.files[0];
      if (!file) return;
      uploadWikipediaImage(file);
    });
  }

  async function refreshSocialCounts(button, options = {}) {
    if (!button || !refreshUrl) return { success: false };
    const platform = button.dataset.platform || 'instagram';
    const fieldByPlatform = {
      instagram: 'instagram_followers',
      youtube: 'youtube_subscribers',
      facebook: 'facebook_followers',
      spotify: 'spotify_followers',
      soundcloud: 'soundcloud_followers',
      x: 'x_followers',
      tiktok: 'tiktok_followers',
    };
    const field = fieldByPlatform[platform];
    const row = document.querySelector(`.social-row[data-field="${field}"]`);
    const oldCount = row ? parseSocialCount(row.querySelector('.social-count-display')?.textContent) : null;
    const originalText = button.textContent;
    const silent = options.silent === true;

    button.disabled = true;
    button.textContent = '⏳ در حال استخراج...';
    if (!silent) {
      setRefreshStatus(`در حال استخراج آمار ${platform}...`, false);
    }

    let responseData = { success: false, message: 'پاسخ سرور معتبر نبود.', extracted: [], failed: [] };
    try {
      const response = await fetch(refreshUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ platform }),
      });
      try {
        responseData = await response.json();
      } catch (error) {
        console.error('Invalid JSON response for social refresh', error);
      }
    } catch (error) {
      console.error('Social refresh failed', error);
      if (!silent) {
        setRefreshStatus('ارتباط با سرور برقرار نشد. دوباره تلاش کنید.', true);
      }
      return { success: false, platform, field, error };
    }

    updateSocialInputs(responseData);

    const extracted = Array.isArray(responseData.extracted) ? responseData.extracted : [];
    const failed = Array.isArray(responseData.failed) ? responseData.failed : [];
    const extractedFields = extracted.map((value) => fieldByPlatform[value] || value);
    const failedFields = failed.map((value) => fieldByPlatform[value] || value);
    const relevantFields = Array.from(new Set([...extractedFields, ...failedFields]));
    relevantFields.forEach(clearRowStatus);

    extractedFields.forEach((fieldKey) => {
      const newCount = parseSocialCount(responseData[fieldKey]);
      if (oldCount !== null && newCount !== null && fieldKey === field) {
        const diff = newCount - oldCount;
        if (diff > 0) {
          setRowStatus(fieldKey, formatDelta(diff), 'positive');
        } else if (diff < 0) {
          setRowStatus(fieldKey, formatDelta(diff), 'negative');
        } else {
          setRowStatus(fieldKey, 'بدون تغییر', 'success');
        }
      } else {
        setRowStatus(fieldKey, 'به‌روز شد', 'success');
      }
    });
    failedFields.forEach((fieldKey) => setRowStatus(fieldKey, 'عدم استخراج', 'error'));

    if (!silent) {
      if (responseData.success) {
        const extractedLabel = extractedFields.length ? extractedFields.join('، ') : 'هیچ پلتفرمی';
        const failedLabel = failedFields.length ? failedFields.join('، ') : 'هیچ پلتفرمی';
        setRefreshStatus(`${responseData.message || 'آمار اجتماعی استخراج شد.'}\nپلتفرم‌های موفق: ${extractedLabel}\nپلتفرم‌های ناموفق: ${failedLabel}`, false);
      } else {
        setRefreshStatus(responseData.message || 'خطا در استخراج آمار اجتماعی.', true);
      }
    }

    button.disabled = false;
    button.textContent = originalText;

    return { success: responseData.success, platform, field, extractedFields, failedFields, data: responseData };
  }

  function toggleInlineEdit(button) {
    const field = button.dataset.field;
    const row = document.querySelector(`.social-row[data-field="${field}"]`);
    if (!row) return;
    const displayCell = row.querySelector('td:nth-child(2)');
    const hidden = form.querySelector(`input[name="${field}"]`);
    if (!displayCell || !hidden) return;

    const isEditing = button.dataset.editing === 'true';
    if (isEditing) {
      const input = row.querySelector('.social-count-input');
      if (!input) return;
      const newValue = input.value.trim();
      hidden.value = newValue;
      const span = document.createElement('span');
      span.className = 'social-count-display';
      span.textContent = newValue;
      input.replaceWith(span);
      button.textContent = '✏️';
      button.title = 'ویرایش';
      button.dataset.editing = 'false';
      return;
    }

    const currentValue = hidden.value || '';
    const input = document.createElement('input');
    input.type = 'number';
    input.min = '0';
    input.value = currentValue;
    input.className = 'social-count-input';
    input.style.width = '100px';

    const currentDisplay = row.querySelector('.social-count-display');
    if (currentDisplay) {
      currentDisplay.replaceWith(input);
    } else {
      displayCell.textContent = '';
      displayCell.appendChild(input);
    }

    button.textContent = '💾';
    button.title = 'ذخیره';
    button.dataset.editing = 'true';
  }

  function insertText(textarea, text, selectStartOffset = 0, selectEndOffset = 0) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    textarea.value = value.slice(0, start) + text + value.slice(end);
    textarea.focus();
    const newStart = start + selectStartOffset;
    const newEnd = textarea.value.length - (value.length - end) - selectEndOffset;
    textarea.setSelectionRange(newStart, newEnd);
  }

  function wrapSelection(textarea, before, after) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    const selected = value.slice(start, end) || 'متن شما';
    const wrapped = before + selected + after;
    textarea.value = value.slice(0, start) + wrapped + value.slice(end);
    textarea.focus();
    textarea.setSelectionRange(start + before.length, start + before.length + selected.length);
  }

  function toggleLinePrefix(textarea, prefix) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const value = textarea.value;
    const selected = value.slice(start, end) || value;
    const lines = selected.split('\n');
    const formatted = lines.map((line) => {
      if (!line.trim()) return line;
      return prefix + line.replace(/^\s*/, '');
    }).join('\n');
    textarea.value = value.slice(0, start) + formatted + value.slice(end);
    textarea.focus();
    textarea.setSelectionRange(start, start + formatted.length);
  }

  function insertLink(textarea) {
    const url = window.prompt('لینک را وارد کنید (https://...)');
    if (!url) return;
    const label = window.prompt('متن لینک را وارد کنید', 'لینک');
    insertText(textarea, `[${label || 'لینک'}](${url})`, 0, 0);
  }

  function insertImage(textarea) {
    const url = window.prompt('آدرس تصویر را وارد کنید (https://...)');
    if (!url) return;
    const alt = window.prompt('متن جایگزین تصویر', 'تصویر');
    insertText(textarea, `![${alt || 'تصویر'}](${url})`, 0, 0);
  }

  function insertVideo(textarea) {
    const url = window.prompt('آدرس ویدیو را وارد کنید (https://...)');
    if (!url) return;
    const caption = window.prompt('متن توضیحی ویدیو', 'ویدیو');
    const videoHtml = `\n<video controls style="max-width:100%; border-radius: 16px; margin: 12px 0;" src="${url}"></video>\n`;
    insertText(textarea, videoHtml, 0, 0);
  }

  function toggleCodeBlock(textarea) {
    wrapSelection(textarea, '```\n', '\n```');
  }

  function chooseTextColor(textarea) {
    const color = window.prompt('کد رنگ یا نام رنگ را وارد کنید، مثلاً #FF6B6B', '#FF6B6B');
    if (!color) return;
    wrapSelection(textarea, `<span style="color: ${color};">`, '</span>');
  }

  function toggleHeading(textarea, level) {
    const prefix = '#'.repeat(level) + ' ';
    toggleLinePrefix(textarea, prefix);
  }

  function toggleBlockquote(textarea) {
    toggleLinePrefix(textarea, '> ');
  }

  function toggleFullscreen(wrapper, button) {
    if (!wrapper) return;
    wrapper.classList.toggle('textarea-editor-fullscreen');
    if (button) {
      button.textContent = wrapper.classList.contains('textarea-editor-fullscreen') ? '⤡' : '⤢';
      button.title = wrapper.classList.contains('textarea-editor-fullscreen') ? 'خروج از حالت تمام صفحه' : 'تمام صفحه';
    }
  }

  function createTextareaToolbar(textarea) {
    const toolbar = document.createElement('div');
    toolbar.className = 'textarea-editor-toolbar';

    const buttons = [
      { label: 'H1', title: 'عنوان بزرگ', action: () => toggleHeading(textarea, 1) },
      { label: 'H2', title: 'عنوان متوسط', action: () => toggleHeading(textarea, 2) },
      { label: 'B', title: 'ضخیم', action: () => wrapSelection(textarea, '**', '**') },
      { label: 'I', title: 'مایل', action: () => wrapSelection(textarea, '*', '*') },
      { label: 'U', title: 'زیرخط', action: () => wrapSelection(textarea, '__', '__') },
      { label: 'S', title: 'خط خورده', action: () => wrapSelection(textarea, '~~', '~~') },
      { label: '•', title: 'لیست گلوله‌ای', action: () => toggleLinePrefix(textarea, '- ') },
      { label: '1.', title: 'لیست شماره‌دار', action: () => toggleLinePrefix(textarea, '1. ') },
      { label: '“”', title: 'نقل قول', action: () => toggleBlockquote(textarea) },
      { label: '</>', title: 'بلوک کد', action: () => toggleCodeBlock(textarea) },
      { label: 'لینک', title: 'افزودن لینک', action: () => insertLink(textarea) },
      { label: 'تصویر', title: 'افزودن تصویر', action: () => insertImage(textarea) },
      { label: 'ویدیو', title: 'افزودن ویدیو', action: () => insertVideo(textarea) },
      { label: '⤢', title: 'تمام صفحه', action: (button) => toggleFullscreen(textarea.parentNode, button) },
    ];

    buttons.forEach(({ label, title, action }) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'textarea-editor-button';
      button.textContent = label;
      button.title = title;
      button.addEventListener('click', () => action(button));
      toolbar.appendChild(button);
    });

    return toolbar;
  }

  function setupTextareaEditor(textarea) {
    if (!textarea || textarea.dataset.editorInitialized) return;
    if (textarea.id === 'wikipedia-timeline-section') return;
    const wrapper = document.createElement('div');
    wrapper.className = 'textarea-editor-wrapper';
    const toolbar = createTextareaToolbar(textarea);
    textarea.classList.add('textarea-editor-textarea');
    textarea.parentNode.insertBefore(wrapper, textarea);
    wrapper.appendChild(toolbar);
    wrapper.appendChild(textarea);
    textarea.dataset.editorInitialized = '1';
  }

  function renderInfoboxRows(items) {
    container.innerHTML = '';
    if (!items || !items.length) {
      const row = document.createElement('div');
      row.className = 'infobox-row';
      row.draggable = false;
      row.innerHTML = '<button type="button" class="remove-infobox-row" title="حذف">🗑</button>' +
        '<input type="text" name="infobox_key[]" placeholder="عنوان">' +
        '<input type="text" name="infobox_value[]" placeholder="مقدار">' +
        '<span class="infobox-row-handle" title="جابجایی">☰</span>';
      container.appendChild(row);
      setupDragEvents(row);
      return;
    }

    items.forEach(function (item) {
      const row = document.createElement('div');
      row.className = 'infobox-row';
      row.draggable = false;
      row.innerHTML = '<button type="button" class="remove-infobox-row" title="حذف">🗑</button>' +
        '<input type="text" name="infobox_key[]" value="' + (item.key || '') + '" placeholder="عنوان">' +
        '<input type="text" name="infobox_value[]" value="' + (item.value || '') + '" placeholder="مقدار">' +
        '<span class="infobox-row-handle" title="جابجایی">☰</span>';
      container.appendChild(row);
      setupDragEvents(row);
    });
  }

  function setupDragEvents(row) {
    row.draggable = false;
    const inputs = row.querySelectorAll('input');
    const handle = row.querySelector('.infobox-row-handle');

    function disableDrag() {
      row.draggable = false;
    }

    function enableDrag() {
      row.draggable = true;
    }

    inputs.forEach(function (input) {
      input.addEventListener('focus', disableDrag);
      input.addEventListener('blur', function () {
        if (!row.classList.contains('dragging')) {
          enableDrag();
        }
      });
    });

    if (handle) {
      handle.addEventListener('pointerdown', function () {
        enableDrag();
      });

      handle.addEventListener('pointerup', function () {
        if (!row.classList.contains('dragging')) {
          disableDrag();
        }
      });
    }

    row.addEventListener('dragstart', function () {
      row.classList.add('dragging');
    });

    row.addEventListener('dragend', function () {
      row.classList.remove('dragging');
      disableDrag();
    });
  }

  function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.infobox-row:not(.dragging)')];
    return draggableElements.reduce((closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset: offset, element: child };
      }
      return closest;
    }, { offset: Number.NEGATIVE_INFINITY }).element;
  }

  function initializeEditorToolbars() {
    const textareas = form.querySelectorAll('textarea');
    textareas.forEach(setupTextareaEditor);
  }

  container.querySelectorAll('.infobox-row').forEach(setupDragEvents);

  container.addEventListener('click', function (event) {
    if (event.target.classList.contains('remove-infobox-row')) {
      event.target.closest('.infobox-row').remove();
    }
  });

  container.addEventListener('dragover', function (event) {
    event.preventDefault();
    const afterElement = getDragAfterElement(container, event.clientY);
    const draggable = document.querySelector('.infobox-row.dragging');
    if (!draggable) {
      return;
    }
    if (!afterElement) {
      container.appendChild(draggable);
    } else {
      container.insertBefore(draggable, afterElement);
    }
  });

  addButton.addEventListener('click', function () {
    const row = document.createElement('div');
    row.className = 'infobox-row';
    row.draggable = false;
    row.innerHTML = '<button type="button" class="remove-infobox-row" title="حذف">🗑</button>' +
      '<input type="text" name="infobox_key[]" placeholder="عنوان">' +
      '<input type="text" name="infobox_value[]" placeholder="مقدار">' +
      '<span class="infobox-row-handle" title="جابجایی">☰</span>';
    container.appendChild(row);
    setupDragEvents(row);
  });

  function attachSocialHandlers() {
    refreshButtons.forEach((button) => {
      button.addEventListener('click', () => refreshSocialCounts(button));
    });

    if (refreshAllButton) {
      refreshAllButton.addEventListener('click', async () => {
        const buttons = Array.from(document.querySelectorAll('.refresh-social-counts'));
        const inProgressText = '⏳ در حال استخراج...';
        const originalButtonTexts = new Map();

        buttons.forEach((btn) => {
          originalButtonTexts.set(btn, btn.textContent);
          btn.disabled = true;
          btn.textContent = inProgressText;
        });

        const requests = buttons.map((btn) => refreshSocialCounts(btn, { silent: true }));
        const results = await Promise.all(requests);

        buttons.forEach((btn) => {
          const originalText = originalButtonTexts.get(btn) || '🔄';
          btn.disabled = false;
          btn.textContent = originalText;
        });

        const successPlatforms = results.filter((result) => result && result.success).map((result) => result.platform);
        const failedPlatforms = results.filter((result) => result && !result.success).map((result) => result.platform);

        setRefreshStatus(
          `بروزرسانی همه پلتفرم‌ها انجام شد. موفق: ${successPlatforms.length ? successPlatforms.join('، ') : 'هیچ‌کدام'}. ناموفق: ${failedPlatforms.length ? failedPlatforms.join('، ') : 'هیچ‌کدام'}.`,
          failedPlatforms.length > 0,
        );
      });
    }

    editButtons.forEach((button) => {
      button.addEventListener('click', () => toggleInlineEdit(button));
    });
  }

  initializeEditorToolbars();
  setupWikipediaImageUpload();
  attachSocialHandlers();

  form.addEventListener('click', function () {
    // no media removal actions needed after media fields were removed.
  });
}

function initWikipediaInfoPage() {
    const editorContainer = document.getElementById('wikipedia-timeline-editor');
    const hiddenTextarea = document.getElementById('wikipedia-timeline-section');
    if (!editorContainer || !hiddenTextarea) return;

    const form = document.getElementById('wikipedia-info-form');
    const uploadMediaUrl = (form && form.dataset.uploadUrl) ? form.dataset.uploadUrl : '/admin/wikipedia-info/upload-media';
    const uploadInput = document.getElementById('ckeditor-upload-input');
    const uploadImageButton = document.getElementById('ckeditor-upload-image');
    const uploadVideoButton = document.getElementById('ckeditor-upload-video');

    ClassicEditor.create(editorContainer, {
      toolbar: [
        'bold', 'italic', 'underline', 'strikethrough', 'code',
        '|', 'link', 'bulletedList', 'numberedList',
        '|', 'blockQuote', 'insertTable', 'mediaEmbed',
        '|', 'undo', 'redo'
      ],
      language: 'fa',
      image: {
        toolbar: [ 'imageTextAlternative', 'imageStyle:full', 'imageStyle:side', '|', 'resizeImage' ],
        resizeOptions: [
          {
            name: 'resizeImage:original',
            value: null,
            label: '100%'
          },
          {
            name: 'resizeImage:75',
            value: '75',
            label: '75%'
          },
          {
            name: 'resizeImage:50',
            value: '50',
            label: '50%'
          },
          {
            name: 'resizeImage:25',
            value: '25',
            label: '25%'
          }
        ],
        resizeUnit: '%'
      },
      table: {
        contentToolbar: [ 'tableColumn', 'tableRow', 'mergeTableCells', 'tableCellProperties', 'tableProperties' ]
      },
      mediaEmbed: {
        previewsInData: true
      },
      fontSize: {
        options: [ 10, 12, 14, 16, 18, 20, 24, 28, 32 ]
      }
    })
    .then(editor => {
      function normalizeEditorParagraphs(html) {
        if (!html) {
          return html;
        }

        let normalized = html.trim();

        if (!normalized.match(/<\/?(p|div|h[1-6]|ul|ol|li|blockquote|table|img|video|br|iframe|section|article)/i)) {
          normalized = normalized
            .split(/\r\n|\r|\n/)
            .map(line => line.trim())
            .filter(line => line.length)
            .map(line => `<p>${line}</p>`)
            .join('');
        } else {
          normalized = normalized
            .replace(/<br\s*\/?>(\s*)/gi, '</p><p>')
            .replace(/(\r\n|\r|\n)/g, '</p><p>')
            .replace(/<p>\s*<\/p>/g, '')
            .replace(/<\/p>\s*<p>/g, '</p><p>');

          if (!normalized.startsWith('<p>') && normalized.startsWith('<')) {
            normalized = normalized;
          } else if (!normalized.startsWith('<p>')) {
            normalized = `<p>${normalized}`;
          }

          if (!normalized.endsWith('</p>')) {
            normalized = normalized + '</p>';
          }
        }

        return normalized;
      }

      editor.setData(normalizeEditorParagraphs(hiddenTextarea.value || ''));

      const uploadActions = document.querySelector('.ckeditor-upload-actions');
      const formElement = document.getElementById('wikipedia-info-form');
      const toolbarElement = editor.ui.view.toolbar.element;
      const toolbarWrapper = toolbarElement && (toolbarElement.parentElement || toolbarElement.parentNode);

      if (formElement) {
        formElement.addEventListener('submit', function () {
          hiddenTextarea.value = normalizeEditorParagraphs(editor.getData());
        });
      }

      if (uploadActions && toolbarElement && toolbarWrapper) {
        toolbarWrapper.style.display = 'flex';
        toolbarWrapper.style.flexWrap = 'wrap';
        toolbarWrapper.style.alignItems = 'center';
        toolbarWrapper.style.gap = '12px';
        toolbarElement.style.flex = '1 1 auto';
        uploadActions.style.margin = '0';
        toolbarWrapper.insertBefore(uploadActions, toolbarElement.nextSibling);
      }

      function setEditorFocusState(focused) {
        const editorWrapper = document.querySelector('.ckeditor-editor-wrapper');
        if (!editorWrapper) return;
        editorWrapper.classList.toggle('focused', focused);
      }

      editor.editing.view.document.on('focus', () => setEditorFocusState(true));
      editor.editing.view.document.on('blur', () => {
        setTimeout(() => {
          if (!editor.editing.view.document.isFocused) {
            setEditorFocusState(false);
          }
        });
      });

      function uploadFileAs(type) {
        if (!uploadInput) return;
        uploadInput.accept = type === 'image' ? 'image/*' : 'video/*';
        uploadInput.dataset.mediaType = type;
        uploadInput.click();
      }

      if (uploadImageButton) {
        uploadImageButton.addEventListener('click', function () {
          uploadFileAs('image');
        });
      }
      if (uploadVideoButton) {
        uploadVideoButton.addEventListener('click', function () {
          uploadFileAs('video');
        });
      }

      if (uploadInput) {
        uploadInput.addEventListener('change', function () {
          const file = uploadInput.files && uploadInput.files[0];
          const mediaType = uploadInput.dataset.mediaType || 'image';
          if (!file) return;

          const formData = new FormData();
          formData.append('upload', file);
          formData.append('media_type', mediaType);

          fetch(uploadMediaUrl, {
            method: 'POST',
            body: formData,
          })
            .then((response) => response.json())
            .then((data) => {
              if (!data || !data.success || !data.url) {
                throw new Error(data?.message || 'آپلود موفق نبود.');
              }

              if (mediaType === 'image') {
                editor.execute('insertImage', {
                  source: data.url,
                  alt: 'Uploaded image'
                });
              } else {
                const viewFragment = editor.data.processor.toView(
                  `<video controls style="max-width:100%;"><source src="${data.url}" type="${file.type}"></video>`
                );
                const modelFragment = editor.data.toModel(viewFragment);
                editor.model.change(writer => {
                  editor.model.insertContent(modelFragment, editor.model.document.selection);
                });
              }
            })
            .catch((error) => {
              console.error('Media upload failed:', error);
              alert(error.message || 'خطا در آپلود فایل رخ داد.');
            })
            .finally(() => {
              if (uploadInput) {
                uploadInput.value = '';
                delete uploadInput.dataset.mediaType;
              }
            });
        });
      }

      if (editor.keystrokes) {
        editor.keystrokes.set('Shift+Enter', (data, cancel) => {
          editor.execute('enter');
          cancel();
        });
      }
    })
    .catch(function (error) {
      console.error('CKEditor initialization failed:', error);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initAdminWikipediaInfo();
      initWikipediaInfoPage();
    });
  } else {
    initAdminWikipediaInfo();
    initWikipediaInfoPage();
}
