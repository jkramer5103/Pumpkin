const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const when = value => value ? new Date(typeof value === 'number' ? value*1000 : value).toLocaleString([], {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : 'Not reported';
const timeLeft = value => {const n=Math.max(0,Math.ceil(value-Date.now()/1000));return `${Math.floor(n/3600)}h ${Math.floor(n%3600/60)}m`;};
const states={working:'Working',waiting_for_reset:'Waiting for reset',retrying:'Retrying',needs_attention:'Needs attention',complete:'Complete',queued:'Queued',starting:'Starting'};
let state=null;

function quota(title, window) {
  const left=typeof window?.used_percent==='number'?Math.max(0,100-window.used_percent):null;
  return `<div class="quota"><div class="quota-title"><span>${title}</span><b>${left===null?'—':left+'% left'}</b></div><div class="bar"><i data-width="${left??0}"></i></div><div class="reset">Reset ${when(window?.reset_at)}</div></div>`;
}

function workers() {
  $('workers').innerHTML=state.accounts.map(a=>{
    const q=a.quota||{}, status=a.status||'starting';
    const note=status==='waiting_for_reset'?`Resumes in <b>${timeLeft(a.retry_at||Date.now()/1000)}</b>`:`${a.completed_tasks||0} tasks completed`;
    return `<article class="worker"><div class="worker-head"><div class="avatar ${esc(a.id)}">${esc(a.label[0])}</div><div><div class="worker-name">${esc(a.label)}</div><div class="worker-role">Codex Plus · GPT-6.1-Sol</div></div><span class="state ${esc(status)}">${states[status]||esc(status)}</span></div><div class="task" title="${esc(a.task_title)}">${esc(a.task_title||'Preparing the next task')}</div><div class="quota-row">${quota('5-HOUR WINDOW',q.five_hour)}${quota('WEEKLY WINDOW',q.weekly)}</div><div class="worker-foot"><span>${note}</span><span>${q.error?'Quota check unavailable':`<b>${q.banked_count??'—'}</b> banked · untouched`}</span></div></article>`;
  }).join('');
  document.querySelectorAll('[data-width]').forEach(el=>el.style.width=el.dataset.width+'%');
}

function patches() {
  const ledger=state.patch_ledger||{}, items=ledger.patches||[];
  const pushed=items.filter(p=>p.pushed).length;
  $('patch-count').textContent=items.length;
  $('patch-total').textContent=items.length?`${pushed} pushed · ${items.length-pushed} local`:'No source fixes pushed yet';
  $('patch-list').innerHTML=items.length?items.map(p=>`<article class="patch-card"><div class="patch-heading"><div class="patch-symbol">↳</div><div><h3>${esc(p.title)}</h3><div class="patch-meta">${esc(p.account)} · ${when(p.timestamp)}</div></div><span class="pill ${p.pushed?'':'local'}">${p.pushed?'Pushed':'Local commit'}</span></div><p>${esc(p.summary)}</p><div class="patch-validation"><span class="validation-dot ${p.validated?'passed':''}"></span><span>${esc(p.validation)}</span></div><div class="patch-bottom"><span>${p.files.length} source ${p.files.length===1?'file':'files'}</span>${p.url?`<a href="${esc(p.url)}" target="_blank" rel="noopener">View commit ${esc(p.commit.slice(0,7))} ↗</a>`:`<span>${esc(p.commit.slice(0,7))} · awaiting push</span>`}</div></article>`).join(''):`<div class="empty patch-empty"><div class="empty-icon">↳</div><b>The agents are working on their first fixes.</b><p>Source patches appear here once committed, with a short explanation and actual validation. Findings and failed probes are not counted as fixes.</p></div>`;
  const pub=state.published||{};
  $('lab-summary').innerHTML=`<div><span class="eyebrow">THE LAB ITSELF</span><p>Comparison engine, ${state.scenario_count} scenarios, two subscription workers, and automatic quota recovery.</p></div>${pub.head?`<a href="https://github.com/jkramer5103/Pumpkin/tree/parity-lab/tools/parity-lab" target="_blank" rel="noopener">Lab source ↗</a>`:'<span class="subtle">Initial publication pending</span>'}`;
}

async function poll() {
  try {
    const response=await fetch('/api/status');if(!response.ok)throw Error(response.status);
    state=await response.json();workers();patches();
    $('connection-label').textContent='Live';$('connection-dot').classList.add('green');$('offline').hidden=true;
    $('last-update').textContent='Updated '+new Date(state.updated_at).toLocaleTimeString();
  } catch {
    $('connection-label').textContent='Reconnecting';$('connection-dot').classList.remove('green');$('offline').hidden=false;
  } finally {setTimeout(poll,5000);}
}
setInterval(()=>{if(state?.accounts.some(a=>a.status==='waiting_for_reset'))workers();},1000);
poll();
