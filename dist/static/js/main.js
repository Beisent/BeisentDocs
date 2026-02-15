/* ==========================================================================
   BeisentDocs - Interactive JS
   ========================================================================== */

(function () {
  'use strict';

  // ---- Mobile sidebar toggle -------------------------------------------
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    sidebar?.classList.toggle('open');
  });
  overlay?.addEventListener('click', () => {
    sidebar?.classList.remove('open');
  });

  // ---- Copy button on code blocks --------------------------------------
  document.querySelectorAll('pre code').forEach((block) => {
    const btn = document.createElement('button');
    btn.className = 'copy-btn';
    btn.textContent = 'Copy';
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(block.textContent).then(() => {
        btn.textContent = 'Copied!';
        setTimeout(() => { btn.textContent = 'Copy'; }, 2000);
      });
    });
    block.parentElement.style.position = 'relative';
    block.parentElement.appendChild(btn);
  });

  // ---- Active TOC tracking ---------------------------------------------
  const tocLinks = document.querySelectorAll('.toc-link');
  if (tocLinks.length) {
    const headings = [];
    tocLinks.forEach((link) => {
      const id = link.getAttribute('href')?.slice(1);
      const el = id && document.getElementById(id);
      if (el) headings.push({ el, link });
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            tocLinks.forEach((l) => l.classList.remove('active'));
            const match = headings.find((h) => h.el === entry.target);
            if (match) match.link.classList.add('active');
          }
        });
      },
      { rootMargin: '-80px 0px -60% 0px', threshold: 0.1 }
    );

    headings.forEach(({ el }) => observer.observe(el));
  }

})();
