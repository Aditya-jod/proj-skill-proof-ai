export const apiRequest = async (endpoint, options = {}) => {
  const defaults = {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
  };

  const merged = {
    ...defaults,
    ...options,
    headers: {
      ...defaults.headers,
      ...(options.headers || {}),
    },
  };

  const response = await fetch(endpoint, merged);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const message = detail?.detail || detail?.error || `Request to ${endpoint} failed`;
    throw new Error(message);
  }

  return response.json().catch(() => null);
};
