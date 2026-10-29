// Photography lightbox: opens the full-size photo in a <dialog>, with
// keyboard / swipe navigation and a shareable #photo-<id> URL.
(function() {
  const tiles = Array.from(document.querySelectorAll('.gallery .tile'));
  const box = document.querySelector('.lightbox');
  if (!tiles.length) return;

  // Hide the nav while scrolling down; bring it back on any upward scroll.
  const nav = document.querySelector('.nav');
  let lastY = window.scrollY;
  window.addEventListener('scroll', function() {
    const y = window.scrollY;
    const menuOpen = document.querySelector('.nav-links.show');
    if (Math.abs(y - lastY) < 6) return;
    nav.classList.toggle('nav-hidden', y > lastY && y > 80 && !menuOpen);
    lastY = y;
  }, { passive: true });

  // Fade tiles up into place as they scroll into view, staggered within each batch.
  if ('IntersectionObserver' in window && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const gallery = document.querySelector('.gallery');
    gallery.classList.add('reveal');
    const observer = new IntersectionObserver(function(entries) {
      entries.filter(function(e) { return e.isIntersecting; }).forEach(function(e, i) {
        e.target.style.setProperty('--delay', Math.min(i * 0.07, 0.5) + 's');
        e.target.classList.add('is-visible');
        observer.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -5% 0px' });
    tiles.forEach(function(t) { observer.observe(t); });
  }

  if (!box || typeof box.showModal !== 'function') return; // fall back to plain links

  const img = box.querySelector('.lightbox-img');
  const title = box.querySelector('.lightbox-title');
  const meta = box.querySelector('.lightbox-meta');
  const caption = box.querySelector('.lightbox-caption');
  const counter = box.querySelector('.lightbox-counter');
  let current = -1;

  function preload(i) {
    const tile = tiles[(i + tiles.length) % tiles.length];
    new Image().src = tile.href;
  }

  function show(i) {
    current = (i + tiles.length) % tiles.length;
    const tile = tiles[current];
    const thumb = tile.querySelector('img');
    const metaEl = tile.querySelector('.tile-meta');
    const captionEl = tile.querySelector('.tile-caption');

    // Show the cached thumbnail right away, then swap in the full image once loaded.
    img.src = thumb.currentSrc || thumb.src;
    img.alt = thumb.alt;
    const full = new Image();
    full.onload = function() {
      if (tiles[current] === tile) img.src = full.src;
    };
    full.src = tile.href;

    title.textContent = tile.querySelector('.tile-title').textContent;
    meta.textContent = metaEl ? metaEl.textContent : '';
    caption.innerHTML = captionEl ? captionEl.innerHTML : '';
    counter.textContent = (current + 1) + ' / ' + tiles.length;
    history.replaceState(null, '', '#' + tile.id);

    preload(current + 1);
    preload(current - 1);
  }

  function open(i) {
    show(i);
    document.documentElement.classList.add('lightbox-open');
    if (!box.open) box.showModal();
  }

  box.addEventListener('close', function() {
    document.documentElement.classList.remove('lightbox-open');
    history.replaceState(null, '', location.pathname + location.search);
    if (tiles[current]) tiles[current].focus({ preventScroll: true });
  });

  tiles.forEach(function(tile, i) {
    tile.addEventListener('click', function(e) {
      e.preventDefault();
      open(i);
    });
  });

  box.querySelector('.lightbox-close').addEventListener('click', function() { box.close(); });
  box.querySelector('.lightbox-prev').addEventListener('click', function() { show(current - 1); });
  box.querySelector('.lightbox-next').addEventListener('click', function() { show(current + 1); });

  // Clicking the dark background (not the photo or controls) closes the viewer.
  box.addEventListener('click', function(e) {
    if (e.target === box || e.target === box.querySelector('.lightbox-figure')) box.close();
  });

  document.addEventListener('keydown', function(e) {
    if (!box.open) return;
    if (e.key === 'ArrowLeft') show(current - 1);
    if (e.key === 'ArrowRight') show(current + 1);
  });

  // Swipe left / right on touch screens.
  let touchX = null;
  box.addEventListener('touchstart', function(e) { touchX = e.touches[0].clientX; }, { passive: true });
  box.addEventListener('touchend', function(e) {
    if (touchX === null) return;
    const dx = e.changedTouches[0].clientX - touchX;
    if (Math.abs(dx) > 50) show(current + (dx < 0 ? 1 : -1));
    touchX = null;
  });

  // Open directly when the URL points at a photo, e.g. /photography/#photo-22
  const linked = tiles.findIndex(function(t) { return '#' + t.id === location.hash; });
  if (linked >= 0) open(linked);
})();
