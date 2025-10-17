(function(){
  // Minimal dev context panel for right panel tabs (web)
  const state = { dev: false, ctx: null };

  async function fetchDevFlag() {
    try {
      const res = await fetch('/api/config/dev');
      const j = await res.json();
      state.dev = !!(j && j.dev_mode);
    } catch(e) { state.dev = false; }
    return state.dev;
  }

  function ensureTab() {
    // Inject minimal CSS for readability
    try {
      const style = document.createElement('style');
      style.innerHTML = `
        #tab-context .settings-section { color:#eee; }
        #tab-context label { color:#eee; }
        #tab-context pre { color:#eee; background:#222; border:1px solid #444; }
        #tab-context input[type=text], #tab-context select { background:#2e2e2e; color:#eee; border:1px solid #555; padding:4px; }
      `;
      document.head.appendChild(style);
    } catch(e) { console.warn('context-panel css inject failed', e); }
    const tabsBar = document.querySelector('.right-tabs .tab-buttons');
    const content = document.querySelector('.right-tabs .tab-content');
    if (!tabsBar || !content) return false;

    // If already added, skip
    if (document.getElementById('btn-tab-context')) return true;

    // Add tab button
    const btn = document.createElement('button');
    btn.className = 'rp-tab-btn';
    btn.id = 'btn-tab-context';
    btn.setAttribute('data-tab', 'tab-context');
    btn.textContent = 'Context';
    tabsBar.appendChild(btn);

    // Add pane
    const pane = document.createElement('div');
    pane.className = 'rp-tab-pane';
    pane.id = 'tab-context';
    pane.innerHTML = `
      <div class="settings-section">
        <h3>Game Context (Dev)</h3>
        <pre id="dev-ctx-json" style="white-space:pre-wrap;background:#222;padding:8px;border:1px solid #444;border-radius:4px;max-height:180px;overflow:auto;">{}</pre>
        <div class="form-group"><label>Location Name</label><input id="dev-ctx-loc-name" type="text"></div>
        <div class="form-group"><label>Location Major</label><select id="dev-ctx-loc-major"></select></div>
        <div class="form-group"><label>Venue</label><select id="dev-ctx-venue"></select></div>
        <div class="form-group"><label>Weather</label><select id="dev-ctx-weather"></select></div>
        <div class="form-group"><label>Time of Day</label><select id="dev-ctx-tod"></select></div>
        <div class="form-group"><label>Biome</label><select id="dev-ctx-biome"></select></div>
        <div class="form-group"><label>Interior</label><input id="dev-ctx-interior" type="checkbox"></div>
        <div class="form-group"><label>Underground</label><input id="dev-ctx-underground" type="checkbox"></div>
        <div class="form-group"><label>Crowd</label><select id="dev-ctx-crowd"></select></div>
        <div class="form-group"><label>Danger</label><select id="dev-ctx-danger"></select></div>
        <div style="display:flex;gap:8px;margin-top:8px;">
          <button id="dev-ctx-refresh" class="secondary-btn">Refresh</button>
          <button id="dev-ctx-apply" class="primary-btn">Apply</button>
        </div>
      </div>`;
    content.appendChild(pane);

    // Bind tab switching for this button
    btn.addEventListener('click', () => {
      document.querySelectorAll('.right-tabs .rp-tab-btn').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.right-tabs .rp-tab-pane').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
      pane.classList.add('active');
    });

    // Bind actions
    document.getElementById('dev-ctx-refresh').addEventListener('click', refreshFromServer);
    document.getElementById('dev-ctx-apply').addEventListener('click', applyToServer);

    // Fetch enums to populate selects (from static JSON)
    try {
      fetch('/sound/../config/audio/context_enums.json') // path trick: served root static only for /sound, but server mounts /sound only; fallback to inline list
        .then(r=>r.json()).then(populateEnums).catch(()=>populateEnums(null));
    } catch { populateEnums(null); }
    return true;
  }

  function populateEnums(data) {
    const fallback = {
      location: { major:["city","forest","camp","village","castle","dungeon","seaside","desert","mountain","swamp","ruins","port","temple"], venue:["tavern","market","blacksmith","inn","chapel","library","manor","arena","fireplace","bridge","tower","cave","farm"]},
      weather: { type:["clear","overcast","rain","storm","snow","blizzard","fog","windy","sandstorm"] },
      time_of_day: ["deep_night","pre_dawn","dawn","morning","noon","afternoon","evening","sunset","night"],
      biome:["forest","desert","swamp","mountain","seaside","plains","ruins"],
      crowd_level:["empty","sparse","busy"],
      danger_level:["calm","tense","deadly"]
    };
    const enums = data || fallback;
    const fill = (id, arr) => {
      const el = document.getElementById(id); if (!el) return; el.innerHTML='';
      const list = (arr||[]).map(v=>({value:String(v),label:String(v)}));
      list.forEach(o=>{ const opt=document.createElement('option'); opt.value=o.value; opt.textContent=o.label; el.appendChild(opt); });
    };
    fill('dev-ctx-loc-major', enums.location?.major);
    fill('dev-ctx-venue', enums.location?.venue);
    fill('dev-ctx-weather', enums.weather?.type);
    fill('dev-ctx-tod', enums.time_of_day);
    fill('dev-ctx-biome', enums.biome);
    fill('dev-ctx-crowd', enums.crowd_level);
    fill('dev-ctx-danger', enums.danger_level);
  }

  async function refreshFromServer(){
    console.log('[ContextPanel] Refresh clicked');
    try {
      if (!window.apiClient || !apiClient.sessionId) return;
      const res = await fetch(`/api/context/${apiClient.sessionId}`);
      const j = await res.json();
      const ctx = (j && j.context) || {};
      state.ctx = ctx;
      renderCtx(ctx);
      prefillForm(ctx);
    } catch(e) { console.warn('refreshFromServer failed', e); }
  }

  function renderCtx(ctx){
    try { document.getElementById('dev-ctx-json').textContent = JSON.stringify(ctx||{}, null, 2); } catch{}
  }

  function prefillForm(ctx){
    if (!ctx) return;
    try { document.getElementById('dev-ctx-loc-name').value = ctx.location?.name || ''; } catch{}
    const setVal=(id,val)=>{ try{ const el=document.getElementById(id); if (el && val){ el.value=val; } }catch{} };
    setVal('dev-ctx-loc-major', ctx.location?.major);
    setVal('dev-ctx-venue', ctx.location?.venue);
    setVal('dev-ctx-weather', ctx.weather?.type);
    setVal('dev-ctx-tod', ctx.time_of_day);
    setVal('dev-ctx-biome', ctx.biome);
    try { document.getElementById('dev-ctx-interior').checked = !!ctx.interior; } catch{}
    try { document.getElementById('dev-ctx-underground').checked = !!ctx.underground; } catch{}
    setVal('dev-ctx-crowd', ctx.crowd_level);
    setVal('dev-ctx-danger', ctx.danger_level);
  }

  async function applyToServer(){
    console.log('[ContextPanel] Apply clicked');
    if (!window.apiClient || !apiClient.sessionId) return;
    const payload = {
      location: {
        name: document.getElementById('dev-ctx-loc-name').value || '',
        major: document.getElementById('dev-ctx-loc-major').value || null,
        venue: document.getElementById('dev-ctx-venue').value || null,
      },
      weather: { type: document.getElementById('dev-ctx-weather').value || null },
      time_of_day: document.getElementById('dev-ctx-tod').value || null,
      biome: document.getElementById('dev-ctx-biome').value || null,
      interior: document.getElementById('dev-ctx-interior').checked,
      underground: document.getElementById('dev-ctx-underground').checked,
      crowd_level: document.getElementById('dev-ctx-crowd').value || null,
      danger_level: document.getElementById('dev-ctx-danger').value || null,
    };
    try {
      const res = await fetch(`/api/context/${apiClient.sessionId}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      if (res.ok) {
        // Refresh display
        await refreshFromServer();
      }
    } catch(e) { console.warn('applyToServer failed', e); }
  }

  async function init(){
    const dev = await fetchDevFlag();
    if (!dev) return; // Do not show in production
    if (!ensureTab()) return;
    // Initial fetch shortly after session creation
    document.addEventListener('session-created', ()=> setTimeout(refreshFromServer, 300));
  }

  // Expose minimal API for WS updates
  window.ContextPanel = {
    onContextUpdate: function(data){
      const ctx = data && data.data ? data.data : data;
      state.ctx = ctx; renderCtx(ctx); prefillForm(ctx);
    }
  };

  // Start
  document.addEventListener('DOMContentLoaded', init);
})();