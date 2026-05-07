/* ================================================
   Aethelgard BCA Portal — Shared JavaScript
   Backend: Python Flask  |  DB: SQLite
   ================================================ */

// ── API Helper ──────────────────────────────────
async function api(method, url, body) {
  const opts = {
    method: method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin'
  };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  return { ok: res.ok, status: res.status, data };
}

// ── Auth Guard ──────────────────────────────────
async function requireAuth() {
  const r = await api('GET', '/api/auth/me');
  if (!r.ok) { window.location.href = '/login'; return null; }
  return r.data;
}

// ── Logout ──────────────────────────────────────
async function logout() {
  await api('POST', '/api/auth/logout');
  window.location.href = '/login';
}

// ── Live Clock ──────────────────────────────────
function initClock() {
  const el = document.getElementById('live-clock');
  if (!el) return;
  function tick() {
    const now = new Date();
    const opts = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true };
    const dateStr = now.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
    el.textContent = dateStr + '  •  ' + now.toLocaleTimeString('en-IN', opts);
  }
  tick();
  setInterval(tick, 1000);
}

// ── Dynamic Greeting ────────────────────────────
function getGreeting(name) {
  const h = new Date().getHours();
  let g = 'Good Evening';
  if (h < 12) g = 'Good Morning';
  else if (h < 17) g = 'Good Afternoon';
  return g + ', ' + name + '.';
}

// ── Toast Notification ──────────────────────────
function showToast(message, icon) {
  icon = icon || 'info';
  let toast = document.getElementById('global-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'global-toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.innerHTML = '<span class="material-symbols-outlined">' + icon + '</span>' + message;
  toast.classList.add('show');
  setTimeout(function () { toast.classList.remove('show'); }, 3500);
}

// ── Animate Counter ─────────────────────────────
function animateCounter(el, target, duration) {
  if (!el) return;
  duration = duration || 1000;
  let start = 0;
  const isDecimal = String(target).includes('.');
  const step = target / (duration / 16);
  function update() {
    start += step;
    if (start >= target) {
      el.textContent = isDecimal ? Number(target).toFixed(2) : target;
      return;
    }
    el.textContent = isDecimal ? start.toFixed(2) : Math.floor(start);
    requestAnimationFrame(update);
  }
  update();
}

// ── Animate Progress Bars ───────────────────────
function initProgressBars() {
  document.querySelectorAll('.progress-bar-fill').forEach(function (bar) {
    const w = bar.getAttribute('data-width');
    if (w) setTimeout(function () { bar.style.width = w + '%'; }, 300);
  });
}

// ── Format Countdown ────────────────────────────
function formatCountdown(targetDate) {
  const now = new Date();
  const diff = new Date(targetDate) - now;
  if (diff <= 0) return 'Overdue';
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor((diff % 86400000) / 3600000);
  const mins = Math.floor((diff % 3600000) / 60000);
  if (days > 0) return days + 'd ' + hours + 'h remaining';
  return hours + 'h ' + mins + 'm remaining';
}

// ── Notification Badge ──────────────────────────
async function loadNotifBadge() {
  const r = await api('GET', '/api/stats');
  if (!r.ok) return;
  const count = r.data.unread_notifications || 0;
  const badge = document.getElementById('notif-badge');
  if (badge) {
    badge.textContent = count;
    badge.style.display = count > 0 ? 'flex' : 'none';
  }
}

// ── Init Common ─────────────────────────────────
document.addEventListener('DOMContentLoaded', function () {
  initClock();
  initProgressBars();
  loadNotifBadge();
  initHamburger();
  initScrollReveal();
  initRippleEffect();
  initGlowHover();
  initKeyboardShortcuts();
  
  if (typeof io !== 'undefined') {
    const socket = io();
    socket.on('new_notification', function(data) {
      showToast(data.title, 'notifications_active');
      loadNotifBadge();
      // If we are on the notifications page, reload it
      if (window.location.pathname === '/notifications' && typeof loadNotifications === 'function') {
        loadNotifications();
      }
    });
  }
});

// ── Hamburger Menu ──────────────────────────────
function initHamburger() {
  const btn = document.getElementById('hamburger-toggle');
  const sidebar = document.querySelector('.sidebar');
  const overlay = document.getElementById('sidebar-overlay');
  if (!btn || !sidebar) return;

  btn.addEventListener('click', function () {
    btn.classList.toggle('active');
    sidebar.classList.toggle('mobile-open');
    if (overlay) overlay.classList.toggle('active');
    document.body.style.overflow = sidebar.classList.contains('mobile-open') ? 'hidden' : '';
  });

  if (overlay) {
    overlay.addEventListener('click', function () {
      btn.classList.remove('active');
      sidebar.classList.remove('mobile-open');
      overlay.classList.remove('active');
      document.body.style.overflow = '';
    });
  }
}

// ── Scroll Reveal (IntersectionObserver) ────────
function initScrollReveal() {
  if (!('IntersectionObserver' in window)) return;
  const els = document.querySelectorAll('.scroll-reveal');
  if (els.length === 0) return;
  const obs = new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    });
  }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
  els.forEach(function (el) { obs.observe(el); });
}

// ── Ripple Effect on Buttons ────────────────────
function initRippleEffect() {
  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.btn-gold, .btn-primary, .btn-outline');
    if (!btn) return;
    var circle = document.createElement('span');
    circle.className = 'ripple';
    var d = Math.max(btn.clientWidth, btn.clientHeight);
    circle.style.width = circle.style.height = d + 'px';
    var rect = btn.getBoundingClientRect();
    circle.style.left = (e.clientX - rect.left - d / 2) + 'px';
    circle.style.top = (e.clientY - rect.top - d / 2) + 'px';
    btn.appendChild(circle);
    setTimeout(function () { circle.remove(); }, 600);
  });
}

// ── Glow Hover (mouse tracking) ────────────────
function initGlowHover() {
  document.addEventListener('mousemove', function (e) {
    var card = e.target.closest('.glow-hover');
    if (!card) return;
    var rect = card.getBoundingClientRect();
    card.style.setProperty('--mx', ((e.clientX - rect.left) / rect.width * 100) + '%');
    card.style.setProperty('--my', ((e.clientY - rect.top) / rect.height * 100) + '%');
  });
}

// ── Keyboard Shortcuts ──────────────────────────
function initKeyboardShortcuts() {
  document.addEventListener('keydown', function (e) {
    // Ctrl+K or Cmd+K → focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      var searchInput = document.getElementById('search-input');
      if (searchInput) searchInput.focus();
    }
    // Escape → close modals & sidebar
    if (e.key === 'Escape') {
      var overlay = document.getElementById('sidebar-overlay');
      if (overlay && overlay.classList.contains('active')) {
        document.getElementById('hamburger-toggle')?.classList.remove('active');
        document.querySelector('.sidebar')?.classList.remove('mobile-open');
        overlay.classList.remove('active');
        document.body.style.overflow = '';
      }
      document.querySelectorAll('.modal-overlay.active').forEach(function (m) { m.classList.remove('active'); });
    }
  });
}

