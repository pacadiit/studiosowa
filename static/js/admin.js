/* =========================================================
   STUDIOSOWA — Admin JS
   Handles: drag & drop upload, image reorder, delete, cover
   ========================================================= */

'use strict';

// ---------------------------------------------------------
// New project — local image preview (before form submit)
// ---------------------------------------------------------
const imagesInput = document.getElementById('imagesInput');
const imagesPreview = document.getElementById('imagesPreview');
const uploadZone = document.getElementById('uploadZone');

if (imagesInput && imagesPreview) {
  imagesInput.addEventListener('change', () => {
    imagesPreview.innerHTML = '';
    Array.from(imagesInput.files).forEach((file, i) => {
      const reader = new FileReader();
      reader.onload = e => {
        const item = document.createElement('div');
        item.className = 'image-preview-item';
        item.innerHTML = `
          <img src="${e.target.result}" alt="Aperçu ${i + 1}">
          ${i === 0 ? '<div class="image-preview-cover-badge">Vignette</div>' : ''}
        `;
        imagesPreview.appendChild(item);
      };
      reader.readAsDataURL(file);
    });
  });
}

// Drag & drop on upload zone (new project)
if (uploadZone) {
  uploadZone.addEventListener('dragover', e => {
    e.preventDefault();
    uploadZone.classList.add('drag-over');
  });
  uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
  uploadZone.addEventListener('drop', e => {
    e.preventDefault();
    uploadZone.classList.remove('drag-over');
    if (imagesInput) {
      const dt = new DataTransfer();
      Array.from(e.dataTransfer.files).forEach(f => dt.items.add(f));
      imagesInput.files = dt.files;
      imagesInput.dispatchEvent(new Event('change'));
    }
  });
}

// ---------------------------------------------------------
// Edit project — AJAX image upload
// ---------------------------------------------------------
const ajaxInput = document.getElementById('ajaxImageInput');
const uploadZoneEdit = document.getElementById('uploadZoneEdit');
const progressEl = document.getElementById('uploadProgress');
const progressBar = document.getElementById('progressBar');
const uploadStatus = document.getElementById('uploadStatus');
const existingImages = document.getElementById('existingImages');

// Determine projectId (set inline in template)
const pid = typeof projectId !== 'undefined' ? projectId : null;

if (ajaxInput && pid) {
  ajaxInput.addEventListener('change', () => {
    uploadFiles(Array.from(ajaxInput.files));
    ajaxInput.value = '';
  });
}

if (uploadZoneEdit && pid) {
  uploadZoneEdit.addEventListener('dragover', e => {
    e.preventDefault();
    uploadZoneEdit.classList.add('drag-over');
  });
  uploadZoneEdit.addEventListener('dragleave', () => uploadZoneEdit.classList.remove('drag-over'));
  uploadZoneEdit.addEventListener('drop', e => {
    e.preventDefault();
    uploadZoneEdit.classList.remove('drag-over');
    uploadFiles(Array.from(e.dataTransfer.files));
  });
}

async function uploadFiles(files) {
  if (!files.length || !pid) return;

  progressEl && (progressEl.style.display = 'block');
  let completed = 0;

  for (const file of files) {
    if (!file.type.startsWith('image/')) continue;
    if (uploadStatus) uploadStatus.textContent = `Upload de ${file.name}…`;

    const formData = new FormData();
    formData.append('image', file);

    try {
      const res = await fetch(`/admin/projets/${pid}/upload`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();

      if (data.success && existingImages) {
        addImagePreview(data.image_id, data.url);
      }
    } catch (err) {
      console.error('Upload error:', err);
    }

    completed++;
    if (progressBar) progressBar.style.width = `${(completed / files.length) * 100}%`;
  }

  if (uploadStatus) uploadStatus.textContent = `${completed} image(s) ajoutée(s) !`;
  setTimeout(() => {
    if (progressEl) progressEl.style.display = 'none';
    if (progressBar) progressBar.style.width = '0%';
  }, 2000);
}

function addImagePreview(imageId, url) {
  if (!existingImages) return;
  const item = document.createElement('div');
  item.className = 'image-preview-item';
  item.setAttribute('data-image-id', imageId);
  item.setAttribute('draggable', 'true');
  item.innerHTML = `
    <img src="${url}" alt="">
    <div class="image-preview-actions">
      <button class="img-action-btn" title="Définir comme vignette" onclick="setCover(${imageId}, this)">★</button>
      <button class="img-action-btn delete" title="Supprimer" onclick="deleteImage(${imageId}, this)">×</button>
    </div>
  `;
  existingImages.appendChild(item);
  initDragForItem(item);
}

// ---------------------------------------------------------
// Delete image
// ---------------------------------------------------------
window.deleteImage = async function(imageId, btn) {
  if (!confirm('Supprimer cette image ?')) return;
  const item = btn.closest('.image-preview-item');
  try {
    const res = await fetch(`/admin/images/${imageId}/supprimer`, { method: 'POST' });
    const data = await res.json();
    if (data.success && item) {
      item.style.opacity = '0';
      item.style.transform = 'scale(0.9)';
      item.style.transition = 'all 0.3s';
      setTimeout(() => item.remove(), 300);
    }
  } catch (e) {
    alert('Erreur lors de la suppression.');
  }
};

// ---------------------------------------------------------
// Set cover image
// ---------------------------------------------------------
window.setCover = async function(imageId, btn) {
  try {
    const res = await fetch(`/admin/images/${imageId}/cover`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      // Remove all existing cover badges
      document.querySelectorAll('.image-preview-cover-badge').forEach(b => b.remove());
      // Add to this item
      const item = btn.closest('.image-preview-item');
      if (item) {
        const badge = document.createElement('div');
        badge.className = 'image-preview-cover-badge';
        badge.textContent = 'Vignette';
        item.appendChild(badge);
      }
    }
  } catch (e) {
    alert('Erreur.');
  }
};

// ---------------------------------------------------------
// Drag & drop reorder (existing images)
// ---------------------------------------------------------
let dragSrc = null;

function initDragForItem(item) {
  item.addEventListener('dragstart', () => {
    dragSrc = item;
    item.style.opacity = '0.4';
  });
  item.addEventListener('dragend', () => {
    item.style.opacity = '1';
    dragSrc = null;
    saveOrder();
  });
  item.addEventListener('dragover', e => {
    e.preventDefault();
    if (!dragSrc || dragSrc === item) return;
    const bounding = item.getBoundingClientRect();
    const offset = e.clientY - bounding.top;
    if (offset < bounding.height / 2) {
      item.parentNode.insertBefore(dragSrc, item);
    } else {
      item.parentNode.insertBefore(dragSrc, item.nextSibling);
    }
  });
}

async function saveOrder() {
  if (!existingImages) return;
  const order = Array.from(existingImages.querySelectorAll('.image-preview-item'))
    .map(el => parseInt(el.getAttribute('data-image-id')));
  try {
    await fetch('/admin/images/reorder', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order }),
    });
  } catch (e) {
    console.error('Reorder error:', e);
  }
}

// Init drag for existing images
document.querySelectorAll('.image-preview-item[draggable]').forEach(initDragForItem);
