const $ = id => document.getElementById(id);
const escapeHTML = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let state = null, scenarios = [], runs = [], activityAccount = 'all', currentTab = 'overview';
let currentResults = [], selectedResults = [], evidenceResults = [];
const when = stamp => stamp ? new Date(typeof stamp === 'number' ? stamp * 1000 : stamp).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : 'Not reported';
const left = window => window && typeof window.used_percent === 'number' ? Math.max(0, 100-window.used_percent) : null;
const remaining = stamp => {const n = Math.max(0, Math.ceil(stamp-Date.now()/1000)); return `${Math.floor(n/3600)}h ${Math.floor(n%3600/60)}m`;};
const labels = {working:'Working',waiting_for_reset:'Waiting for reset',retrying:'Retrying',needs_attention:'Needs attention',complete:'Complete',queued:'Queued',starting:'Starting'};

function quotaHTML(title, window) {
  const value = left(window);
  return `<div class="quota"><div class="quota-title"><span>${title}</span><b>${value === null ? '—' : value+'% left'}</b></div><div class="bar"><i data-width="${value ?? 0}"></i></div><div class="reset">Reset ${when(window?.reset_at)}</div></div>`;
}

function renderWorkers() {
  $('workers').innerHTML = state.accounts.map(account => {
    const q = account.quota || {}, status = account.status || 'starting';
    const title = (account.task_title || 'Preparing workspace').replace(/^#+\s*/, '');
    const resume = status === 'waiting_for_reset' ? `Resumes in <b>${remaining(account.retry_at || Date.now()/1000)}</b>` : `${account.completed_tasks || 0} / ${account.total_tasks || '—'} tasks completed`;
    return `<article class="worker"><div class="worker-head"><div class="avatar ${account.id}">${account.label[0]}</div><div><div class="worker-name">${account.label}</div><div class="worker-role">${account.id === 'christine' ? 'Comparison engine & validation' : 'Servers & scenario coverage'}</div></div><span class="state ${escapeHTML(status)}">${labels[status] || escapeHTML(status)}</span></div><div class="task" title="${escapeHTML(title)}">${escapeHTML(title)}</div><div class="quota-row">${quotaHTML('5-HOUR WINDOW', q.five_hour)}${quotaHTML('WEEKLY WINDOW', q.weekly)}</div><div class="worker-foot"><span>${resume}</span><span>${q.error ? 'Quota check unavailable' : `<b>${q.banked_count ?? '—'}</b> banked · untouched`}</span></div></article>`;
  }).join('');
  document.querySelectorAll('[data-width]').forEach(bar => {bar.style.width = bar.dataset.width+'%';});
}

function renderActivity() {
  if (!state) return;
  const streams = state.accounts.filter(a => activityAccount === 'all' || a.id === activityAccount).map(a => ({account:a,events:a.activity?.events || []}));
  const events = [];
  const length = Math.max(0, ...streams.map(s=>s.events.length));
  for(let i=length-1;i>=0;i--) for(const stream of streams) {
    const event = stream.events[stream.events.length-1-(length-1-i)];
    if(event) events.push({...event,account:stream.account});
  }
  $('activity').innerHTML = events.length ? events.slice(0,20).map(e=>`<article class="event ${e.kind}"><span class="event-icon">${e.kind === 'command' ? '›_' : '✧'}</span><div><h3>${escapeHTML(e.account.label)} <span>· ${e.kind === 'command' ? 'Running command' : 'Progress update'}</span></h3><p>${escapeHTML(e.text)}</p></div></article>`).join('') : '<div class="empty">Workers are preparing their first tasks.</div>';
}

function resultsTable(results, namespace) {
  if (!results?.length) return '<div class="empty">No comparison results yet.</div>';
  return `<table><thead><tr><th>SCENARIO</th><th>CATEGORY</th><th>RESULT</th><th></th></tr></thead><tbody>${results.map((r,i)=>`<tr><td>${escapeHTML(r.title || r.id)}<small>${escapeHTML(r.id)}</small></td><td>${escapeHTML(r.category || '—')}</td><td><span class="pill ${escapeHTML(r.status)}">${escapeHTML(r.status)}</span></td><td><button class="evidence-button" data-evidence="${namespace}:${i}">Inspect ↗</button></td></tr>`).join('')}</tbody></table>`;
}

function renderStatus() {
  $('stat-scenarios').textContent = state.scenario_count;
  $('nav-count').textContent = state.scenario_count;
  const summary = state.latest?.summary;
  $('stat-passing').textContent = summary?.passed ?? '—';
  $('stat-different').textContent = summary?.different ?? '—';
  $('stat-errors').textContent = summary?.error ?? '—';
  $('disk').textContent = `${state.disk_free_gb} GB`;
  renderWorkers(); renderActivity();
  const names = {'pumpkin-parity-vanilla.service':['Vanilla','Reference server · 127.0.0.1:25575'],'pumpkin-parity-pumpkin.service':['Pumpkin','Candidate server · 127.0.0.1:25576'],'pumpkin-parity-supervisor.service':['Campaign supervisor','Persistent queue · automatic resume']};
  $('services').innerHTML = state.services.map(s=>`<div class="service"><div><b>${escapeHTML((names[s.Id]||[s.Id])[0])}</b><small>${escapeHTML((names[s.Id]||['',''])[1])}</small></div><span class="service-state ${s.ActiveState==='active'?'':'off'}"><span class="dot ${s.ActiveState==='active'?'green':''}"></span>${escapeHTML(s.ActiveState || 'Not started')}</span></div>`).join('');
  currentResults = state.latest?.results || [];
  $('latest-results').innerHTML = resultsTable(currentResults.slice(0,12),'latest');
  const publication = state.published || {};
  const forkRows = [{name:'Lab source',branch:'parity-lab',...publication},...state.accounts.map(a=>({name:a.label,...a.fork}))];
  $('fork-activity').innerHTML = forkRows.map(f=>`<div class="service"><div><b>${escapeHTML(f.name)}</b><small>${escapeHTML(f.branch || 'Awaiting first patch')} ${f.pushed_at ? '· '+when(f.pushed_at) : ''}</small></div>${f.head && f.pushed_at ? `<a class="evidence-button" href="https://github.com/jkramer5103/Pumpkin/commit/${encodeURIComponent(f.head)}" target="_blank" rel="noopener">${escapeHTML(f.head.slice(0,7))} ↗</a>` : '<span class="subtle">Working locally</span>'}</div>`).join('');
  $('last-update').textContent = `Updated ${new Date(state.updated_at).toLocaleTimeString()}`;
}

function renderScenarios() {
  const query = $('scenario-search').value.toLowerCase();
  const rows = scenarios.filter(s=>[s.id,s.title,s.category,s.description,...(s.tags||[])].join(' ').toLowerCase().includes(query));
  $('scenario-list').innerHTML = rows.length ? rows.map(s=>`<article class="scenario"><span class="label">${escapeHTML(s.category || 'Uncategorized')}</span><h3>${escapeHTML(s.title || s.id)}</h3><p>${escapeHTML(s.description || s.error || 'Description not yet provided.')}</p><small>${s.steps || 0} steps · ${escapeHTML(s.id)}</small></article>`).join('') : '<div class="empty">No matching scenarios. New cases appear as workers write them.</div>';
}

function renderRuns() {
  $('run-list').innerHTML = runs.length ? `<table><thead><tr><th>STARTED</th><th>PASS</th><th>DIFFERENT</th><th>ERROR</th><th></th></tr></thead><tbody>${runs.map(r=>`<tr><td>${when(r.started_at)}<small>${escapeHTML(r.run_id || r.directory)}</small></td><td>${r.summary?.passed ?? '—'}</td><td class="orange">${r.summary?.different ?? '—'}</td><td>${r.summary?.error ?? '—'}</td><td><button class="evidence-button" data-run="${escapeHTML(r.directory)}">Open run ↗</button></td></tr>`).join('')}</tbody></table>` : '<div class="empty">No completed comparisons yet. Provisioning and scenario construction are in progress.</div>';
}

function tab(name) {
  currentTab = name;
  document.querySelectorAll('.tab-panel').forEach(el=>el.hidden=el.id!==name);
  document.querySelectorAll('.nav').forEach(el=>el.classList.toggle('active',el.dataset.tab===name));
  const titles = {overview:['Overview','Same world. <span>Different engine.</span>','Two subscriptions. One question: does Pumpkin behave like vanilla?'],scenarios:['Scenarios','Every behavior. <span>A reproducible test.</span>','Deterministic command scenarios, with explicit positive observations.'],runs:['Test runs','Evidence first. <span>Every comparison saved.</span>','Inspect what both engines actually returned, including failures.']};
  $('page-label').textContent=titles[name][0]; $('page-title').innerHTML=titles[name][1]; $('page-description').textContent=titles[name][2];
}

async function poll() {
  try {
    const response = await fetch('/api/status'); if(!response.ok) throw Error(response.status);
    state = await response.json(); renderStatus();
    $('connection-label').textContent='Live'; $('connection-dot').classList.add('green'); $('offline').hidden=true;
    [scenarios,runs]=await Promise.all(['/api/scenarios','/api/runs'].map(async url=>{const r=await fetch(url);if(!r.ok)throw Error(r.status);return r.json();}));
    renderScenarios(); renderRuns();
  } catch(error) {
    $('connection-label').textContent='Reconnecting'; $('connection-dot').classList.remove('green'); $('offline').hidden=false;
  } finally {setTimeout(poll,5000);}
}

document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>tab(button.dataset.tab)));
$('view-runs').addEventListener('click',()=>tab('runs'));
$('scenario-search').addEventListener('input',renderScenarios);
$('activity-filter').addEventListener('click',event=>{const button=event.target.closest('[data-account]');if(!button)return;activityAccount=button.dataset.account;document.querySelectorAll('[data-account]').forEach(el=>el.classList.toggle('selected',el===button));renderActivity();});
document.addEventListener('click', async event=>{
  const runButton=event.target.closest('[data-run]');
  if(runButton){try{const response=await fetch('/api/runs/'+encodeURIComponent(runButton.dataset.run));if(!response.ok)throw Error(response.status);const run=await response.json();selectedResults=run.results||[];$('selected-run').hidden=false;$('selected-run-title').textContent='Run · '+when(run.started_at);$('selected-run-results').innerHTML=resultsTable(selectedResults,'selected');$('selected-run').scrollIntoView({behavior:'smooth'});}catch{$('run-list').insertAdjacentHTML('afterbegin','<div class="notice">Could not load this run. Please retry.</div>');}}
  const evidence=event.target.closest('[data-evidence]');
  if(evidence){const [namespace,index]=evidence.dataset.evidence.split(':');const r=(namespace==='latest'?currentResults:selectedResults)[Number(index)];if(!r)return;$('evidence-title').textContent=r.title||r.id;const raw=r.observations||{};$('evidence-body').innerHTML=`<p class="evidence-reason">${escapeHTML(r.reason || 'Observed responses matched and explicit expectations passed.')}</p><div class="evidence-grid">${['vanilla','pumpkin'].map(target=>`<section><h3>${target==='vanilla'?'Vanilla · reference':'Pumpkin · candidate'}</h3><pre>${escapeHTML(JSON.stringify(raw[target]??'No observations recorded',null,2))}</pre></section>`).join('')}</div>`;$('evidence-dialog').showModal();}
});
$('close-evidence').addEventListener('click',()=>$('evidence-dialog').close());
$('evidence-dialog').addEventListener('click',event=>{if(event.target===$('evidence-dialog'))$('evidence-dialog').close();});
setInterval(()=>{$('clock').textContent=new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'});if(state?.accounts.some(a=>a.status==='waiting_for_reset'))renderWorkers();},1000);
poll();
