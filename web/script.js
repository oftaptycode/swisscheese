const seenIDs = new Set();

const formatPublishedDate = (dateString) => {
  if (!dateString) return "";
  const dateObj = new Date(dateString);
  return dateObj.toLocaleString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).replace(' at ', ' ');
};

function makeCard(item, extraClass = "") {
  const card = document.createElement("div");
  card.className = "tz-card" + (extraClass ? " " + extraClass : "");
  if (item.level === 'active active-critical') card.classList.add("critical");
  card.innerHTML = `
    <div class="tz-top">
      <a href="${item.url}" target="_blank" class="tz-city news-card-title ${extraClass}">${item.title}</a>
    </div>
    <div class="tz-date">${formatPublishedDate(item.published)}</div>`;
  return card;
}

async function pollNews() {
  const [newsRes, breakingRes] = await Promise.all([
    fetch("https://swisscheese-production.up.railway.app/news"),
    fetch("https://swisscheese-production.up.railway.app/news/breaking")
  ]);
  const news = await newsRes.json();
  const breaking = await breakingRes.json();

  const newsList = document.getElementById("news-list");
  const breakingList = document.getElementById("breaking-news-list");
  const breakingSection = document.getElementById("breaking-news-section");

  // Collect unseen items, reverse so newest ends up on top after prepend
  const newItems = news.filter(item => !seenIDs.has(item.id));
  newItems.reverse().forEach(item => {
    seenIDs.add(item.id);
    newsList.prepend(makeCard(item));
  });

  // Rebuild breaking news each poll — drop items older than 24 hours
  const twentyFourHoursAgo = Date.now() - 24 * 60 * 60 * 1000;
  const freshBreaking = breaking.filter(item => new Date(item.published).getTime() > twentyFourHoursAgo);

  breakingList.innerHTML = "";
  if (freshBreaking.length > 0) {
    breakingSection.style.display = "block";
    freshBreaking.forEach(item => breakingList.appendChild(makeCard(item, "flashing breaking-news-card-title")));
  } else {
    breakingSection.style.display = "none";
  }
}

const zones = [
  { city: 'New York', tz: 'America/New_York', market: 'NYSE' },
  { city: 'London', tz: 'Europe/London', market: 'LSE' },
  { city: 'Tokyo', tz: 'Asia/Tokyo', market: 'TSE' },
  { city: 'Sydney', tz: 'Australia/Sydney', market: 'ASX' },
];

function isMarketOpen(market, h, m, day) {
  if (day < 1 || day > 5) return false;
  const time = h * 60 + m;
  switch (market) {
    case 'NYSE': return time >= (9 * 60 + 30) && time < (16 * 60);
    case 'LSE': return time >= (8 * 60) && time < (16 * 60 + 30);
    case 'Euronext': return time >= (9 * 60) && time < (17 * 60 + 30);
    case 'TSE':
      const morning = time >= (9 * 60) && time < (11 * 60 + 30);
      const afternoon = time >= (12 * 60 + 30) && time < (15 * 60);
      return morning || afternoon;
    case 'ASX': return time >= (10 * 60) && time < (16 * 60);
    default: return false;
  }
}

function getOffset(tz) {
  const now = new Date();
  const fmt = new Intl.DateTimeFormat('en', { timeZone: tz, timeZoneName: 'shortOffset' });
  const parts = fmt.formatToParts(now);
  const off = parts.find(p => p.type === 'timeZoneName')?.value || '';
  return off.replace('GMT', 'UTC');
}

function getParts(tz) {
  const now = new Date();
  const fmt = new Intl.DateTimeFormat('en-US', {
    timeZone: tz,
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false, weekday: 'short', month: 'short', day: 'numeric'
  });
  const parts = fmt.formatToParts(now);
  const get = t => parts.find(p => p.type === t)?.value || '';
  let h = get('hour'), m = get('minute'), s = get('second');
  if (h === '24') h = '00';
  const hNum = parseInt(h, 10);
  const mNum = parseInt(m, 10);
  const isDay = hNum >= 6 && hNum < 20;
  const dateStr = `${get('weekday')} ${get('month')} ${get('day')}`;
  // Get numeric wall-clock day of week (0-6)
  const dayOfWeek = new Date(now.toLocaleString('en-US', { timeZone: tz })).getDay();
  return { h, m, s, hNum, mNum, dayOfWeek, isDay, dateStr };
}

const grid = document.getElementById('grid');

function initGrid() {
  const offsets = zones.map(z => getOffset(z.tz));
  const continentColors = {
    America: '255, 123, 114',
    Europe: '126, 231, 135',
    Asia: '210, 168, 255',
    Australia: '121, 192, 255',
    Africa: '255, 176, 0',
    Pacific: '57, 197, 207',
    Atlantic: '242, 204, 96'
  };

  zones.forEach((z, i) => {
    const continent = z.tz.split('/')[0];
    const rgb = continentColors[continent] || '126, 184, 247';
    const card = document.createElement('div');
    card.className = 'tz-card';
    card.id = 'card-' + i;
    card.innerHTML = `
      <div class="tz-top">
        <span class="tz-city" style="font-family: 'Libre Baskerville', serif; font-weight: 700;">${z.city}</span>
        <span class="tz-offset" style="--c: ${rgb};">${offsets[i]}</span>
      </div>
      <div class="tz-time" id="time-${i}"></div>
      <div class="tz-date" id="date-${i}"></div>
    `;
    grid.appendChild(card);
  });
}

function tick() {
  const now = new Date();
  const utcH = String(now.getUTCHours()).padStart(2, '0');
  const utcM = String(now.getUTCMinutes()).padStart(2, '0');
  const utcS = String(now.getUTCSeconds()).padStart(2, '0');
  const utcClock = document.getElementById('utc-clock');
  if (utcClock) utcClock.textContent = `${utcH}:${utcM}:${utcS}`;

  zones.forEach((z, i) => {
    const { h, m, s, hNum, mNum, dayOfWeek, dateStr } = getParts(z.tz);
    const card = document.getElementById('card-' + i);
    const timeEl = document.getElementById('time-' + i);
    const dateEl = document.getElementById('date-' + i);

    if (card && timeEl && dateEl) {
      const isOpen = isMarketOpen(z.market, hNum, mNum, dayOfWeek);
      card.classList.toggle('is-open', isOpen);

      timeEl.innerHTML = `${h}:${m}<span class="sec">:${s}</span>`;
      dateEl.textContent = dateStr;
    }
  });
}

// Initialization
document.addEventListener('DOMContentLoaded', () => {
  initGrid();
  pollNews();
  tick();
  setInterval(pollNews, 10000);
  setInterval(tick, 1000);
});
