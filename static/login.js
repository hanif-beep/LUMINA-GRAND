// ============================================================
// LOGIN LOGIC — login.html
// Tempelkan script ini di bagian bawah login.html
// (gantikan script yang sudah ada, atau tambahkan ke dalamnya)
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

  // ── 1. Toggle Password Visibility ──────────────────────────
  const togglePass = document.querySelector('button[type="button"]');
  const passInput = document.querySelector('#password');

  if (togglePass && passInput) {
    togglePass.addEventListener('click', () => {
      const isPassword = passInput.type === 'password';
      passInput.type = isPassword ? 'text' : 'password';
      togglePass.querySelector('span').innerText = isPassword
        ? 'visibility'
        : 'visibility_off';
    });
  }

  // ── 2. Label Focus Color ───────────────────────────────────
  document.querySelectorAll('.form-input-minimal').forEach(input => {
    input.addEventListener('focus', () => {
      const labelWrap = input.closest('.flex.flex-col');
      const label = labelWrap?.querySelector('label');
      if (label) label.style.color = '#735c00';
    });
    input.addEventListener('blur', () => {
      const labelWrap = input.closest('.flex.flex-col');
      const label = labelWrap?.querySelector('label');
      if (label) label.style.color = '#43474e';
    });
  });

  // ── 3. Inline Error Helper ─────────────────────────────────
  function showError(fieldId, message) {
    removeError(fieldId);
    const input = document.getElementById(fieldId);
    if (!input) return;
    const err = document.createElement('p');
    err.id = fieldId + '-error';
    err.className = 'text-[11px] text-red-500 mt-1 font-label-sm';
    err.textContent = message;
    input.parentElement.insertAdjacentElement('afterend', err);
    input.style.borderBottomColor = '#ba1a1a';
  }

  function removeError(fieldId) {
    const old = document.getElementById(fieldId + '-error');
    if (old) old.remove();
    const input = document.getElementById(fieldId);
    if (input) input.style.borderBottomColor = '';
  }

  function clearErrors() {
    ['email', 'password'].forEach(removeError);
  }

  // ── 4. Client-Side Validation ──────────────────────────────
  function validateLogin(email, password) {
    let valid = true;
    clearErrors();

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showError('email', 'Please enter a valid email address.');
      valid = false;
    }
    if (!password || password.length < 6) {
      showError('password', 'Password must be at least 6 characters.');
      valid = false;
    }
    return valid;
  }

  // ── 5. Submit Handler ──────────────────────────────────────
  const form = document.getElementById('login-form') || document.querySelector('form');
  const btn = form?.querySelector('button[type="submit"]');

  if (!form || !btn) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const email = document.getElementById('email')?.value.trim();
    const password = document.getElementById('password')?.value;

    if (!validateLogin(email, password)) return;

    // Loading state
    const originalHTML = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="material-symbols-outlined animate-spin text-[18px] mr-2">autorenew</span> Signing in...';
    btn.style.opacity = '0.8';

    try {
      const res = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ email, password }),
      });

      if (res.redirected) {
        window.location.href = res.url;
        return;
      }

      const text = await res.text();

      // Cek apakah Flask mengembalikan halaman login lagi (gagal)
      if (res.ok && !text.includes('invalid') && !text.includes('Login')) {
        window.location.href = '/rooms';
      } else {
        showError('password', 'Invalid email or password. Please try again.');
        btn.disabled = false;
        btn.innerHTML = originalHTML;
        btn.style.opacity = '1';
      }

    } catch (err) {
      console.error('Login error:', err);
      showError('email', 'Network error. Please try again.');
      btn.disabled = false;
      btn.innerHTML = originalHTML;
      btn.style.opacity = '1';
    }
  });

  // ── 6. Smooth Hero Image Ken Burns ────────────────────────
  const heroImg = document.querySelector('section:first-child img');
  if (heroImg) {
    heroImg.style.transform = 'scale(1.05)';
    heroImg.style.transition = 'transform 12s ease-out';
    setTimeout(() => { heroImg.style.transform = 'scale(1)'; }, 100);
  }

});