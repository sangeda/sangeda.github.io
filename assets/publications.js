const search = document.querySelector('#pub-search');
const year = document.querySelector('#pub-year');
const cards = [...document.querySelectorAll('.pub-card')];
const count = document.querySelector('#pub-count');

function filterPublications() {
  const query = (search?.value || '').trim().toLowerCase();
  const selectedYear = year?.value || '';
  let visible = 0;
  cards.forEach((card) => {
    const matchesQuery = !query || card.dataset.search.includes(query);
    const matchesYear = !selectedYear || card.dataset.year === selectedYear;
    card.hidden = !(matchesQuery && matchesYear);
    if (!card.hidden) visible += 1;
  });
  count.textContent = `${visible} record${visible === 1 ? '' : 's'}`;
}

search?.addEventListener('input', filterPublications);
year?.addEventListener('change', filterPublications);
