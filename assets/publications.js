const search = document.querySelector('#pub-search');
const year = document.querySelector('#pub-year');
const cards = [...document.querySelectorAll('.pub-card')];
const count = document.querySelector('#pub-count');
const topicCloud = document.querySelector('#topic-cloud');
const topicStatus = document.querySelector('#topic-status');
const topicClear = document.querySelector('#topic-clear');
const topicSearch = document.querySelector('#topic-search');

let selectedTopic = '';
let topicRecords = new Map();

function filterPublications() {
  const query = (search?.value || '').trim().toLowerCase();
  const selectedYear = year?.value || '';
  const allowed = selectedTopic ? topicRecords.get(selectedTopic) || new Set() : null;
  let visible = 0;

  cards.forEach((card) => {
    const recordId = Number(card.dataset.recordId);
    const matchesQuery = !query || card.dataset.search.includes(query);
    const matchesYear = !selectedYear || card.dataset.year === selectedYear;
    const matchesTopic = !allowed || allowed.has(recordId);
    card.hidden = !(matchesQuery && matchesYear && matchesTopic);
    if (!card.hidden) visible += 1;
  });

  count.textContent = `${visible} record${visible === 1 ? '' : 's'}`;
  if (topicStatus) {
    topicStatus.textContent = selectedTopic
      ? `Filtering by “${selectedTopic}”. Search and year filters can be combined.`
      : 'Select a normalized topic to filter the publication catalogue.';
  }
  if (topicClear) topicClear.hidden = !selectedTopic;
}

function chooseTopic(topic, button) {
  selectedTopic = selectedTopic === topic ? '' : topic;
  document.querySelectorAll('.topic-chip').forEach((chip) => {
    const active = chip.dataset.topic === selectedTopic;
    chip.classList.toggle('active', active);
    chip.setAttribute('aria-pressed', active ? 'true' : 'false');
  });
  filterPublications();
  if (selectedTopic) document.querySelector('#publication-list')?.scrollIntoView({behavior:'smooth', block:'start'});
}

async function loadTopics() {
  if (!topicCloud) return;
  try {
    const response = await fetch('data/publication_topics.json', {cache: 'no-store'});
    if (!response.ok) throw new Error('Topic data unavailable');
    const data = await response.json();

    topicRecords = new Map(
      Object.entries(data.topics || {}).map(([topic, value]) => [
        topic,
        new Set((value.record_ids || []).map(Number)),
      ])
    );

    const counts = data.topic_counts || [];
    if (!counts.length) throw new Error('No normalized topics found');

    const max = Math.max(...counts.map((d) => Number(d.publications) || 0), 1);
    const min = Math.min(...counts.map((d) => Number(d.publications) || 0), max);

    topicCloud.innerHTML = '';
    counts.forEach(({topic, publications}) => {
      const n = Number(publications) || 0;
      const ratio = max === min ? 0.5 : (Math.sqrt(n) - Math.sqrt(min)) / (Math.sqrt(max) - Math.sqrt(min));
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'topic-chip';
      button.dataset.topic = topic;
      button.setAttribute('aria-pressed', 'false');
      button.style.setProperty('--topic-scale', (0.9 + ratio * 0.75).toFixed(3));
      button.innerHTML = `<span>${topic}</span><small>${n}</small>`;
      button.addEventListener('click', () => chooseTopic(topic, button));
      topicCloud.appendChild(button);
    });

    topicSearch?.addEventListener('input', () => {
      const q = topicSearch.value.trim().toLowerCase();
      document.querySelectorAll('.topic-chip').forEach((chip) => {
        chip.hidden = !!q && !chip.dataset.topic.toLowerCase().includes(q);
      });
    });

    if (topicStatus) {
      topicStatus.textContent = `${data.matched_publications} of ${data.publication_count} indexed works currently match at least one controlled research topic.`;
    }
  } catch (error) {
    topicCloud.innerHTML = '<span class="topic-loading">Normalized topics are temporarily unavailable. Search and year filters still work.</span>';
    if (topicStatus) topicStatus.textContent = '';
  }
}

topicClear?.addEventListener('click', () => {
  selectedTopic = '';
  document.querySelectorAll('.topic-chip').forEach((chip) => {
    chip.classList.remove('active');
    chip.setAttribute('aria-pressed', 'false');
  });
  filterPublications();
});

search?.addEventListener('input', filterPublications);
year?.addEventListener('change', filterPublications);
filterPublications();
loadTopics();
