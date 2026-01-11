(() => {
  const form = document.getElementById('access-form');
  const modeToggle = document.querySelector('[data-auth-mode-toggle]');
  if (!form || !modeToggle) {
    return;
  }

  const storageKey = 'skillproof-access-profile';
  const toggleButtons = modeToggle.querySelectorAll('button[data-mode]');
  const nameField = form.querySelector('[data-auth-section="register"]');
  const nameInput = form.querySelector('input[name="name"]');
  const emailInput = form.querySelector('input[name="email"]');
  const passwordInput = form.querySelector('input[name="password"]');
  const errorElement = document.getElementById('auth-error');
  const submitButton = form.querySelector('[data-auth-submit]');
  const registerOnlyElements = form.querySelectorAll('[data-auth-copy="register"]');

  let mode = form.dataset.authMode || 'login';

  const setMode = (nextMode) => {
    mode = nextMode;
    form.dataset.authMode = mode;

    toggleButtons.forEach((button) => {
      const isActive = button.dataset.mode === mode;
      button.classList.toggle('selected', isActive);
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    const isRegister = mode === 'register';

    if (nameField && nameInput) {
      nameInput.required = isRegister;
      nameField.hidden = !isRegister;
    }

    registerOnlyElements.forEach((element) => {
      element.hidden = !isRegister;
    });

    if (passwordInput && submitButton) {
      passwordInput.setAttribute('autocomplete', isRegister ? 'new-password' : 'current-password');
      passwordInput.placeholder = isRegister ? 'Create a password' : 'Your password';
      submitButton.textContent = isRegister ? 'Create account' : 'Continue to dashboard';
    }

    if (errorElement) {
      errorElement.hidden = true;
    }
  };

  modeToggle.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) {
      return;
    }
    const { mode } = target.dataset;
    if (mode) {
      setMode(mode);
    }
  });

  try {
    const existing = window.localStorage.getItem(storageKey);
    if (existing) {
      const profile = JSON.parse(existing);
      if (profile?.email && emailInput) {
        emailInput.value = profile.email;
      }
      if (profile?.name && nameInput) {
        nameInput.value = profile.name;
      }
    }
  } catch (error) {
    console.warn('Unable to load stored profile', error);
  }

  const handleAuthRequest = async (endpoint) => {
    if (!form.reportValidity()) {
      return;
    }

    if (errorElement) {
      errorElement.hidden = true;
    }

    const payload = {
      email: emailInput.value.trim(),
      password: passwordInput.value,
    };

    if (mode === 'register' && nameInput) {
      payload.name = nameInput.value.trim();
    }

    try {
      const response = await fetch(`/api/auth/${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const details = await response.json().catch(() => ({ detail: 'Unable to process request.' }));
        const message = details?.detail || details?.error || 'Request rejected.';
        if (errorElement) {
          errorElement.textContent = message;
          errorElement.hidden = false;
        }
        return;
      }

      const result = await response.json().catch(() => null);

      try {
        const profile = {
          name: result?.user?.name || payload.name || '',
          email: result?.user?.email || payload.email || '',
          timestamp: Date.now(),
        };
        window.localStorage.setItem(storageKey, JSON.stringify(profile));
        window.sessionStorage.setItem(storageKey, JSON.stringify(profile));
      } catch (error) {
        console.warn('Unable to persist profile', error);
      }

      window.location.href = '/session';
    } catch (error) {
      console.error('Authentication request failed', error);
      if (errorElement) {
        errorElement.textContent = 'Unexpected error. Please try again.';
        errorElement.hidden = false;
      }
    }
  };

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const endpoint = mode === 'register' ? 'register' : 'login';
    handleAuthRequest(endpoint);
  });

  setMode(mode);
})();
