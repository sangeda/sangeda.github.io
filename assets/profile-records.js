(() => {
  'use strict';
  const root = document.querySelector('[data-records]');
  if (!root) return;
  const records = JSON.parse(document.getElementById('record-data').textContent);
  const list = document.getElementById('record-list');
  const cards = Array.from(list.children);
  const form = document.getElementById('record-filters');
  const search = document.getElementById('search');
  const filters = Array.from(form.querySelectorAll('[data-filter]'));
  const sort = document.getElementById('sort');
  const normal = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
  const params = new URLSearchParams(location.search);
  for (const input of [search, ...filters, sort]) {
    if (params.has(input.name)) input.value = params.get(input.name);
  }
  if (!sort.value) sort.value = 'newest';
  function update() {
    const words = normal(search.value.trim()).split(/\s+/).filter(Boolean);
    for (const card of cards) {
      card.hidden = !words.every(w => normal(card.textContent).includes(w)) ||
        filters.some(input => input.value && card.dataset[input.dataset.filter] !== input.value);
    }
    cards.sort((a, b) => {
      if (sort.value === 'name') return a.dataset.name.localeCompare(b.dataset.name);
      const x = a.dataset.date, y = b.dataset.date;
      if (!x || !y) return x ? -1 : y ? 1 : 0;
      return sort.value === 'oldest' ? x.localeCompare(y) : y.localeCompare(x);
    }).forEach(card => list.appendChild(card));
    const count = cards.filter(card => !card.hidden).length;
    document.getElementById('record-count').textContent = `${count} of ${cards.length} records`;
    document.getElementById('record-empty').hidden = count !== 0;
    const query = new URLSearchParams();
    for (const input of [search, ...filters, sort]) if (input.value && !(input === sort && input.value === 'newest')) query.set(input.name, input.value);
    history.replaceState(null, '', location.pathname + (query.size ? '?' + query.toString() : '') + location.hash);
  }
  form.addEventListener('submit', e => e.preventDefault());
  form.addEventListener('input', update);
  form.addEventListener('change', update);
  document.getElementById('reset').addEventListener('click', () => { form.reset(); update(); search.focus(); });
  document.getElementById('download').addEventListener('click', () => {
    const byId = new Map(records.map(r => [r.id, r]));
    const selected = cards.filter(card => !card.hidden).map(card => byId.get(card.id));
    const fields = Object.keys(records[0] || {});
    const escape = value => {
      let s = String(value ?? '');
      if (/^[\s]*[=+@-]/.test(s)) s = "'" + s;
      return '"' + s.replace(/"/g, '""') + '"';
    };
    const csv = '\uFEFF' + [fields, ...selected.map(r => fields.map(k => r[k]))].map(row => row.map(escape).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv], {type:'text/csv;charset=utf-8'}));
    const a = document.createElement('a'); a.href = url; a.download = `Sangeda_${root.dataset.records}_filtered.csv`; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
  document.querySelectorAll('[data-enhanced]').forEach(el => { el.hidden = false; });
  update();
})();
