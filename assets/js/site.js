// Shared behaviour for every page: mobile nav, smooth scroll, navbar shadow, dark mode.

// Mobile nav toggle
document.querySelector('.nav-toggle').addEventListener('click', function() {
  document.querySelector('.nav-links').classList.toggle('show');
});

// Trigger hero entrance motion after DOM is ready
document.addEventListener('DOMContentLoaded', function() {
  document.body.classList.add('is-loaded');
});

// Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
  anchor.addEventListener('click', function(e) {
    const target = document.querySelector(this.getAttribute('href'));
    if (target) {
      e.preventDefault();
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      document.querySelector('.nav-links').classList.remove('show');
    }
  });
});

// Navbar shrink on scroll
window.addEventListener('scroll', function() {
  const nav = document.querySelector('.nav');
  if (window.scrollY > 50) {
    nav.classList.add('scrolled');
  } else {
    nav.classList.remove('scrolled');
  }
});

// Dark mode toggle
(function() {
  const toggle = document.getElementById('theme-toggle');
  const icon = toggle.querySelector('i');

  function updateIcon() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    icon.className = isDark ? 'fas fa-sun' : 'fas fa-moon';
  }

  updateIcon();

  toggle.addEventListener('click', function() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
    updateIcon();
  });

  // Listen for OS theme changes (only if user hasn't manually set)
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
    if (!localStorage.getItem('theme')) {
      document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
      updateIcon();
    }
  });
})();
