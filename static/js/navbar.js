const navMount = document.getElementById('navbar');

if (navMount) {
  const links = [
    { label: 'Overview', href: '/' },
    { label: 'Platform', href: '/platform' },
    { label: 'Features', href: '/features' },
    { label: 'Use Cases', href: '/use-cases' },
    { label: 'About', href: '/about' }
  ];

  const navTemplate = `
    <nav class="navbar" data-solid="false">
      <div class="container nav-inner">
        <div class="nav-left">
          <div class="brand-mark" aria-hidden="true">SP</div>
          <span class="brand-name">SkillProof AI</span>
        </div>
        <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav-links">
          <span class="sr-only">Toggle navigation</span>
          <span aria-hidden="true">Menu</span>
        </button>
        <div class="nav-links" id="nav-links" role="navigation" aria-label="Primary"></div>
        <div class="nav-actions" id="nav-actions">
          <a class="btn secondary" href="/access">Candidate Login</a>
          <a class="btn primary" href="/admin/login">Admin Login</a>
        </div>
      </div>
    </nav>
  `;

  navMount.innerHTML = navTemplate;

  const navLinksEl = document.getElementById('nav-links');
  const navActionsEl = document.getElementById('nav-actions');
  const toggle = document.querySelector('.nav-toggle');
  const navbar = navMount.querySelector('.navbar');
  const currentPath = window.location.pathname.replace(/\/$/, '') || '/';

  const navLinks = links
    .map(link => {
      const normalisedHref = link.href.replace(/\/$/, '') || '/';
      const isActive = currentPath === normalisedHref;
      return `<a href="${link.href}" data-nav-link data-active="${isActive}">${link.label}</a>`;
    })
    .join('');

  if (navLinksEl) {
    navLinksEl.innerHTML = navLinks;
  }

  const setSolidState = () => {
    if (!navbar) return;
    const solid = window.scrollY > 32;
    navbar.dataset.solid = solid.toString();
  };

  setSolidState();
  window.addEventListener('scroll', setSolidState);

  if (toggle && navLinksEl && navActionsEl) {
    const closeMenu = () => {
      toggle.setAttribute('aria-expanded', 'false');
      navLinksEl.classList.remove('is-open');
      navActionsEl.classList.remove('is-open');
    };

    toggle.addEventListener('click', () => {
      const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', (!isExpanded).toString());
      navLinksEl.classList.toggle('is-open');
      navActionsEl.classList.toggle('is-open');
    });

    navLinksEl.addEventListener('click', event => {
      const target = event.target;
      if (target instanceof HTMLAnchorElement) {
        closeMenu();
      }
    });
  }
}
