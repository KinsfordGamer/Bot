// ========== STATE ==========
let currentAnime = null;
let currentFilter = '';

// ========== INIT ==========
document.addEventListener('DOMContentLoaded', () => {
  checkAuth();
  loadLatestEps();
});

// ========== AUTH ==========
async function checkAuth() {
  try {
    const res = await fetch('/auth/me');
    const data = await res.json();
    const btn = document.getElementById('authBtn');
    if (data.logged_in && btn) {
      btn.textContent = `👤 ${data.user.name}`;
      btn.onclick = () => { window.location.href = '/auth/logout'; };
    }
  } catch {}
}

async function doLogin() {
  const email = document.getElementById('loginEmail').value;
  const password = document.getElementById('loginPassword').value;
  const errEl = document.getElementById('loginError');
  try {
    const res = await fetch('/auth/login', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (data.success) {
      closeModal('auth');
      const btn = document.getElementById('authBtn');
      if (btn) { btn.textContent = `👤 ${data.user.name}`; btn.onclick = () => window.location.href='/auth/logout'; }
      errEl.textContent = '';
    } else {
      errEl.textContent = data.error || 'Xato';
    }
  } catch { errEl.textContent = 'Server xatosi'; }
}

async function doRegister() {
  const name = document.getElementById('regName').value;
  const email = document.getElementById('regEmail').value;
  const password = document.getElementById('regPassword').value;
  const errEl = document.getElementById('regError');
  try {
    const res = await fetch('/auth/register', {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ name, email, password })
    });
    const data = await res.json();
    if (data.success) {
      closeModal('auth');
      const btn = document.getElementById('authBtn');
      if (btn) { btn.textContent = `👤 ${data.user.name}`; btn.onclick = () => window.location.href='/auth/logout'; }
      errEl.textContent = '';
    } else {
      errEl.textContent = data.error || 'Xato';
    }
  } catch { errEl.textContent = 'Server xatosi'; }
}

function loginWithTelegram() {
  window.open(`https://t.me/${TG_BOT_USERNAME || 'ATNALTIK'}`, '_blank');
}

// ========== LOAD DATA ==========
async function loadLatestEps() {
  try {
    const res = await fetch('/api/latest-episodes');
    const eps = await res.json();
    const g = document.getElementById('epsGrid');
    if (!g) return;
    g.innerHTML = eps.map(e => `
      <div class="card-ep" onclick="openAnime(${e.anime_id})">
        <div class="ep-num">${e.num}</div>
        <div class="ep-body">
          <div class="ep-anime">${e.anime_title}</div>
          <div class="ep-title">${e.season_title} ${e.is_new ? '<span class="ep-new">YANGI</span>' : ''}</div>
          <div class="ep-meta">${e.duration}</div>
        </div>
        <div class="ep-play">▶</div>
      </div>
    `).join('');
  } catch {}
}

// ========== OPEN ANIME (from API) ==========
async function openAnime(id) {
  try {
    const res = await fetch(`/api/animes/${id}`);
    const anime = await res.json();
    currentAnime = anime;
    renderDetailPage(anime);
    showPage('detail');
  } catch {
    // fallback: direct navigation
    window.location.href = `/anime/${id}`;
  }
}

// ========== STATE ==========
let plyrPlayer = null;

// ========== VIDEO STREAMING ==========
async function playEpisode(episodeId, telegramUrl) {
  const frame = document.getElementById('videoFrame');
  const modal = document.getElementById('modal-video');
  modal.classList.add('open');

  // Loading state
  frame.innerHTML = `
    <div class="video-placeholder" id="vLoader">
      <div class="big-icon" style="animation:pulse 1s infinite">⌛</div>
      <p>Video tayyorlanmoqda...</p>
    </div>
    <div id="playerContainer" style="display:none; width:100%; height:100%">
      <video id="mainVideo" playsinline controls preload="metadata" crossorigin="anonymous">
        <source src="/api/stream/${episodeId}" type="video/mp4">
      </video>
    </div>
  `;

  const video = document.getElementById('mainVideo');
  const loader = document.getElementById('vLoader');
  const container = document.getElementById('playerContainer');

  // Initialize Plyr
  if (plyrPlayer) plyrPlayer.destroy();
  plyrPlayer = new Plyr(video, {
    tooltips: { controls: true, seek: true },
    autoplay: true,
    muted: false, // Ovozli boshlashga urinish
    keyboard: { focused: true, global: true }
  });

  video.oncanplay = () => {
    loader.style.display = 'none';
    container.style.display = 'block';
    // Mobil brauzerlarda ovozli autoplay bloklanishi mumkin
    plyrPlayer.play().catch(() => {
        console.log("Ovozli autoplay bloklandi, muted rejimda urinish...");
        plyrPlayer.muted = true;
        plyrPlayer.play();
    });
  };

  video.onerror = async (e) => {
    console.error("Video error:", video.error);
    
    // Serverdan kelgan xabarni tekshirish (JSON bo'lishi mumkin)
    let serverError = null;
    try {
        const checkRes = await fetch(`/api/stream/${episodeId}`, { method: 'HEAD' });
        if (!checkRes.ok) {
            // Agar xato bo'lsa, batafsil ma'lumot olish uchun GET so'rov qilamiz
            const getRes = await fetch(`/api/stream/${episodeId}`);
            const errData = await getRes.json();
            serverError = errData.error;
        }
    } catch(err) {}

    frame.innerHTML = `
      <div class="video-placeholder">
        <div style="font-size:3rem;margin-bottom:16px">${serverError ? '⚠️' : '🎬'}</div>
        <h3 style="margin-bottom:8px">${serverError ? 'Server xatosi' : 'Format qo\'llab-quvvatlanmaydi'}</h3>
        <p style="margin-bottom:20px;color:var(--text2);padding:0 20px;font-size:14px">
          ${serverError || 'Ushbu video formati (MKV/HEVC) yoki brauzer cheklovi sababli video ochilmadi. Telegram orqali ko\'ring yoki videoni yuklab oling.'}
        </p>
        <div style="display:flex; flex-direction:column; gap:10px; width:100%; max-width:280px">
          <button class="btn btn-primary" onclick="window.open('${telegramUrl || 'https://t.me/ATNALTIK'}','_blank')">
              ✈ Telegram orqali ko'rish
          </button>
          <a href="/api/stream/${episodeId}" download class="btn btn-ghost" style="text-decoration:none; text-align:center">
              📥 Videoni yuklab olish
          </a>
          <button class="btn btn-sm" onclick="closeVideoModal()" style="color:var(--text3)">Yopish</button>
        </div>
      </div>
    `;
  };
}

// ========== RENDER DETAIL PAGE ==========
function renderDetailPage(anime) {
  document.getElementById('detailBg').innerHTML = anime.cover_image 
    ? `<img src="${anime.cover_image}" style="opacity:.15; filter:blur(40px)">` 
    : `<span style="font-size:8rem;opacity:.15">${anime.icon}</span>`;
    
  document.getElementById('detailPoster').innerHTML = anime.cover_image 
    ? `<img src="${anime.cover_image}" alt="${anime.title}">` 
    : `<span style="font-size:5rem">${anime.icon}</span>`;
  document.getElementById('detailTitle').textContent = anime.title;
  document.getElementById('detailOriginal').textContent = anime.original_title;
  document.getElementById('detailScore').innerHTML = `⭐ ${anime.score} / 10`;
  document.getElementById('detailStatus').textContent = anime.status;
  document.getElementById('detailDesc').textContent = anime.description;
  document.getElementById('detailGenres').innerHTML = (anime.genres || []).map(g =>
    `<span class="detail-genre-tag">${g}</span>`
  ).join('');

  // Watch button — first episode
  const btnWatch = document.getElementById('btnWatch');
  if (anime.seasons && anime.seasons.length > 0 && anime.seasons[0].episodes.length > 0) {
    const firstEp = anime.seasons[0].episodes[0];
    btnWatch.onclick = () => playEpisode(firstEp.id, firstEp.telegram_url);
  }

  // Episodes list
  const epDiv = document.getElementById('detail-episodes');
  epDiv.innerHTML = (anime.seasons || []).map((s, si) => `
    <div class="season-block">
      <div class="season-block-head" onclick="toggleSeason(${si})">
        <div class="season-block-title">
          <span>${anime.icon}</span>
          ${s.title} — ${s.year}
        </div>
        <div style="display:flex;align-items:center;gap:12px">
          <span class="season-block-eps">${s.episodes.length} qism</span>
          <span class="season-block-toggle" id="stoggle-${si}">▼</span>
        </div>
      </div>
      <div class="eps-list ${si === 0 ? 'open' : ''}" id="slist-${si}">
        ${(s.episodes || []).map(e => `
          <div class="ep-item" onclick="playEpisode(${e.id},'${e.telegram_url}')">
            <div class="ep-item-num">${e.num}</div>
            <div class="ep-item-info">
              <div class="ep-item-title">${e.title}</div>
              <div class="ep-item-dur">${e.duration}</div>
            </div>
            ${e.is_new ? '<span class="ep-item-new">YANGI</span>' : ''}
            ${e.telegram_file_id ? '<span style="font-size:10px;color:#4caf50;margin-left:6px">📁</span>' : ''}
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');

  // Info tab
  document.getElementById('detail-info').innerHTML = `
    <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:1rem;padding:1rem 0">
      <div style="background:var(--card);border:1px solid var(--card-b);border-radius:var(--r-sm);padding:14px 18px">
        <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Chiqarilgan yil</div>
        <div style="font-size:15px;font-weight:600">${anime.year}</div>
      </div>
      <div style="background:var(--card);border:1px solid var(--card-b);border-radius:var(--r-sm);padding:14px 18px">
        <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Holat</div>
        <div style="font-size:15px;font-weight:600">${anime.status}</div>
      </div>
      <div style="background:var(--card);border:1px solid var(--card-b);border-radius:var(--r-sm);padding:14px 18px">
        <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Fasllar</div>
        <div style="font-size:15px;font-weight:600">${(anime.seasons || []).length}</div>
      </div>
      <div style="background:var(--card);border:1px solid var(--card-b);border-radius:var(--r-sm);padding:14px 18px">
        <div style="font-size:11px;color:var(--text3);text-transform:uppercase;letter-spacing:.08em;margin-bottom:6px">Reyting</div>
        <div style="font-size:15px;font-weight:600;color:#ffd700">⭐ ${anime.score} / 10</div>
      </div>
    </div>
  `;
}

// ========== FILTERS ==========
async function filterTab(btn, genre) {
  document.querySelectorAll('#animeTabs .tab').forEach(t => t.classList.remove('on'));
  btn.classList.add('on');
  currentFilter = genre;
  try {
    const res = await fetch(`/api/animes?genre=${encodeURIComponent(genre)}`);
    const animes = await res.json();
    renderAnimeGrid(animes);
  } catch {}
}

function filterByGenre(genre) {
  currentFilter = genre;
  if (genre) {
    fetch(`/api/animes?genre=${encodeURIComponent(genre)}`)
      .then(r => r.json())
      .then(renderAnimeGrid);
    document.querySelector('.section#animes').scrollIntoView({ behavior: 'smooth' });
  }
}

function filterByGenreClick(genre) {
  document.getElementById('genreFilter').value = genre;
  filterByGenre(genre);
  document.getElementById('animes').scrollIntoView({ behavior: 'smooth' });
}

function renderAnimeGrid(animes) {
  const g = document.getElementById('animeGrid');
  if (!g) return;
  g.innerHTML = animes.map(a => `
    <div class="card-a" onclick="openAnime(${a.id})">
      <div class="c-poster">
        ${a.cover_image ? `<img src="${a.cover_image}" alt="${a.title}">` : a.icon}
        <div class="c-play"><div class="c-play-btn"></div></div>
        ${a.status === 'Davom etmoqda' ? '<span class="c-badge new">YANGI</span>' : ''}
        <span class="c-badge ep" style="top:auto;bottom:8px;left:8px">${a.season_count || 0} fasl</span>
        <span class="c-score">⭐ ${a.score}</span>
      </div>
      <div class="c-body">
        <div class="c-title">${a.title}</div>
        <div class="c-meta"><span>${a.year}</span><span style="color:var(--text3)">•</span><span>${(a.genres || [])[0] || ''}</span></div>
        <span class="c-genre">${(a.genres || []).slice(0, 2).join(' • ')}</span>
      </div>
    </div>
  `).join('');
}

// ========== SEARCH ==========
let searchTimer;
function handleSearch(val) {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    if (val.length > 1) doSearchWith(val);
    else if (val.length === 0) { /* refresh */ }
  }, 300);
}

function doSearch() {
  const val = document.getElementById('heroSearch')?.value || document.getElementById('navSearch')?.value;
  if (val?.trim()) doSearchWith(val.trim());
}

async function doSearchWith(query) {
  try {
    const res = await fetch(`/api/animes?search=${encodeURIComponent(query)}`);
    const results = await res.json();
    document.getElementById('searchResultTitle').innerHTML =
      `"${query}" bo'yicha natijalar — ${results.length} ta topildi`;
    const g = document.getElementById('searchGrid');
    g.innerHTML = results.length
      ? results.map(a => `
          <div class="card-a" onclick="openAnime(${a.id})">
            <div class="c-poster">
              ${a.cover_image ? `<img src="${a.cover_image}" alt="${a.title}">` : a.icon}
              <div class="c-play"><div class="c-play-btn"></div></div>
              <span class="c-score">⭐ ${a.score}</span>
            </div>
            <div class="c-body">
              <div class="c-title">${a.title}</div>
              <div class="c-meta"><span>${a.year}</span><span style="color:var(--text3)">•</span><span>${(a.genres || [])[0] || ''}</span></div>
              <span class="c-genre">${(a.genres || []).slice(0, 2).join(' • ')}</span>
            </div>
          </div>
        `).join('')
      : `<div style="grid-column:1/-1;text-align:center;padding:3rem;color:var(--text3)">
           <div style="font-size:3rem;margin-bottom:1rem">🔍</div>
           <p>Hech narsa topilmadi.</p>
         </div>`;
    showPage('search');
  } catch {}
}

// ========== NAVIGATION ==========
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  window.scrollTo(0, 0);
}

function toggleSeason(idx) {
  const list = document.getElementById('slist-' + idx);
  const toggle = document.getElementById('stoggle-' + idx);
  list.classList.toggle('open');
  toggle.classList.toggle('open');
}

function detailTab(btn, tab) {
  document.querySelectorAll('.detail-tab').forEach(t => t.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById('detail-episodes').style.display = tab === 'episodes' ? 'block' : 'none';
  document.getElementById('detail-info').style.display = tab === 'info' ? 'block' : 'none';
}

// ========== MODALS ==========
function openModal(name) { document.getElementById('modal-' + name).classList.add('open'); }
function closeModal(name) { document.getElementById('modal-' + name).classList.remove('open'); }
function closeModalIfOutside(e, name) {
  if (e.target === document.getElementById('modal-' + name)) closeModal(name);
}
function switchAuthTab(btn, tab) {
  document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('on'));
  btn.classList.add('on');
  document.getElementById('auth-login').style.display = tab === 'login' ? 'block' : 'none';
  document.getElementById('auth-register').style.display = tab === 'register' ? 'block' : 'none';
}

// ========== VIDEO MODAL ==========
function closeVideoModal() {
  document.getElementById('modal-video').classList.remove('open');
  document.getElementById('videoFrame').innerHTML = '';
}
function closeVideoIfOutside(e) {
  if (e.target === document.getElementById('modal-video')) closeVideoModal();
}
