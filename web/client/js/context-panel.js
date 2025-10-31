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
        <div class="form-group"><label>Music Mood</label><select id="dev-ctx-mood"></select></div>
        <div class="form-group"><label>Interior</label><input id="dev-ctx-interior" type="checkbox"></div>
        <div class="form-group"><label>Underground</label><input id="dev-ctx-underground" type="checkbox"></div>
        <div class="form-group"><label>Crowd</label><select id="dev-ctx-crowd"></select></div>
        <div class="form-group"><label>Danger</label><select id="dev-ctx-danger"></select></div>
        <div style="display:flex;gap:8px;margin-top:8px;">
          <button id="dev-ctx-refresh" class="secondary-btn">Refresh</button>
          <button id="dev-ctx-apply" class="primary-btn">Apply</button>
        </div>
        <div style="margin-top:12px;">
          <h4 style="margin:0 0 6px 0;color:#eee;font-size:13px;">Now Playing (music + SFX)</h4>
          <ul id="dev-ctx-now-playing" style="list-style:none;padding:0;margin:0;max-height:110px;overflow-y:auto;background:#1e1e1e;border:1px solid #444;border-radius:4px;">
            <li style="padding:4px 8px;color:#888;font-size:12px;">No playback info</li>
          </ul>
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
    document.getElementById('dev-ctx-refresh').addEventListener('click', () => {
      try {
        if (window.webMusicManager) window.webMusicManager.playSfx('ui', 'click');
      } catch {}
      refreshFromServer();
    });
    document.getElementById('dev-ctx-apply').addEventListener('click', () => {
      try {
        if (window.webMusicManager) window.webMusicManager.playSfx('ui', 'click');
      } catch {}
      applyToServer();
    });

    // Fetch enums to populate selects (server endpoint; falls back to inline list)
    try {
      fetch('/api/context/enums')
        .then(r=> r.ok ? r.json() : Promise.reject(new Error('bad status')))
        .then(populateEnums)
        .catch(()=>populateEnums(null));
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
    const fill = (id, arr, withNone=false) => {
      const el = document.getElementById(id); if (!el) return; el.innerHTML='';
      const list = (arr||[]).map(v=>({value:String(v),label:String(v)}));
      if (withNone) list.unshift({value:'None',label:'None'});
      list.forEach(o=>{ const opt=document.createElement('option'); opt.value=o.value; opt.textContent=o.label; el.appendChild(opt); });
    };
    fill('dev-ctx-loc-major', enums.location?.major, true);
    fill('dev-ctx-venue', enums.location?.venue, true);
    fill('dev-ctx-weather', enums.weather?.type);
    fill('dev-ctx-tod', enums.time_of_day);
    fill('dev-ctx-biome', enums.biome, true);
    fill('dev-ctx-crowd', enums.crowd_level);
    fill('dev-ctx-danger', enums.danger_level);

    // Enforce dropdown rules: major None -> venue None/disabled; major set -> biome None; venue enabled
    try {
      const majorEl = document.getElementById('dev-ctx-loc-major');
      const venueEl = document.getElementById('dev-ctx-venue');
      const biomeEl = document.getElementById('dev-ctx-biome');
      const applyRules = () => {
        const maj = (majorEl.value||'').trim().toLowerCase();
        if (['none','no','n/a','null',''].includes(maj)){
          venueEl.value = 'None';
          venueEl.disabled = true;
          // Biome stands independently; do not force
        } else {
          venueEl.disabled = false;
          biomeEl.value = 'None';
        }
      };
      majorEl.addEventListener('change', applyRules);
      // Apply once after initial fill
      setTimeout(applyRules, 0);
    } catch(e) { console.warn('context rules binding failed', e); }

    // If we already have a context snapshot (from WS or refresh), prefill now
    try { if (state.ctx) prefillForm(state.ctx); } catch {}
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
      try { if (window.webMusicManager) window.webMusicManager.applyContext(ctx||{}); } catch {}
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
    
    // Apply venue enable/disable rules after prefilling
    try {
      const majorEl = document.getElementById('dev-ctx-loc-major');
      const venueEl = document.getElementById('dev-ctx-venue');
      const biomeEl = document.getElementById('dev-ctx-biome');
      if (majorEl && venueEl && biomeEl) {
        const maj = (majorEl.value||'').trim().toLowerCase();
        if (['none','no','n/a','null',''].includes(maj)){
          venueEl.value = 'None';
          venueEl.disabled = true;
        } else {
          venueEl.disabled = false;
          biomeEl.value = 'None';
        }
      }
    } catch(e) { console.warn('[ContextPanel] Rule enforcement error:', e); }
  }

  async function applyToServer(){
    console.log('[ContextPanel] Apply clicked');
    if (!window.apiClient || !apiClient.sessionId) return;
    const norm = (v)=>{ const s=(v||'').trim().toLowerCase(); return ['none','no','n/a','null',''].includes(s) ? null : v; };
    const payload = {
      location: {
        name: document.getElementById('dev-ctx-loc-name').value || '',
        major: norm(document.getElementById('dev-ctx-loc-major').value),
        venue: norm(document.getElementById('dev-ctx-venue').value),
      },
      weather: { type: norm(document.getElementById('dev-ctx-weather').value) },
      time_of_day: norm(document.getElementById('dev-ctx-tod').value),
      biome: norm(document.getElementById('dev-ctx-biome').value),
      interior: document.getElementById('dev-ctx-interior').checked,
      underground: document.getElementById('dev-ctx-underground').checked,
      crowd_level: norm(document.getElementById('dev-ctx-crowd').value),
      danger_level: norm(document.getElementById('dev-ctx-danger').value),
    };
    try {
      // Send context to backend - this will trigger SFX via backend's set_game_context
      const res = await fetch(`/api/context/${apiClient.sessionId}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)});
      // Apply selected music mood immediately via backend (mirror desktop GUI)
      try {
        const moodEl = document.getElementById('dev-ctx-mood');
        const mood = (moodEl && moodEl.value) ? String(moodEl.value).trim() : '';
        if (mood) {
          fetch(`/api/music/hard_set/${apiClient.sessionId}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ mood }) }).catch(()=>{});
        }
      } catch { /* ignore */ }
      if (res.ok) {
        // Update state and display
        const ctx = {
          location: payload.location,
          weather: payload.weather,
          time_of_day: payload.time_of_day,
          biome: payload.biome,
          interior: payload.interior,
          underground: payload.underground,
          crowd_level: payload.crowd_level,
          danger_level: payload.danger_level
        };
        state.ctx = ctx;
        renderCtx(ctx);
        
        // Also apply locally for instant feedback; WS update will follow
        if (window.webMusicManager && typeof window.webMusicManager.applyContext === 'function') {
          window.webMusicManager.applyContext(ctx);
        }
        
        console.log('[ContextPanel] Context applied successfully:', ctx);
      } else {
        console.warn('[ContextPanel] Failed to apply context:', res.status);
      }
    } catch(e) { console.warn('applyToServer failed', e); }
  }

  async function fetchAndFillMoods(){
    try {
      const el = document.getElementById('dev-ctx-mood'); if (!el) return;
      if (!window.apiClient || !apiClient.sessionId) {
        // Fallback if no session
        const fallbackMoods = ['ambient', 'combat', 'exploration', 'tension', 'mystery'];
        el.innerHTML='';
        fallbackMoods.forEach(m=>{ const o=document.createElement('option'); o.value=m; o.textContent=m; el.appendChild(o); });
        return;
      }
      
      // Fetch from backend
      const res = await fetch(`/api/music/moods/${apiClient.sessionId}`);
      const j = await res.json();
      const moods = (j && j.moods) || [];
      
      // Add current mood from state if not in list
      try {
        const ms = window.__lastMusicState;
        if (ms && (ms.data || ms).mood) {
          const currentMood = (ms.data || ms).mood;
          if (!moods.includes(currentMood)) {
            moods.unshift(currentMood);
          }
        }
      } catch {}
      
      el.innerHTML='';
      moods.forEach(m=>{ const o=document.createElement('option'); o.value=m; o.textContent=m; el.appendChild(o); });
      
      // Select last known mood if available
      try { 
        const ms = window.__lastMusicState; 
        const mood = (ms && (ms.data||ms).mood) || null; 
        if (mood) el.value = mood; 
      } catch {}
    } catch(e) { 
      console.warn('[ContextPanel] fetchAndFillMoods error:', e);
      // Fallback on error
      const el = document.getElementById('dev-ctx-mood');
      if (el && el.options.length === 0) {
        const fallbackMoods = ['ambient', 'combat', 'exploration', 'tension', 'mystery'];
        fallbackMoods.forEach(m=>{ const o=document.createElement('option'); o.value=m; o.textContent=m; el.appendChild(o); });
      }
    }
  }

  // Mood change -> call backend hard_set endpoint
  try {
    document.addEventListener('change', (ev)=>{
      const t = ev.target; if (!t || t.id !== 'dev-ctx-mood') return;
      try {
        if (!window.apiClient || !apiClient.sessionId) return;
        const mood = (t.value||'').trim(); if (!mood) return;
        console.log(`[ContextPanel] Mood change requested: ${mood}`);
        // Call backend to actually change the mood
        fetch(`/api/music/hard_set/${apiClient.sessionId}`, { 
          method:'POST', 
          headers:{'Content-Type':'application/json'}, 
          body: JSON.stringify({ mood }) 
        }).then(res => {
          if (res.ok) {
            console.log(`[ContextPanel] Music mood set to ${mood}`);
          } else {
            console.warn(`[ContextPanel] Failed to set mood: ${res.status}`);
          }
        }).catch(e => {
          console.warn('[ContextPanel] Mood change request failed:', e);
        });
      } catch(e) { console.warn('[ContextPanel] Mood change error:', e); }
    });
  } catch {}

  async function init(){
    const dev = await fetchDevFlag();
    if (!dev) return; // Do not show in production
    if (!ensureTab()) return;
    // Initial fetch shortly after session creation
    document.addEventListener('session-created', ()=> { 
      setTimeout(refreshFromServer, 300); 
      setTimeout(fetchAndFillMoods, 350);
      // Start periodic playback updates
      startPlaybackUpdates();
    });
    // If a session already exists, populate moods shortly after load
    setTimeout(()=>{ 
      try { fetchAndFillMoods(); } catch{}
      try { startPlaybackUpdates(); } catch{}
    }, 400);
  }
  
  function startPlaybackUpdates() {
    // Periodically pull playback snapshot from WebMusicManager
    if (state._playbackInterval) return; // Already running
    state._playbackInterval = setInterval(() => {
      try {
        if (window.webMusicManager && typeof window.webMusicManager.getPlaybackSnapshot === 'function') {
          const snapshot = window.webMusicManager.getPlaybackSnapshot();
          if (window.ContextPanel && typeof window.ContextPanel.onPlaybackUpdate === 'function') {
            window.ContextPanel.onPlaybackUpdate(snapshot);
          }
        }
      } catch(e) { /* ignore */ }
    }, 1000); // Update every second
  }

  // Expose minimal API for WS updates
  window.ContextPanel = {
    onContextUpdate: function(data){
      const ctx = data && data.data ? data.data : data;
      state.ctx = ctx; renderCtx(ctx); prefillForm(ctx);
    },
    onMusicState: function(data){
      try { 
        const mood = (data && (data.data||data).mood) || null; 
        if (!mood) return; 
        const el=document.getElementById('dev-ctx-mood'); 
        if (el) {
          // Update mood dropdown
          el.value = mood;
          // Also update fallback mood list if this is a new mood
          if (!Array.from(el.options).some(opt => opt.value === mood)) {
            const opt = document.createElement('option');
            opt.value = mood;
            opt.textContent = mood;
            el.insertBefore(opt, el.firstChild);
            el.value = mood;
          }
        }
      } catch {}
    },
    onPlaybackUpdate: function(items){
      try {
        const list = document.getElementById('dev-ctx-now-playing');
        if (!list) return;
        list.innerHTML = '';
        if (!items || items.length === 0) {
          const li = document.createElement('li');
          li.style.padding = '4px 8px';
          li.style.color = '#888';
          li.style.fontSize = '12px';
          li.textContent = 'No playback info';
          list.appendChild(li);
          return;
        }
        items.slice(0, 5).forEach(item => {
          const li = document.createElement('li');
          li.style.padding = '4px 8px';
          li.style.color = '#e0e0e0';
          li.style.fontSize = '12px';
          li.style.borderBottom = '1px solid #333';
          li.textContent = item;
          list.appendChild(li);
        });
      } catch(e) { console.warn('[ContextPanel] onPlaybackUpdate error:', e); }
    }
  };

  // Start
  document.addEventListener('DOMContentLoaded', init);
})();