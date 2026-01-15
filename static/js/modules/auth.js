const storageKey = 'skillproof-access-profile';

const initCandidateAccess = () => {
  const form = document.getElementById('access-form');
  const toggle = document.querySelector('[data-auth-mode-toggle]');
  if (!form || !toggle) {
    return;
  }

  const toggleButtons = Array.from(toggle.querySelectorAll('button[data-mode]'));
  const nameField = form.querySelector('[data-auth-section="register"]');
  const nameInput = form.querySelector('input[name="name"]');
  const emailInput = form.querySelector('input[name="email"]');
  const passwordInput = form.querySelector('input[name="password"]');
  const errorElement = document.getElementById('auth-error') || document.createElement('p');
  if (!errorElement.id) {
    errorElement.id = 'auth-error';
    errorElement.classList.add('form-error');
    errorElement.hidden = true;
    form.appendChild(errorElement);
  }
  const submitButton = form.querySelector('[data-auth-submit]') || form.querySelector('button[type="submit"]');
  const helperBlocks = form.querySelectorAll('[data-auth-copy="register"]');

  let mode = form.dataset.authMode || 'login';

  const setMode = (nextMode) => {
    mode = nextMode;
    form.dataset.authMode = mode;

    toggleButtons.forEach((button) => {
      const isActive = button.dataset.mode === mode;
      button.dataset.active = isActive.toString();
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    const isRegister = mode === 'register';

    if (nameField && nameInput) {
      nameField.hidden = !isRegister;
      nameInput.required = isRegister;
    }

    helperBlocks.forEach((block) => {
      block.hidden = !isRegister;
    });

    if (passwordInput && submitButton) {
      passwordInput.setAttribute('autocomplete', isRegister ? 'new-password' : 'current-password');
      passwordInput.placeholder = isRegister ? 'Create a password' : 'Your password';
      submitButton.textContent = isRegister ? 'Create account' : 'Continue';
      submitButton.dataset.authSubmit = 'true';
    }

    errorElement.hidden = true;
  };

  toggle.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof HTMLButtonElement)) {
      return;
    }
    const nextMode = target.dataset.mode;
    if (nextMode) {
      setMode(nextMode);
    }
  });

  try {
    const cached = window.localStorage.getItem(storageKey);
    if (cached) {
      const profile = JSON.parse(cached);
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

    errorElement.hidden = true;

    const payload = {
      email: emailInput?.value.trim() || '',
      password: passwordInput?.value || '',
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
        errorElement.textContent = message;
        errorElement.hidden = false;
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
      errorElement.textContent = 'Unexpected error. Please try again.';
      errorElement.hidden = false;
    }
  };

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const endpoint = mode === 'register' ? 'register' : 'login';
    handleAuthRequest(endpoint);
  });

  setMode(mode);
};

const initAdminAccess = () => {
  const container = document.querySelector('[data-admin-auth]');
  if (!container) {
    return;
  }

  const form = container.querySelector('form[data-admin-form]');
  const toggle = container.querySelector('[data-admin-toggle]');
  const toggleButtons = toggle ? Array.from(toggle.querySelectorAll('button[data-mode]')) : [];
  const nameField = container.querySelector('[data-admin-field="name"]');
  const nameInput = container.querySelector('input[name="name"]');
  const emailInput = container.querySelector('input[name="email"]');
  const passwordInput = container.querySelector('input[name="password"]');
  const submitButton = container.querySelector('[data-admin-submit]');
  const errorElement = container.querySelector('[data-admin-error]');

  if (!form || !passwordInput || !emailInput || !submitButton || !errorElement) {
    return;
  }

  let mode = container.dataset.adminMode || 'login';

  const setMode = (nextMode) => {
    mode = nextMode;
    container.dataset.adminMode = mode;
    const isRegister = mode === 'register';

    toggleButtons.forEach((button) => {
      const isActive = button.dataset.mode === mode;
      button.dataset.active = isActive.toString();
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
    });

    if (nameField && nameInput) {
      nameField.hidden = !isRegister;
      nameInput.required = isRegister;
    }

    passwordInput.placeholder = isRegister ? 'Create a password' : 'Your password';
    passwordInput.setAttribute('autocomplete', isRegister ? 'new-password' : 'current-password');
    submitButton.textContent = isRegister ? 'Create admin account' : 'Sign in';
    errorElement.hidden = true;
  };

  if (toggle) {
    toggle.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof HTMLButtonElement)) {
        return;
      }
      const nextMode = target.dataset.mode;
      if (nextMode) {
        setMode(nextMode);
      }
    });
  }

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) {
      return;
    }

    errorElement.hidden = true;

    const payload = {
      email: emailInput.value.trim(),
      password: passwordInput.value,
    };

    let endpoint = 'login';

    if (mode === 'register') {
      endpoint = 'admin/register';
      if (nameInput) {
        payload.name = nameInput.value.trim();
      }
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
        errorElement.textContent = message;
        errorElement.hidden = false;
        return;
      }

      const result = await response.json().catch(() => null);
      if (result?.role !== 'admin') {
        errorElement.textContent = 'Administrator access required for this area.';
        errorElement.hidden = false;
        return;
      }

      window.location.href = '/dashboard';
    } catch (error) {
      console.error('Failed to submit admin auth request', error);
      errorElement.textContent = 'Unexpected error. Please retry.';
      errorElement.hidden = false;
    }
  });

  setMode(mode);
};

initCandidateAccess();
initAdminAccess();
