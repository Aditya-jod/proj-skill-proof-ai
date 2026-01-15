const navbar = document.querySelector('[data-nav]');

if (navbar) {
  const toggle = navbar.querySelector('[data-nav-toggle]');
  const navLinks = navbar.querySelector('#primary-nav');
  const navActions = navbar.querySelector('[data-nav-actions]');

  const closeMenu = () => {
    if (!toggle || !navLinks || !navActions) {
      return;
    }
    toggle.setAttribute('aria-expanded', 'false');
    navLinks.classList.remove('is-open');
    navActions.classList.remove('is-open');
  };

  const toggleMenu = () => {
    if (!toggle || !navLinks || !navActions) {
      return;
    }
    const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
    toggle.setAttribute('aria-expanded', (!isExpanded).toString());
    navLinks.classList.toggle('is-open');
    navActions.classList.toggle('is-open');
  };

  const setSolidState = () => {
    const shouldSolidify = window.scrollY > 32;
    navbar.dataset.solid = shouldSolidify.toString();
  };

  setSolidState();

  window.addEventListener('scroll', setSolidState, { passive: true });
  window.addEventListener('resize', () => {
    if (window.matchMedia('(min-width: 960px)').matches) {
      closeMenu();
    }
  });

  if (toggle && navLinks && navActions) {
    toggle.addEventListener('click', toggleMenu);
    navLinks.addEventListener('click', (event) => {
      const target = event.target;
      if (target instanceof HTMLAnchorElement) {
        closeMenu();
      }
    });
  }
}
