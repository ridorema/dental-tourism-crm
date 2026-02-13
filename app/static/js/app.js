(function(){
  const key = 'crm-theme';
  const root = document.documentElement;
  const saved = localStorage.getItem(key);
  if (saved) root.setAttribute('data-theme', saved);
  window.toggleTheme = function() {
    const next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
    root.setAttribute('data-theme', next);
    localStorage.setItem(key, next);
  }
})();
