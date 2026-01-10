(() => {
  const root = document.documentElement;
  const storageKey = 'skillproof-theme';
  const navAttribute = 'data-open';

  const prefersDark = () => window.matchMedia?.('(prefers-color-scheme: dark)').matches;
  const getStoredTheme = () => {
    try {
      return window.localStorage.getItem(storageKey);
    } catch (error) {
      console.warn('Unable to read theme preference', error);
      return null;
    }
  };

  const setStoredTheme = (theme) => {
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch (error) {
      console.warn('Unable to persist theme preference', error);
    }
  };

  const applyTheme = (theme) => {
    const nextTheme = theme || (prefersDark() ? 'dark' : 'light');
    root.setAttribute('data-theme', nextTheme);
    const toggle = document.querySelector('[data-theme-toggle]');
    if (toggle) {
      toggle.dataset.theme = nextTheme;
      toggle.setAttribute('aria-pressed', nextTheme === 'dark');
    }
    document.dispatchEvent(new CustomEvent('skillproof-theme-change', { detail: { theme: nextTheme } }));
  };

  const initTheme = () => {
    const stored = getStoredTheme();
    applyTheme(stored);
  };

  const bindThemeToggle = () => {
    const toggle = document.querySelector('[data-theme-toggle]');
    if (!toggle) {
      return;
    }

    toggle.addEventListener('click', () => {
      const current = root.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      applyTheme(next);
      setStoredTheme(next);
    });
  };

  const bindMobileNav = () => {
    const navToggle = document.querySelector('[data-nav-toggle]');
    const nav = document.querySelector('[data-nav]');
    if (!navToggle || !nav) {
      return;
    }

    if (!nav.hasAttribute(navAttribute)) {
      nav.setAttribute(navAttribute, 'false');
    }

    const closeNav = () => nav.setAttribute(navAttribute, 'false');

    navToggle.addEventListener('click', () => {
      const isOpen = nav.getAttribute(navAttribute) === 'true';
      nav.setAttribute(navAttribute, String(!isOpen));
      navToggle.setAttribute('aria-expanded', String(!isOpen));
    });

    nav.querySelectorAll('a').forEach((link) => {
      link.addEventListener('click', closeNav);
    });

    window.addEventListener('resize', () => {
      if (window.innerWidth > 860) {
        closeNav();
      }
    });
  };

  document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    bindThemeToggle();
    bindMobileNav();
  });
})();
