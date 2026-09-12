const app = document.querySelector('#app');
const params = new URLSearchParams(location.search);
const state = { view: params.get('view') === 'available' ? 'available' : 'chosen', chosen: [], available: [], loading: true, error: params.get('error') };
const api = async path => { const response = await fetch(path); const data = await response.json().catch(() => ({})); if (!response.ok) throw new Error(data.error || 'Request failed (' + response.status + ')'); return data; };
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
const initials = name => String(name || '?').split(/\s+/).filter(Boolean).slice(0, 2).map(x => x[0]).join('').toUpperCase();
const header = (eyebrow, title, subtitle) => '<header class="topbar"><div><p class="eyebrow">' + eyebrow + '</p><h1>' + title + '</h1><p class="subtitle">' + subtitle + '</p></div><a class="refresh" href="/?view=' + state.view + '">↻ Refresh</a></header>';
function render() {
  document.querySelector('#chosen-count').textContent = state.chosen.length || '—'; document.querySelector('#available-count').textContent = state.available.length || '—';
  document.querySelectorAll('.nav').forEach(link => link.classList.toggle('active', new URL(link.href).searchParams.get('view') === state.view));
  if (state.loading) { app.innerHTML = '<div class="loading">Loading candidates…</div>'; return; }
  if (state.error) { app.innerHTML = header('HR WORKSPACE', 'Connection issue', 'Ambiguous data could not be loaded or updated.') + '<section class="message-card"><strong>' + esc(state.error) + '</strong><a class="primary" href="/?view=' + state.view + '">Try again</a></section>'; return; }
  state.view === 'available' ? renderAvailable() : renderChosen();
}
function renderChosen() {
  const closed = state.chosen.filter(x => x.state === 'rejected' || x.state === 'fired').length;
  app.innerHTML = header('CHOSEN CANDIDATES', 'HR decision desk', 'Review selected candidates and update their current employment state.') + '<section class="summary"><div><strong>' + state.chosen.length + '</strong><span>chosen candidates</span></div><div><strong>' + state.chosen.filter(x => x.state === 'offer').length + '</strong><span>offers</span></div><div><strong>' + state.chosen.filter(x => x.state === 'hired').length + '</strong><span>hired</span></div><div><strong>' + closed + '</strong><span>closed</span></div></section><section class="cards">' + (state.chosen.length ? state.chosen.map(candidateCard).join('') : empty('No chosen candidates', 'Candidates selected by the search workflow will appear here.')) + '</section>';
}
function renderAvailable() {
  app.innerHTML = header('AVAILABLE CANDIDATES', 'Candidate pool', 'Candidates not yet reflected in the chosen sheet.') + '<div class="toolbar"><input id="search" placeholder="Search by name, role, or skill…"><span>' + state.available.length + ' available</span></div><section class="cards" id="available-list">' + (state.available.length ? state.available.map(candidateCard).join('') : empty('No available candidates', 'All Candidate Pool entries are already chosen.')) + '</section>';
  document.querySelector('#search').addEventListener('input', event => { const query = event.target.value.toLowerCase(); document.querySelector('#available-list').innerHTML = state.available.filter(x => (x.name + ' ' + x.role + ' ' + x.skills).toLowerCase().includes(query)).map(candidateCard).join('') || empty('No matches', 'Try another search.'); });
}
function candidateCard(candidate) {
  const id = encodeURIComponent(candidate.candidate_id);
  const form = (next, label, extra) => '<form method="post" action="/api/chosen/' + id + '/state">' + (extra || '') + '<input type="hidden" name="state" value="' + next + '"><button class="action ' + next + '" type="submit">' + label + '</button></form>';
  const actions = state.view === 'chosen' ? '<div class="actions"><form method="post" action="/api/chosen/' + id + '/state"><input type="hidden" name="state" value="offer"><input class="offer-input" name="offer_amount" inputmode="decimal" pattern="^\\d+(?:[.,]\\d{1,2})?$" placeholder="EUR amount" value="' + esc(candidate.offer_amount) + '" aria-label="Offer amount"><button class="action offer" type="submit">Send offer</button></form>' + form('hired', 'Hire') + form('rejected', 'Reject') + (candidate.state === 'hired' ? form('fired', 'Fire') : '') + '</div>' : '';
  return '<article class="candidate-card"><div class="candidate-main"><span class="avatar">' + initials(candidate.name) + '</span><div><h2>' + esc(candidate.name || 'Unnamed candidate') + '</h2><p>' + esc(candidate.role || 'Role unknown') + ' · ' + esc(candidate.level || 'Level unknown') + '</p></div><span class="state ' + esc(candidate.state || 'unassigned') + '">' + esc(candidate.state || 'no state') + '</span></div><div class="details"><div><small>SKILLS</small><p>' + esc(candidate.skills || 'Unknown') + '</p></div><div><small>YEARS</small><p>' + esc(candidate.years || 'Unknown') + '</p></div><div><small>OFFER AMOUNT</small><p>' + (candidate.offer_amount ? '€ ' + esc(candidate.offer_amount) : '—') + '</p></div></div>' + actions + '</article>';
}
function empty(title, copy) { return '<div class="empty"><strong>' + title + '</strong><p>' + copy + '</p></div>'; }
async function load() { state.loading = true; state.error = null; render(); try { [state.chosen, state.available] = await Promise.all([api('/api/chosen'), api('/api/candidates')]); } catch (error) { state.error = error.message; } state.loading = false; render(); }
load();
