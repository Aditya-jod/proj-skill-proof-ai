const footerMount = document.getElementById('footer');

if (footerMount) {
  footerMount.innerHTML = `
    <footer class="footer" role="contentinfo">
      <div class="container footer-inner">
        <span>© ${new Date().getFullYear()} SkillProof AI. Every decision traceable.</span>
        <nav class="footer-nav" aria-label="Footer">
          <a href="/about">About</a>
          <a href="/use-cases">Use Cases</a>
          <a href="/access">Candidate</a>
          <a href="/admin/login">Admin</a>
        </nav>
      </div>
    </footer>
  `;
}
