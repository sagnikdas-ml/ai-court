const candidates = [
  { name: 'Mira Patel', initials: 'MP', detail: 'MSc Computer Science · CV lab project', match: '96% match' },
  { name: 'Leon Fischer', initials: 'LF', detail: 'MSc Data Science · PyTorch, MLOps', match: '92% match' },
  { name: 'Sofia Romano', initials: 'SR', detail: 'MSc Robotics · image segmentation', match: '90% match' },
  { name: 'David Chen', initials: 'DC', detail: 'MSc AI · evaluation tooling', match: '88% match' },
  { name: 'Nora Williams', initials: 'NW', detail: 'MSc Informatics · visual learning', match: '86% match' }
];

let selectedCandidate = null;
const list = document.querySelector('#candidate-list');
const modal = document.querySelector('#hr-modal');
const status = document.querySelector('#request-status');
const description = document.querySelector('#request-description');

function renderCandidates() {
  list.innerHTML = candidates.map((candidate, index) => `
    <button class="candidate ${selectedCandidate?.name === candidate.name ? 'selected' : ''}" data-index="${index}">
      <span class="candidate-avatar">${candidate.initials}</span>
      <span class="candidate-info"><strong>${candidate.name}</strong><span>${candidate.detail}</span></span>
      <span class="match">${candidate.match}</span>
      <span class="select-label">SELECT</span>
    </button>`).join('');
  list.querySelectorAll('.candidate').forEach(button => button.addEventListener('click', () => openReview(candidates[button.dataset.index])));
}

function openReview(candidate) {
  selectedCandidate = candidate;
  renderCandidates();
  document.querySelector('#modal-copy').textContent = `Arjun Shah requests approval to hire ${candidate.name} as a student assistant for the vision benchmark evaluation pipeline.`;
  document.querySelector('#review-card').innerHTML = `<strong>${candidate.name}</strong><br><span>${candidate.detail}</span><br><br><span>8 h/week · Starting October 2026 · Lab operating funds</span>`;
  modal.hidden = false;
}

function addMessage(kind, html) {
  const chat = document.querySelector('#chat');
  const article = document.createElement('article');
  article.className = `message ${kind === 'you' ? 'own-message' : 'agent-message'}`;
  const avatar = kind === 'you' ? '<span class="avatar avatar-small">AS</span>' : '<span class="avatar agent">✦</span>';
  const body = `<div class="message-content"><div class="message-meta"><strong>${kind === 'you' ? 'You' : 'Objection agent'}</strong>${kind === 'agent' ? '<span class="agent-pill">ASSISTANT</span>' : ''}<time>now</time></div><div class="bubble">${html}</div></div>`;
  article.innerHTML = kind === 'you' ? body + avatar : avatar + body;
  chat.append(article); chat.scrollTop = chat.scrollHeight;
}

document.querySelector('#approve-request').addEventListener('click', () => {
  modal.hidden = true;
  status.textContent = 'Approved by HR'; description.textContent = `${selectedCandidate.name} has been cleared to hire.`;
  document.querySelector('.status-dot').style.background = '#2e9a70';
  addMessage('agent', `HR approved the request for <strong>${selectedCandidate.name}</strong>. I’ve notified them and added the next onboarding steps to your task list.`);
});
document.querySelector('#reject-request').addEventListener('click', () => {
  modal.hidden = true;
  status.textContent = 'Needs a new decision'; description.textContent = 'HR declined this request; a reason will be shared in chat.';
  document.querySelector('.status-dot').style.background = '#ce775c';
  addMessage('agent', `HR declined the request for <strong>${selectedCandidate.name}</strong>, citing an availability conflict. Would you like me to refine the search, or would you prefer another candidate from this shortlist?`);
});
document.querySelector('#close-modal').addEventListener('click', () => modal.hidden = true);
modal.addEventListener('click', event => { if (event.target === modal) modal.hidden = true; });
document.querySelector('#composer').addEventListener('submit', event => {
  event.preventDefault(); const input = document.querySelector('#message-input'); const value = input.value.trim(); if (!value) return;
  addMessage('you', value); input.value = '';
  setTimeout(() => addMessage('agent', 'I’m on it. I can search candidates, clarify the role brief, or follow up on the hiring request.'), 450);
});
renderCandidates();
