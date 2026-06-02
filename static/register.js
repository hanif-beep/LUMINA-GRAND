// ============================================================
// REGISTER LOGIC — register.html
// Tempelkan script ini di bagian bawah register.html
// (gantikan script yang sudah ada, atau tambahkan ke dalamnya)
// ============================================================

document.addEventListener('DOMContentLoaded', () => {

  const form = document.getElementById('registrationForm');
  const btn  = form?.querySelector('button[type="submit"]');

  if (!form || !btn) return;

  // ── 1. Icon Scale on Focus ─────────────────────────────────
  form.querySelectorAll('input').forEach(input => {
    const icon = input.parentElement?.querySelector('.material-symbols-outlined');
    if (!icon) return;
    input.addEventListener('focus', () => {
      icon.style.transform  = 'scale(1.15)';
      icon.style.color      = '#735c00';
      icon.style.transition = 'transform 0.3s ease, color 0.3s ease';
      const label = input.closest('.group')?.querySelector('label');
      if (label) label.style.color = '#735c00';
    });
    input.addEventListener('blur', () => {
      icon.style.transform = 'scale(1)';
      icon.style.color     = '';
      const label = input.closest('.group')?.querySelector('label');
      if (label) label.style.color = '';
    });
  });

  // ── 2. Inline Error Helper ─────────────────────────────────
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
    ['username', 'email', 'password', 'confirm-password'].forEach(removeError);
  }

  // ── 3. Password Strength Indicator ────────────────────────
  const passInput = document.getElementById('password');
  if (passInput) {
    const strengthBar = document.createElement('div');
    strengthBar.className = 'h-0.5 mt-2 rounded-full transition-all duration-500';
    passInput.parentElement.insertAdjacentElement('afterend', strengthBar);

    passInput.addEventListener('input', () => {
      const val = passInput.value;
      let score = 0;
      if (val.length >= 8)          score++;
      if (/[A-Z]/.test(val))        score++;
      if (/[0-9]/.test(val))        score++;
      if (/[^A-Za-z0-9]/.test(val)) score++;

      const colors = ['', '#ba1a1a', '#e9c349', '#735c00', '#1a6e28'];
      const widths  = ['0%', '25%', '50%', '75%', '100%'];
      strengthBar.style.width           = widths[score];
      strengthBar.style.backgroundColor = colors[score];
    });
  }

  // ── 4. Client-Side Validation ──────────────────────────────
  function validateRegister(username, email, password, confirm, termsChecked) {
    let valid = true;
    clearErrors();

    if (!username || username.length < 3) {
      showError('username', 'Username must be at least 3 characters.');
      valid = false;
    }
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      showError('email', 'Please enter a valid email address.');
      valid = false;
    }
    if (!password || password.length < 6) {
      showError('password', 'Password must be at least 6 characters.');
      valid = false;
    }
    if (password !== confirm) {
      showError('confirm-password', 'Passwords do not match.');
      valid = false;
    }
    if (!termsChecked) {
      const termsLabel = document.querySelector('label[for="terms"]');
      if (termsLabel) {
        termsLabel.style.color = '#ba1a1a';
        setTimeout(() => { termsLabel.style.color = ''; }, 3000);
      }
      valid = false;
    }
    return valid;
  }

  // ── 5. Submit Handler ──────────────────────────────────────
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const username = document.getElementById('username')?.value.trim();
    const email    = document.getElementById('email')?.value.trim();
    const password = document.getElementById('password')?.value;
    const confirm  = document.getElementById('confirm-password')?.value;
    const terms    = document.getElementById('terms')?.checked;

    if (!validateRegister(username, email, password, confirm, terms)) return;

    // Loading state
    const originalHTML = btn.innerHTML;
    btn.disabled  = true;
    btn.innerHTML = '<span class="material-symbols-outlined animate-spin text-[18px] mr-2">autorenew</span> Creating Account...';
    btn.style.opacity = '0.8';

    try {
      const res = await fetch('/register', {
        method : 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body   : new URLSearchParams({ username, email, password }),
      });

      if (res.redirected || res.ok) {
        // Sukses: tampilkan toast lalu redirect ke login
        showToast('Account created! Redirecting to login...', 'success');
        setTimeout(() => { window.location.href = '/login'; }, 1800);
      } else {
        const text = await res.text();
        if (text.includes('already') || text.includes('exists')) {
          showError('email', 'An account with this email already exists.');
        } else {
          showError('username', 'Registration failed. Please try again.');
        }
        btn.disabled  = false;
        btn.innerHTML = originalHTML;
        btn.style.opacity = '1';
      }

    } catch (err) {
      console.error('Register error:', err);
      showError('email', 'Network error. Please try again.');
      btn.disabled  = false;
      btn.innerHTML = originalHTML;
      btn.style.opacity = '1';
    }
  });

  // ── 6. Toast Notification ─────────────────────────────────
  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = [
      'fixed bottom-8 left-1/2 -translate-x-1/2 z-50',
      'px-8 py-4 rounded-full shadow-2xl text-sm font-semibold tracking-wider uppercase',
      'transition-all duration-500 opacity-0 translate-y-4',
      type === 'success'
        ? 'bg-[#735c00] text-white'
        : 'bg-[#ba1a1a] text-white'
    ].join(' ');
    toast.textContent = message;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
      toast.style.opacity   = '1';
      toast.style.transform = 'translateX(-50%) translateY(0)';
    });

    setTimeout(() => {
      toast.style.opacity   = '0';
      toast.style.transform = 'translateX(-50%) translateY(16px)';
      setTimeout(() => toast.remove(), 500);
    }, 2500);
  }

});