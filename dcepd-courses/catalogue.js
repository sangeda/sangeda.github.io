'use strict';
const normalise = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
const form = document.querySelector('#filters');
const query = document.querySelector('#query');
const category = document.querySelector('#category');
const school = document.querySelector('#school');
const cards = [...document.querySelectorAll('.course')];
function filterCourses() {
  const terms = normalise(query.value).split(/\s+/).filter(Boolean);
  let count = 0;
  for (const card of cards) {
    const match = (!category.value || card.dataset.category === category.value) &&
      (!school.value || card.dataset.school === school.value) &&
      terms.every(term => term.length <= 2 ? card.dataset.search.split(' ').includes(term) : card.dataset.search.includes(term));
    card.hidden = !match;
    if (match) count++;
  }
  document.querySelector('#result-count').textContent = `${count} of ${cards.length} courses`;
  document.querySelector('#no-results').hidden = count > 0;
  const params = new URLSearchParams();
  if (query.value.trim()) params.set('q', query.value.trim());
  if (category.value) params.set('category', category.value);
  if (school.value) params.set('school', school.value);
  history.replaceState(null, '', location.pathname + (params.size ? '?' + params.toString() : '') + location.hash);
}
const initial = new URLSearchParams(location.search);
query.value = initial.get('q') || '';
category.value = initial.get('category') || '';
school.value = initial.get('school') || '';
form.addEventListener('input', filterCourses);
form.addEventListener('change', filterCourses);
form.addEventListener('submit', event => { event.preventDefault(); filterCourses(); });
form.addEventListener('reset', () => setTimeout(filterCourses, 0));
filterCourses();
