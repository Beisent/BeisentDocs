/* ==========================================================================
   BeisentDocs - Interactive JS
   ========================================================================== */

(function () {
  'use strict';

  // ---- Performance optimization: debounce utility ----------------------
  function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
      const later = () => {
        clearTimeout(timeout);
        func(...args);
      };
      clearTimeout(timeout);
      timeout = setTimeout(later, wait);
    };
  }

  // ---- Theme toggle ----------------------------------------------------
  const themeToggle = document.getElementById('theme-toggle');
  const html = document.documentElement;

  function applyHljsTheme(theme) {
    const light = document.getElementById('hljs-light');
    const dark = document.getElementById('hljs-dark');
    if (light && dark) {
      light.disabled = theme === 'dark';
      dark.disabled = theme !== 'dark';
    }
  }

  // Load saved theme or default to light
  const savedTheme = localStorage.getItem('theme') || 'light';
  html.setAttribute('data-theme', savedTheme);
  applyHljsTheme(savedTheme);

  themeToggle?.addEventListener('click', () => {
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    applyHljsTheme(newTheme);
  });

  // ---- Mobile sidebar toggle -------------------------------------------
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebar-overlay');

  document.getElementById('sidebar-toggle')?.addEventListener('click', () => {
    sidebar?.classList.toggle('open');
  });
  overlay?.addEventListener('click', () => {
    sidebar?.classList.remove('open');
  });

  // ---- Section link: navigate without toggling <details> ---------------
  document.querySelectorAll('.nav-section-title a').forEach(link => {
    link.addEventListener('click', (e) => {
      e.stopPropagation();
    });
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

  // ---- Back to top button ----------------------------------------------
  const backToTop = document.getElementById('back-to-top');
  if (backToTop) {
    const handleScroll = debounce(() => {
      if (window.scrollY > 300) {
        backToTop.classList.add('visible');
      } else {
        backToTop.classList.remove('visible');
      }
    }, 100);

    window.addEventListener('scroll', handleScroll, { passive: true });

    backToTop.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

  // ---- Search functionality --------------------------------------------
  const searchModal = document.getElementById('search-modal');
  const searchToggle = document.getElementById('search-toggle');
  const searchInput = document.getElementById('search-input');
  const searchClose = document.getElementById('search-close');
  const searchResults = document.getElementById('search-results');
  let searchIndex = [];

  // Load search index with error handling
  if (searchModal) {
    // Determine base path from current location
    const basePath = document.querySelector('link[rel="stylesheet"]')?.getAttribute('href')?.replace('static/css/style.css', '') || '';
    fetch(`${basePath}search-index.json`)
      .then(res => {
        if (!res.ok) throw new Error('Failed to load search index');
        return res.json();
      })
      .then(data => { searchIndex = data; })
      .catch(err => console.error('Search index error:', err));
  }

  // Open search modal
  searchToggle?.addEventListener('click', () => {
    searchModal?.classList.add('active');
    searchInput?.focus();
  });

  // Close search modal
  searchClose?.addEventListener('click', () => {
    searchModal?.classList.remove('active');
    searchInput.value = '';
    searchResults.innerHTML = '';
  });

  searchModal?.addEventListener('click', (e) => {
    if (e.target === searchModal) {
      searchModal.classList.remove('active');
      searchInput.value = '';
      searchResults.innerHTML = '';
    }
  });

  // ESC key to close
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && searchModal?.classList.contains('active')) {
      searchModal.classList.remove('active');
      searchInput.value = '';
      searchResults.innerHTML = '';
    }
    // Ctrl+K or Cmd+K to open search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      searchModal?.classList.add('active');
      searchInput?.focus();
    }
  });

  // Search logic with debouncing for better performance
  const performSearch = debounce((query) => {
    if (!query) {
      searchResults.innerHTML = '';
      return;
    }

    const lowerQuery = query.toLowerCase();
    const results = searchIndex.filter(item => {
      return item.title.toLowerCase().includes(lowerQuery) ||
             item.description.toLowerCase().includes(lowerQuery) ||
             item.content.toLowerCase().includes(lowerQuery);
    }).slice(0, 10);

    if (results.length === 0) {
      searchResults.innerHTML = '<div class="search-no-results">No results found</div>';
      return;
    }

    searchResults.innerHTML = results.map(item => {
      const highlightText = (text) => {
        const regex = new RegExp(`(${query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        return text.replace(regex, '<span class="search-result-highlight">$1</span>');
      };

      return `
        <a href="${item.url}" class="search-result-item">
          <div class="search-result-title">${highlightText(item.title)}</div>
          <div class="search-result-excerpt">${highlightText(item.excerpt)}</div>
        </a>
      `;
    }).join('');
  }, 200);

  searchInput?.addEventListener('input', (e) => {
    performSearch(e.target.value.trim());
  });

})();
