(() => {
  const form = document.getElementById('admin-access-form');
  if (!form) {
    return;
  }

  const emailField = document.getElementById('admin-email');
  const passwordField = document.getElementById('admin-password');
  const errorElement = document.getElementById('admin-access-error');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) {
      return;
    }

    if (errorElement) {
      errorElement.hidden = true;
    }

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        credentials: 'include',
        body: JSON.stringify({
          email: emailField.value.trim(),
          password: passwordField.value,
        }),
      });

      if (!response.ok) {
        const details = await response.json().catch(() => ({ detail: 'Unable to sign in.' }));
        const message = details?.detail || details?.error || 'Credentials rejected.';
        if (errorElement) {
          errorElement.textContent = message;
          errorElement.hidden = false;
        }
        return;
      }

      const result = await response.json().catch(() => null);
      if (result?.role !== 'admin') {
        if (errorElement) {
          errorElement.textContent = 'Administrator access required for this area.';
          errorElement.hidden = false;
        }
        return;
      }

      window.location.href = '/dashboard';
    } catch (error) {
      console.error('Failed to sign in admin', error);
      if (errorElement) {
        errorElement.textContent = 'Unexpected error during sign-in. Please retry.';
        errorElement.hidden = false;
      }
    }
  });
})();
