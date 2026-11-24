// ===== Noms des pages : doivent être IDENTIQUES aux noms de vos fichiers =====
const PAGES = {
  home: 'index.html',
  deps: 'Departments.html',
  news: 'announce.html',
  login: 'Login.html',
  admin: 'Admin.html'
};

// ===== Données de démonstration (utilisées seulement si l'API /api n'existe pas) =====
const SAMPLE = {
  departments: [
    {id:1,name:'Computer Science',description:'Computer systems, Software Engineering, Artificial Intelligence.'},
    {id:2,name:'Mathematics',description:'Applied mathematics, statistics and mathematical modeling.'},
    {id:3,name:'Physics',description:'Mechanics, optics, energy, and applied physics.'},
    {id:4,name:'Chemistry',description:'The study of matter, its properties, and the changes it undergoes.'},
    {id:5,name:'Medicine',description:'The science and practice of diagnosing, treating, and preventing disease.'},
    {id:6,name:'Biology',description:'The study of living organisims and their interactions with the environment.'},
    {id:7,name:'Agronomy',description:'Which studies techniques and methods to improve agricultural production, protect plants and soil, and develop sustainable agriculture'}],
  announcements: [
    {id:1,category:'Registrations',created_at:'2026-11-12',title:'Registration for the 2026-2027 Academic Year Is Now Open',content:'Applications are open until January 15.'},
    {id:2,category:'Event',created_at:'2026-11-28',title:'Campus Open Day',content:'Guided tours and meetings with faculty members.'},
    {id:3,category:'Examinations',created_at:'2026-12-05',title:'Semester 1 Examination Schedule',content:'The schedule is available for all academic programs.'},
    {id:4,category:'Conference',created_at:'2026-12-15',title:'Artificial Intelligence Conference',content:'Amphitheater 100, open to students and visitors.'},
    {id:5,category:'Information',created_at:'2026-12-20',title:'Library Closure for Inventory',content:'Reopening scheduled for January 4.'}]
};

function demo(path, method, body) {
  const db = JSON.parse(sessionStorage.demoDB || 'null') || structuredClone(SAMPLE);
  if (path === '/login') {
    if (body.username === 'admin' && body.password === 'admin') { sessionStorage.demoAuth = '1'; return {ok:true}; }
    throw new Error('Invalid username or password.');
  }
  if (path === '/logout') { sessionStorage.removeItem('demoAuth'); return null; }
  if (path === '/departments') return db.departments;
  const m = path.match(/^\/announcements(?:\/(\d+))?$/);
  if (!m) throw new Error('Unknown route: ' + path);
  if (method === 'GET') return db.announcements.slice().sort((a, b) => b.created_at.localeCompare(a.created_at));
  if (!sessionStorage.demoAuth) { location.href = PAGES.login; return null; }
  const id = +m[1];
  if (method === 'POST') db.announcements.push({id: Date.now(), created_at: new Date().toISOString().slice(0, 10), ...body});
  if (method === 'PUT') Object.assign(db.announcements.find(a => a.id === id), body);
  if (method === 'DELETE') db.announcements = db.announcements.filter(a => a.id !== id);
  sessionStorage.demoDB = JSON.stringify(db);
  return null;
}

// ===== Appel à l'API Flask (repli sur la démo si l'API est absente) =====
// IMPORTANT : les routes sont en minuscules : /departments et /announcements
async function api(path, method = 'GET', body) {
  try {
    const r = await fetch('/api' + path, {method, headers: {'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined});
    if (r.status === 404) throw new Error('nf');
    if (r.status === 401 && path !== '/login') { location.href = PAGES.login; return null; }
    if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || 'Error ' + r.status);
    return r.status === 204 ? null : await r.json();
  } catch (e) {
    if (e instanceof TypeError || e.message === 'nf') return demo(path, method, body);
    throw e;
  }
}

// ===== Utilitaires =====
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = d => new Date(d).toLocaleDateString('en-GB', {day:'numeric', month:'short', year:'numeric'});
const $ = s => document.querySelector(s);
const annCard = a => `<article class="cd"><span class="tg">${esc(a.category)} · ${fmt(a.created_at)}</span><h3>${esc(a.title)}</h3><p>${esc(a.content)}</p></article>`;
const depCard = d => `<article class="cd"><h3>${esc(d.name)}</h3><p>${esc(d.description)}</p></article>`;
function say(text, ok) { const m = $('#msg'); if (m) { m.textContent = text; m.className = ok ? 'ok' : 'err'; } }

// ===== En-tête et pied de page communs =====
function layout() {
  const page = document.body.dataset.page;
  const links = [[PAGES.home,'home','Home'],[PAGES.deps,'deps','Departments'],[PAGES.news,'news','Announcements'],[PAGES.login,'login','Administration']];
  document.body.insertAdjacentHTML('afterbegin',
    `<header class="hd"><b>University M’hamed Bougara of Boumerdes</b><nav>${links.map(([h,p,t]) =>
      `<a href="${h}" ${p === page || (p === 'login' && page === 'admin') ? 'aria-current="page"' : ''}>${t}</a>`).join('')}</nav></header>`);
  document.body.insertAdjacentHTML('beforeend',
    '<footer class="ft">University M’hamed Bougara of Boumerdes (fictional institution) · contact@univ-boumerdes.dz</footer>');
}

// ===== Pages =====
const pages = {
  async home() {
    const [a, d] = await Promise.all([api('/announcements'), api('/departments')]);
    $('#latest').innerHTML = a.slice(0, 3).map(annCard).join('');
    $('#deps').innerHTML = d.slice(0, 3).map(depCard).join('');
  },
  async deps() {
    $('#deps').innerHTML = (await api('/departments')).map(depCard).join('');
  },
  async news() {
    $('#news').innerHTML = (await api('/announcements')).map(annCard).join('') || '<p>No announcements at the moment.</p>';
  },
  login() {
    $('#loginForm').addEventListener('submit', async e => {
      e.preventDefault();
      try {
        await api('/login', 'POST', {username: $('#u').value.trim(), password: $('#p').value});
        location.href = PAGES.admin;
      } catch (err) { say(err.message, false); }
    });
  },
  async admin() {
    const form = $('#annForm');
    const load = async () => {
      const list = await api('/announcements');
      if (!list) return;
      $('#rows').innerHTML = list.map(a => `<tr><td>${esc(a.title)}</td><td>${esc(a.category)}</td><td>${fmt(a.created_at)}</td>
        <td><button class="b2" data-edit="${a.id}">Edit</button> <button class="b3" data-del="${a.id}">Delete</button></td></tr>`).join('')
        || '<tr><td colspan="4">No announcements. Create the first one.</td></tr>';
      load.list = list;
    };
    const reset = () => { form.reset(); $('#id').value = ''; $('#formTitle').textContent = 'New announcement'; };
    $('#newBtn').onclick = () => { reset(); $('#title').focus(); };
    $('#logout').onclick = async () => { await api('/logout', 'POST'); location.href = PAGES.login; };
    $('#rows').addEventListener('click', async e => {
      const ed = e.target.dataset.edit, del = e.target.dataset.del;
      if (ed) {
        const a = load.list.find(x => x.id == ed);
        $('#id').value = a.id; $('#title').value = a.title; $('#category').value = a.category; $('#content').value = a.content;
        $('#formTitle').textContent = 'Edit announcement'; $('#title').focus();
      }
      if (del && confirm('Delete this announcement?')) {
        try { await api('/announcements/' + del, 'DELETE'); say('Announcement deleted.', true); reset(); load(); }
        catch (err) { say(err.message, false); }
      }
    });
    form.addEventListener('submit', async e => {
      e.preventDefault();
      const data = {title: $('#title').value.trim(), category: $('#category').value, content: $('#content').value.trim()};
      const id = $('#id').value;
      try {
        await api(id ? '/announcements/' + id : '/announcements', id ? 'PUT' : 'POST', data);
        say(id ? 'Announcement updated.' : 'Announcement added.', true); reset(); load();
      } catch (err) { say(err.message, false); }
    });
    load();
  }
};
document.addEventListener('DOMContentLoaded', () => { layout(); pages[document.body.dataset.page]?.(); });
