(() => {
  const form = document.getElementById('access-form');
  if (!form) {
    return;
  }

  const nameField = document.getElementById('access-name');
  const contactField = document.getElementById('access-contact');
  const storageKey = 'skillproof-access-profile';

  try {
    const existing = window.localStorage.getItem(storageKey);
    if (existing) {
      const profile = JSON.parse(existing);
      if (profile?.name) {
        nameField.value = profile.name;
      }
      if (profile?.contact) {
        contactField.value = profile.contact;
      }
    }
  } catch (error) {
    console.warn('Unable to load stored profile', error);
  }

  form.addEventListener('submit', (event) => {
    event.preventDefault();
    if (!form.reportValidity()) {
      return;
    }

    const profile = {
      name: nameField.value.trim(),
      contact: contactField.value.trim(),
      timestamp: Date.now(),
    };

    try {
      window.localStorage.setItem(storageKey, JSON.stringify(profile));
      window.sessionStorage.setItem(storageKey, JSON.stringify(profile));
    } catch (error) {
      console.warn('Unable to persist profile', error);
    }

    window.location.href = '/session';
  });
})();
