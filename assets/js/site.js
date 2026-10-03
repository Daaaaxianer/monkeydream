/* Every interaction runs in the browser; no API or database is required. */
(() => {
  const menu = document.querySelector('.menu-button');
  menu?.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    document.querySelector('#main-nav').classList.toggle('open', open);
  });
  async function copy(button, text) {
    const label = button.textContent;
    try {
      await navigator.clipboard.writeText(text);
      button.textContent = '已复制';
    } catch {
      button.textContent = '请手动复制';
    }
    setTimeout(() => { button.textContent = label; }, 1800);
  }
  document.querySelectorAll('[data-copy]').forEach(button => {
    button.addEventListener('click', () => copy(button, button.dataset.copy));
  });
  document.querySelectorAll('.article-body pre').forEach(pre => {
    const button = document.createElement('button');
    button.type = 'button'; button.className = 'copy-code'; button.textContent = '复制';
    const source = (pre.querySelector('code') || pre).textContent;
    button.addEventListener('click', () => copy(button, source));
    pre.append(button);
  });
  document.querySelectorAll('.article-body table').forEach(table => {
    const wrap = document.createElement('div'); wrap.className = 'table-scroll';
    table.before(wrap); wrap.append(table);
  });
  const toc = document.querySelector('#toc');
  if (toc) {
    document.querySelectorAll('#article-body h2, #article-body h3').forEach((heading, i) => {
      if (!heading.id) heading.id = `section-${i + 1}`;
      const a = document.createElement('a'); a.href = `#${heading.id}`;
      a.textContent = heading.textContent; a.className = heading.tagName === 'H3' ? 'sub' : '';
      toc.append(a);
    });
    if (!toc.children.length) toc.closest('aside').hidden = true;
  }
  const top = document.querySelector('.back-top');
  if (top) {
    const refresh = () => { top.hidden = window.scrollY < 500; };
    window.addEventListener('scroll', refresh, { passive: true }); refresh();
    top.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
  }
  const form = document.querySelector('#blog-filter');
  if (!form) return;
  const posts = JSON.parse(document.querySelector('#post-index').textContent);
  const fields = ['q', 'type', 'evidence', 'session'];
  const params = new URLSearchParams(location.search);
  fields.forEach(name => { form.elements[name].value = params.get(name) || ''; });
  function filter(updateURL = true) {
    const values = Object.fromEntries(fields.map(name => [name, form.elements[name].value.trim()]));
    const terms = values.q.toLocaleLowerCase().split(/\s+/).filter(Boolean);
    let count = 0;
    posts.forEach((post, i) => {
      const match = terms.every(t => post.search.toLocaleLowerCase().includes(t))
        && (!values.type || post.type === values.type)
        && (!values.evidence || post.evidence === values.evidence)
        && (!values.session || post.sessions.some(s => s.toUpperCase().includes(values.session.toUpperCase())));
      document.querySelector(`[data-post="${i}"]`).hidden = !match;
      if (match) count++;
    });
    document.querySelector('#filter-count').textContent = `${count} 篇文章`;
    document.querySelector('#search-empty').hidden = count !== 0;
    if (updateURL) {
      const query = new URLSearchParams();
      fields.forEach(name => { if (values[name]) query.set(name, values[name]); });
      history.replaceState(null, '', location.pathname + (query.size ? '?' + query : '') + location.hash);
    }
  }
  form.addEventListener('submit', e => { e.preventDefault(); filter(); });
  form.addEventListener('input', () => filter());
  form.addEventListener('reset', () => setTimeout(() => filter(), 0));
  filter(false);
})();
