
(() => {
  'use strict';
  document.documentElement.classList.add('enhanced');
  const toc = document.querySelector('.toc');
  const toggle = document.getElementById('toc-toggle');
  toggle.addEventListener('click', () => {
    const open = toc.classList.toggle('is-open');
    toggle.setAttribute('aria-expanded', String(open));
  });
  const navLinks = Array.from(document.querySelectorAll('.toc-links a'));
  navLinks.forEach(link => link.addEventListener('click', () => {
    toc.classList.remove('is-open');
    toggle.setAttribute('aria-expanded', 'false');
  }));
  const input = document.getElementById('program-search');
  const scope = document.getElementById('program-scope');
  const programs = Array.from(document.querySelectorAll('[data-program]'));
  function filterPrograms() {
    const query = input.value.trim().toLocaleLowerCase('ru');
    let count = 0;
    programs.forEach(row => {
      const inScope = scope.value === 'all' || (scope.value === 'queue' && row.dataset.queue === 'true') ||
        (scope.value === 'tested' && row.dataset.tested === 'true');
      const show = inScope && row.dataset.search.includes(query);
      row.hidden = !show;
      if (show) count += 1;
    });
    document.getElementById('program-count').textContent = `Показано ${count} из ${programs.length}`;
    document.getElementById('program-empty').hidden = count !== 0;
  }
  input.addEventListener('input', filterPrograms);
  scope.addEventListener('change', filterPrograms);
  filterPrograms();
  const sections = Array.from(document.querySelectorAll('main section[id]'));
  let scheduled = false;
  function updateLocation() {
    const line = window.innerWidth <= 760 ? 120 : 100;
    let active = sections[0];
    for (const section of sections) {
      if (section.getBoundingClientRect().top <= line) active = section;
    }
    navLinks.forEach(link => {
      if (link.hash === '#' + active.id) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
    scheduled = false;
  }
  window.addEventListener('scroll', () => {
    if (!scheduled) { scheduled = true; window.requestAnimationFrame(updateLocation); }
  }, { passive: true });
  window.addEventListener('resize', updateLocation);
  updateLocation();
})();
