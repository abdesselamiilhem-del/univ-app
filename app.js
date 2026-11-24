// ===== Noms des pages : doivent être IDENTIQUES aux noms de vos fichiers =====
const PAGES = {
  home: 'index.html',
  deps: 'Departments.html',
  news: 'announce.html',
  login: 'Login.html',
  admin: 'Admin.html'
};

// ===== Appel à l'API Flask =====
async function api(path, method = 'GET', body) {
  const r = await fetch('/api' + path, {method, headers: {'Content-Type': 'application/json'}, body: body ? JSON.stringify(body) : undefined});
  if (r.status === 401 && path !== '/login') { location.href = PAGES.login; return null; }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || 'Error ' + r.status);
  return r.status === 204 ? null : await r.json();
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
