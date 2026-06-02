/* =========================================================
   STUDIOSOWA — Frontend JS
   ========================================================= */

'use strict';

// ---------------------------------------------------------
// Index projets — bas gauche (survol + clic)
// ---------------------------------------------------------
document.addEventListener('DOMContentLoaded', function () {
  const wrap = document.getElementById('projIndex');
  if (!wrap) return;
  const btn  = document.getElementById('projIndexBtn');

  let closeTimer;

  function openIndex() {
    clearTimeout(closeTimer);
    wrap.classList.add('open');
    btn.setAttribute('aria-expanded', 'true');
  }

  function closeIndex() {
    closeTimer = setTimeout(function () {
      wrap.classList.remove('open');
      btn.setAttribute('aria-expanded', 'false');
    }, 150);
  }

  // Survol
  wrap.addEventListener('mouseenter', openIndex);
  wrap.addEventListener('mouseleave', closeIndex);

  // Clic (mobile)
  btn.addEventListener('click', function () {
    wrap.classList.contains('open') ? closeIndex() : openIndex();
  });

  // Fermer si clic ailleurs
  document.addEventListener('click', function (e) {
    if (!wrap.contains(e.target)) closeIndex();
  });
});

// ---------------------------------------------------------
// Language management
// ---------------------------------------------------------
function getLang() {
  return document.documentElement.getAttribute('data-lang') || 'fr';
}

window.applyLang = function(lang) {
  document.documentElement.setAttribute('data-lang', lang);
  document.body.setAttribute('data-lang', lang);
  document.querySelectorAll('#btn-fr, #btn-en').forEach(btn => {
    btn.classList.remove('active');
  });
  const btn = document.getElementById(`btn-${lang}`);
  if (btn) btn.classList.add('active');
};

function setLang(lang) {
  if (!['fr', 'en'].includes(lang)) lang = 'fr';
  // Save cookie
  document.cookie = `lang=${lang};path=/;max-age=${60*60*24*365};samesite=Lax`;
  // Apply immediately
  applyLang(lang);
}

window.setLang = setLang;

// ---------------------------------------------------------
// Custom cursor
// ---------------------------------------------------------
(function initCursor() {
  const cursor = document.getElementById('cursor');
  if (!cursor) return;

  let cx = window.innerWidth / 2, cy = window.innerHeight / 2;
  let tx = cx, ty = cy;
  let raf;

  document.addEventListener('mousemove', e => {
    tx = e.clientX;
    ty = e.clientY;
  });

  function animate() {
    cx += (tx - cx) * 0.18;
    cy += (ty - cy) * 0.18;
    cursor.style.left = `${cx}px`;
    cursor.style.top  = `${cy}px`;
    raf = requestAnimationFrame(animate);
  }
  animate();

  // Hoverable elements
  const hoverTargets = 'a, button, .project-card, [role="button"]';
  document.addEventListener('mouseover', e => {
    if (e.target.closest(hoverTargets)) cursor.classList.add('hovering');
  });
  document.addEventListener('mouseout', e => {
    if (e.target.closest(hoverTargets)) cursor.classList.remove('hovering');
  });

  // Hide cursor when leaving window
  document.addEventListener('mouseleave', () => { cursor.style.opacity = '0'; });
  document.addEventListener('mouseenter', () => { cursor.style.opacity = '1'; });
})();

// ---------------------------------------------------------
// Loading screen
// ---------------------------------------------------------
(function initLoader() {
  const loader = document.getElementById('loader');
  const counter = document.getElementById('loaderCounter');
  if (!loader) return;

  // Only show loader on first visit per session
  const loaderShown = sessionStorage.getItem('loaderShown');

  if (loaderShown) {
    loader.style.display = 'none';
    revealPage();
    return;
  }

  sessionStorage.setItem('loaderShown', '1');

  // Trigger name reveal
  setTimeout(() => {
    loader.classList.add('reveal');
  }, 100);

  // Animate counter
  let count = 0;
  const interval = setInterval(() => {
    count += Math.floor(Math.random() * 12) + 4;
    if (count >= 100) {
      count = 100;
      clearInterval(interval);
      if (counter) counter.textContent = '100%';
      setTimeout(() => {
        loader.classList.add('hide');
        setTimeout(() => {
          loader.style.display = 'none';
          revealPage();
        }, 1100);
      }, 300);
    }
    if (counter) counter.textContent = `${Math.min(count, 100)}%`;
  }, 80);
})();

function revealPage() {
  // Stagger reveal of project cards
  const cards = document.querySelectorAll('.project-card');
  cards.forEach((card, i) => {
    setTimeout(() => card.classList.add('visible'), i * 80);
  });
}

// ---------------------------------------------------------
// Intersection Observer — reveal on scroll
// ---------------------------------------------------------
(function initScrollReveal() {
  const items = document.querySelectorAll('.project-image-item');
  if (!items.length) return;

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });

  items.forEach(item => observer.observe(item));
})();

// ---------------------------------------------------------
// Page transitions
// ---------------------------------------------------------
(function initPageTransitions() {
  const overlay = document.getElementById('pageTransition');
  if (!overlay) return;

  // Animate in (page loaded)
  overlay.classList.add('leaving');

  // Intercept navigation links
  document.addEventListener('click', e => {
    const link = e.target.closest('a[href]');
    if (!link) return;

    const href = link.getAttribute('href');
    // Skip external, anchor, admin links
    if (!href || href.startsWith('#') || href.startsWith('http') ||
        href.startsWith('mailto') || href.startsWith('tel') ||
        href.includes('/admin') || link.target === '_blank') return;

    e.preventDefault();
    overlay.classList.remove('leaving');
    overlay.classList.add('entering');

    setTimeout(() => {
      window.location.href = href;
    }, 520);
  });
})();

// ---------------------------------------------------------
// Homepage — project card entrance (fallback for browsers
// without IntersectionObserver, or when loader is skipped)
// ---------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  // Apply language immediately
  const lang = getLang();
  applyLang(lang);

  // If no loader shown, immediately reveal cards
  const loaderEl = document.getElementById('loader');
  if (loaderEl && loaderEl.style.display === 'none') {
    revealPage();
  }

  initLightbox();
});

// ---------------------------------------------------------
// Lightbox
// ---------------------------------------------------------
function initLightbox() {
  const images = Array.from(document.querySelectorAll('.project-image-item img'));
  if (!images.length) return;

  // Inject lightbox DOM
  const lb = document.createElement('div');
  lb.id = 'lightbox';
  lb.setAttribute('role', 'dialog');
  lb.setAttribute('aria-modal', 'true');
  lb.setAttribute('aria-label', 'Image en plein écran');
  if (images.length === 1) lb.classList.add('single');

  lb.innerHTML = `
    <button class="lb-close" aria-label="Fermer" id="lbClose">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M18 6L6 18M6 6l12 12"/>
      </svg>
    </button>
    <button class="lb-prev" aria-label="Image précédente" id="lbPrev">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M15 18l-6-6 6-6"/>
      </svg>
    </button>
    <div class="lb-img-wrap">
      <img id="lb-img" src="" alt="">
    </div>
    <button class="lb-next" aria-label="Image suivante" id="lbNext">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M9 18l6-6-6-6"/>
      </svg>
    </button>
    <div class="lb-caption" id="lbCaption"></div>
    <div class="lb-counter" id="lbCounter"></div>
  `;
  document.body.appendChild(lb);

  const lbImg     = document.getElementById('lb-img');
  const lbCaption = document.getElementById('lbCaption');
  const lbCounter = document.getElementById('lbCounter');
  let current = 0;

  function open(idx) {
    current = (idx + images.length) % images.length;
    lbImg.src = images[current].src;
    lbImg.alt = images[current].alt;
    lbCaption.textContent = images[current].alt !== images[current].closest('.project-image-item')?.querySelector('img')?.getAttribute('data-title')
      ? (images[current].getAttribute('data-caption') || '')
      : '';
    lbCounter.textContent = `${current + 1} / ${images.length}`;
    lb.classList.add('open');
    document.body.style.overflow = 'hidden';
  }

  function close() {
    lb.classList.remove('open');
    document.body.style.overflow = '';
  }

  function go(dir) {
    lbImg.classList.add('transitioning');
    setTimeout(() => {
      current = (current + dir + images.length) % images.length;
      lbImg.src = images[current].src;
      lbImg.alt = images[current].alt;
      lbCounter.textContent = `${current + 1} / ${images.length}`;
      lbImg.classList.remove('transitioning');
    }, 220);
  }

  // Click on images to open lightbox
  images.forEach((img, i) => {
    img.style.cursor = 'zoom-in';
    img.addEventListener('click', () => open(i));
  });

  document.getElementById('lbClose').addEventListener('click', close);
  document.getElementById('lbPrev').addEventListener('click', () => go(-1));
  document.getElementById('lbNext').addEventListener('click', () => go(1));

  // Close on backdrop click
  lb.addEventListener('click', e => { if (e.target === lb) close(); });

  // Keyboard navigation
  document.addEventListener('keydown', e => {
    if (!lb.classList.contains('open')) return;
    if (e.key === 'Escape')     close();
    if (e.key === 'ArrowLeft')  go(-1);
    if (e.key === 'ArrowRight') go(1);
  });

  // Touch / swipe support
  let touchStartX = 0;
  let touchStartY = 0;

  lb.addEventListener('touchstart', e => {
    touchStartX = e.changedTouches[0].clientX;
    touchStartY = e.changedTouches[0].clientY;
  }, { passive: true });

  lb.addEventListener('touchend', e => {
    const dx = e.changedTouches[0].clientX - touchStartX;
    const dy = e.changedTouches[0].clientY - touchStartY;
    if (Math.abs(dx) < 30 && Math.abs(dy) < 30) { close(); return; } // tap = close
    if (Math.abs(dx) > Math.abs(dy) && Math.abs(dx) > 50) {
      go(dx < 0 ? 1 : -1);
    }
  }, { passive: true });
}
