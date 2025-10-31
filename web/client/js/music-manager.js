/**
 * WebMusicManager using Web Audio API (Milestone 1 baseline)
 * - Two music sources for crossfade
 * - Simple stinger ducking (optional, not wired yet)
 * - SFX buses (stubs)
 * - Enable Sound overlay to satisfy autoplay
 */
class WebMusicManager {
  constructor() {
    this.ctx = null;
    this.masterGain = null;
    this.musicGainA = null;
    this.musicGainB = null;
    this.musicSrcA = null;
    this.musicSrcB = null;
    this.audioElementA = null; // track HTMLAudio for cleanup
    this.audioElementB = null;
    this.useA = true;
    this.muted = false;
    this.master = 1.0; // 0..1
    this.music = 1.0;
    this.effects = 1.0;
    this.intensity = 0.3; // 0..1
    this.currentUrl = null;
    this.pendingState = null;
    // SFX bus and state
    this.sfxGain = null;
    this._lastCtx = null;
    this._lastVenueTs = 0;
    this._lastWeatherTs = 0;
    // Loop channels: environment and weather
    this.weatherLoopEl = null;
    this.weatherLoopSrc = null;
    this.environmentLoopEl = null;
    this.environmentLoopSrc = null;
    // Track active loops and recent oneshots for "Now Playing" display
    this._activeLoops = { environment: null, weather: null };
    this._recentOneshots = [];
    this._lastMusicTrack = null;
    // Rotation management
    this._loopPools = { environment: [], weather: [] };
    this._loopNextSwapTs = { environment: 0, weather: 0 };
    this._loopRotationPeriodMs = 120000; // 120s like Python
    this._rotatorInterval = null;
    // Directory listing caches to avoid spamming server
    this._envListCache = new Map(); // domain -> [urls]
    this._weatherListCache = new Map(); // token -> [urls]
    this._startRotator();
  }
  async enableAudio() {
    // Create audio context if missing, otherwise resume if suspended
    if (this.ctx) {
      try { if (this.ctx.state === 'suspended') await this.ctx.resume(); } catch {}
      return;
    }
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = this.muted ? 0 : this.master;
    this.masterGain.connect(this.ctx.destination);

    this.musicGainA = this.ctx.createGain();
    this.musicGainB = this.ctx.createGain();
    this.musicGainA.gain.value = 0;
    this.musicGainB.gain.value = 0;
    // SFX bus
    this.sfxGain = this.ctx.createGain();
    this.sfxGain.gain.value = this.muted ? 0 : (this.master * this.effects);

    this.musicGainA.connect(this.masterGain);
    this.musicGainB.connect(this.masterGain);
    this.sfxGain.connect(this.masterGain);

    // apply any pending state once enabled
    if (this.pendingState) {
      this.applyState(this.pendingState);
      this.pendingState = null;
    }
  }
  async setEnabled(on) {
    this.muted = !on;
    if (on) {
      await this.enableAudio();
      if (this.masterGain) this.masterGain.gain.value = this.master;
      try { if (this.ctx && this.ctx.state === 'suspended') await this.ctx.resume(); } catch {}
    } else {
      if (this.masterGain) this.masterGain.gain.value = 0;
      try { if (this.ctx && this.ctx.state === 'running') await this.ctx.suspend(); } catch {}
    }
  }
  _intensityGain(i, gamma = 1.8, floor = 0.0) {
    i = Math.max(0, Math.min(1, i || 0));
    if (i === 0) return 0;
    let g = Math.pow(i, gamma);
    if (floor > 0) g = floor + (1 - floor) * g;
    return Math.max(0, Math.min(1, g));
  }
  _targetMusicGain() {
    if (!this.ctx) return 0;
    if (this.muted) return 0;
    return this.master * this.music * this._intensityGain(this.intensity);
  }
  _rampGain(node, target, seconds) {
    if (!node || !this.ctx) return;
    const now = this.ctx.currentTime;
    try {
      node.gain.cancelScheduledValues(now);
      node.gain.setValueAtTime(node.gain.value, now);
      node.gain.linearRampToValueAtTime(target, now + Math.max(0.01, seconds||0));
    } catch {}
  }
  setVolumes(masterPct, musicPct, effectsPct, muted) {
    this.master = Math.max(0, Math.min(1, (masterPct||0)/100));
    this.music = Math.max(0, Math.min(1, (musicPct||0)/100));
    this.effects = Math.max(0, Math.min(1, (effectsPct||0)/100));
    this.muted = !!muted;
    if (this.masterGain) this.masterGain.gain.value = this.muted ? 0 : this.master;
    if (this.sfxGain) this.sfxGain.gain.value = this.muted ? 0 : (this.master * this.effects);
    // Also update the currently active music gain node to apply music volume/intensity change immediately
    const activeGain = this.useA ? this.musicGainA : this.musicGainB;
    if (activeGain) {
      const tgt = this._targetMusicGain();
      if (this.ctx) {
        this._rampGain(activeGain, tgt, 0.25);
      } else {
        activeGain.gain.value = tgt;
      }
    }
  }
  async _createMediaElement(url) {
    const audio = new Audio();
    audio.src = url;
    audio.crossOrigin = 'anonymous';
    audio.loop = true; // keep looping long tracks
    // Attempt to play; browsers may block until a user gesture enables audio
    await audio.play().catch(()=>{});
    return audio;
  }
  async applyState(state) {
    // state: { mood, intensity, url, muted, master, music, effects, reason }
    if (!this.ctx) {
      this.pendingState = state;
      return;
    }
    // Update volumes first
    this.setVolumes(state.master||100, state.music||100, state.effects||100, !!state.muted);
    // Update intensity from state if provided
    if (typeof state.intensity === 'number') {
      this.intensity = Math.max(0, Math.min(1, state.intensity));
    }

    const url = state.url || null;
    // If URL unchanged, apply intensity-only update with short ramp
    if (!url || url === this.currentUrl) {
      const activeGain = this.useA ? this.musicGainA : this.musicGainB;
      if (activeGain) {
        const reason = String(state.reason || '').toLowerCase();
        const isAttack = reason.includes('jumpscare_attack');
        const isRelease = reason.includes('jumpscare_release');
        const ramp = isAttack ? 0.08 : (isRelease ? 0.8 : 0.25);
        this._rampGain(activeGain, this._targetMusicGain(), ramp);
      }
      return;
    }
    // Crossfade to new track
    const reason = String(state.reason || '').toLowerCase();
    const intensityNow = this._intensityGain(this.intensity);
    // Optionally vary fade length with intensity (faster at high intensity)
    const fadeMs = Math.max(400, Math.min(4000, Math.round(3000 - 2200 * intensityNow)));
    try {
      const newEl = await this._createMediaElement(url);
      const newSrc = this.ctx.createMediaElementSource(newEl);
      const tgtGain = this.useA ? this.musicGainB : this.musicGainA;
      const curGain = this.useA ? this.musicGainA : this.musicGainB;
      const oldElement = this.useA ? this.audioElementB : this.audioElementA;

      newSrc.connect(tgtGain);
      // crossfade
      const now = this.ctx.currentTime;
      tgtGain.gain.cancelScheduledValues(now);
      curGain.gain.cancelScheduledValues(now);
      tgtGain.gain.setValueAtTime(0, now);
      tgtGain.gain.linearRampToValueAtTime(this._targetMusicGain(), now + fadeMs/1000);
      curGain.gain.setValueAtTime(curGain.gain.value, now);
      curGain.gain.linearRampToValueAtTime(0, now + fadeMs/1000);

      // Stop and cleanup old audio element after fade completes
      setTimeout(() => {
        try {
          if (oldElement) {
            oldElement.pause();
            oldElement.currentTime = 0;
            oldElement.src = '';
          }
        } catch {}
      }, fadeMs + 100);

      // flip active and store new element
      if (this.useA) {
        this.audioElementB = newEl;
        this.musicSrcB = newSrc;
      } else {
        this.audioElementA = newEl;
        this.musicSrcA = newSrc;
      }
      this.useA = !this.useA;
      this.currentUrl = url;
      // Track for Now Playing
      try {
        const basename = url ? url.split('/').pop() : null;
        this._lastMusicTrack = basename;
      } catch {}
    } catch (e) {
      console.warn('WebMusicManager applyState error:', e);
    }
  }


  _resolveUrl(relOrAbs) {
    if (!relOrAbs) return null;
    if (/^https?:\/\//i.test(relOrAbs) || relOrAbs.startsWith('/')) return relOrAbs;
    return `/sound/${relOrAbs}`.replace(/\/+/, '/');
  }
  
  _normalizeToWebUrl(anyPath) {
    try {
      if (!anyPath) return null;
      if (/^https?:\/\//i.test(anyPath) || String(anyPath).startsWith('/')) return anyPath;
      const s = String(anyPath);
      // Find 'sound' segment and convert tail to /sound/
      const idx = s.toLowerCase().lastIndexOf('sound');
      if (idx >= 0) {
        const tail = s.slice(idx + 'sound'.length).replace(/\\/g, '/').replace(/^\/+/, '');
        return `/sound/${tail}`.replace(/\/+/, '/');
      }
    } catch {}
    return null;
  }
  
  async _listEnvFiles(domain) {
    if (!domain) return [];
    if (this._envListCache.has(domain)) return this._envListCache.get(domain) || [];
    try {
      const res = await fetch(`/api/sfx/loop_list/${encodeURIComponent(domain)}`);
      const j = await res.json();
      const files = (j && j.files) || [];
      this._envListCache.set(domain, files);
      return files;
    } catch (e) {
      console.warn('[SFX] listEnvFiles error:', e);
      return [];
    }
  }
  
  async _listWeatherFiles(token) {
    if (!token) return [];
    if (this._weatherListCache.has(token)) return this._weatherListCache.get(token) || [];
    try {
      const res = await fetch(`/api/sfx/weather_list/${encodeURIComponent(token)}`);
      const j = await res.json();
      const files = (j && j.files) || [];
      this._weatherListCache.set(token, files);
      return files;
    } catch (e) {
      console.warn('[SFX] listWeatherFiles error:', e);
      return [];
    }
  }

  async playSfx(category, name) {
    try {
      const cat = String(category||'').toLowerCase();
      const key = String(name||'').toLowerCase();
      // Comprehensive mapping for all SFX categories
      const sfxMap = {
        'ui': {
          'click': 'sfx/ui/ui_click_01.mp3',
          'dropdown': 'sfx/ui/ui_dropdown.mp3',
          'tab_click': 'sfx/ui/ui_tab_click_01.mp3',
          'loot_pickup': 'sfx/ui/loot_pickup_01.mp3'
        },
        'weather': {
          'storm': 'sfx/weather/storm_oneshot.mp3',
          'rain': 'sfx/weather/rain_oneshot.mp3',
          'windy': 'sfx/weather/wind_gust.mp3'
        },
        'crowd': {
          'busy': 'sfx/crowd/chatter_busy_1.mp3',
          'sparse': 'sfx/crowd/footsteps_sparse_1.mp3',
          'empty': 'sfx/crowd/empty_room_tail.mp3'
        },
        'event': {
          'combat_start': 'sfx/event/event_combat_start_01.mp3',
          'victory': 'sfx/event/event_victory_fanfare_01.mp3',
          'defeat': 'sfx/event/event_defeat_01.mp3'
        },
        'magic': {
          'generic_short': 'sfx/magic/magic_generic_cast_short_01.mp3',
          'flames': 'sfx/magic/magic_flames_cast_short_01.mp3',
          'lightning': 'sfx/magic/magic_lightning_cast_short_01.mp3'
        }
      };
      
      const categoryMap = sfxMap[cat];
      if (!categoryMap) return; // unknown category
      const rel = categoryMap[key];
      if (!rel) return; // unknown sound in category
      
      await this.enableAudio();
      if (!this.ctx || !this.sfxGain) return;
      const el = new Audio();
      el.src = this._resolveUrl(rel); 
      el.crossOrigin = 'anonymous'; 
      el.loop = false;
      
      // Add error handler for missing files
      el.addEventListener('error', (e) => {
        console.warn(`[SFX] Failed to load ${cat}:${key} from ${rel}:`, el.error);
      });
      
      const src = this.ctx.createMediaElementSource(el);
      src.connect(this.sfxGain);
      await el.play().catch((e)=>{ console.warn(`[SFX] Play failed for ${cat}:${key}:`, e); });
      el.addEventListener('ended', ()=>{ try { el.src=''; } catch {} });
      
      // Track one-shot with expiry timestamp (like Python)
      try {
        const now = Date.now() / 1000; // seconds
        const expiry = now + (cat === 'ui' ? 1.0 : 3.0); // UI expires in 1s, others in 3s
        this._recentOneshots.push([rel, expiry]);
        this._pruneRecentOneshots();
      } catch {}
    } catch(e) { console.warn('[SFX] playSfx error:', e); }
  }


  async applyContext(ctx) {
    console.log('[SFX] Applying context:', ctx);
    const prev = this._lastCtx || {};
    this._lastCtx = ctx || {};
    const now = Date.now();
    
    // Extract context fields
    const loc = (ctx?.location || {});
    const weather = (ctx?.weather || {});
    const tod = (ctx?.time_of_day || '').trim().toLowerCase() || null;
    const major = (loc?.major || '').trim().toLowerCase() || null;
    let venue = (loc?.venue || '').trim().toLowerCase() || null;
    if (venue && ['none', 'no', 'n/a', 'null', ''].includes(venue)) venue = null;
    const biome = (ctx?.biome || '').trim().toLowerCase() || null;
    const region = (ctx?.region || '').trim().toLowerCase() || null;
    const wtype = (weather?.type || '').trim().toLowerCase() || null;
    
    // NOTE: Venues are LOOPS not one-shots - they're part of environment loop
    // Only crowd has one-shots
    
    // Crowd one-shot
    try {
      const crowd = (ctx?.crowd_level||'').trim().toLowerCase();
      const prevCrowd = (prev?.crowd_level||'').trim().toLowerCase();
      if (crowd && crowd !== prevCrowd) this.playSfx('crowd', crowd);
    } catch {}
    
    // Update environment loop (domain priority: venue > major > biome > region)
    await this._updateEnvironmentLoop(major, tod, venue, biome, region);
    
    // Update weather loop
    await this._updateWeatherLoop(wtype);
  }
  
  async _updateEnvironmentLoop(major, tod, venue, biome, region) {
    // Domain priority: venue > major > biome > region
    const candidates = [venue, major, biome, region].filter(Boolean);
    let chosen = null;
    let files = [];

    // Try each candidate until we find a domain that actually has files
    for (const cand of candidates) {
      const list = await this._listEnvFiles(cand);
      if (list && list.length > 0) {
        chosen = cand;
        files = list;
        break;
      }
    }

    if (!chosen) {
      // Stop environment loop if no valid domain
      if (this.environmentLoopEl) {
        try { this.environmentLoopEl.pause(); this.environmentLoopEl.src=''; } catch {}
        this.environmentLoopEl = null; this.environmentLoopSrc = null; this._activeLoops.environment = null;
      }
      this._loopPools.environment = [];
      return;
    }

    // Score files (mirror Python heuristic)
    const scored = files.map(url => {
      const filename = String(url).split('/').pop().toLowerCase();
      let s = 0;
      if (chosen && filename.includes(String(chosen).toLowerCase())) s += 2;
      if (filename.includes('loop')) s += 1;
      if (tod && filename.includes(String(tod).toLowerCase())) s += 2;
      return { url, score: s };
    }).sort((a,b)=>b.score-a.score);

    const best = (scored[0] && scored[0].url) || files[0];
    this._loopPools.environment = files.slice();
    if (best && best !== this._activeLoops.environment) {
      await this._startEnvironmentLoop(best);
      this._loopNextSwapTs.environment = Date.now() + this._loopRotationPeriodMs;
    }
  }
  
  async _updateWeatherLoop(wtype) {
    if (!wtype) {
      // Stop if no weather
      if (this.weatherLoopEl) {
        try { this.weatherLoopEl.pause(); this.weatherLoopEl.src=''; } catch {}
        this.weatherLoopEl = null; this.weatherLoopSrc = null; this._activeLoops.weather = null; this._loopPools.weather = [];
      }
      return;
    }
    const files = await this._listWeatherFiles(wtype);
    if (files && files.length > 0) {
      const urls = files.slice();
      this._loopPools.weather = urls;
      const bestUrl = urls[0];
      if (bestUrl !== this._activeLoops.weather) {
        await this._startWeatherLoop(bestUrl);
        this._loopNextSwapTs.weather = Date.now() + this._loopRotationPeriodMs;
      }
    } else {
      // Stop weather loop if no matching type
      if (this.weatherLoopEl) {
        try { this.weatherLoopEl.pause(); this.weatherLoopEl.src=''; } catch {}
        this.weatherLoopEl = null; this.weatherLoopSrc = null; this._activeLoops.weather = null; this._loopPools.weather = [];
      }
    }
  }
  
  async _startEnvironmentLoop(url) {
    console.log(`[SFX] Starting environment loop: ${url}`);
    await this.enableAudio();
    try {
      // Stop previous loop
      if (this.environmentLoopEl) {
        try { this.environmentLoopEl.pause(); this.environmentLoopEl.src=''; } catch {}
        this.environmentLoopEl = null;
        this.environmentLoopSrc = null;
      }
      if (!url) {
        this._activeLoops.environment = null;
        return;
      }
      if (!this.ctx || !this.sfxGain) {
        console.warn('[SFX] Audio context or SFX gain not ready for environment loop');
        return;
      }
      const el = new Audio();
      el.crossOrigin = 'anonymous';
      el.loop = true;
      el.src = url;
      
      // Add error handler but don't cascade through pool
      el.addEventListener('error', (e) => {
        console.warn(`[SFX] Environment loop load failed for ${url}:`, el.error);
        this._activeLoops.environment = null;
      });
      
      const src = this.ctx.createMediaElementSource(el);
      src.connect(this.sfxGain);
      
      await el.play().catch((e) => { 
        console.warn('[SFX] Environment loop play failed:', e);
        this._activeLoops.environment = null;
      });
      
      this.environmentLoopEl = el;
      this.environmentLoopSrc = src;
      this._activeLoops.environment = url;
      
      // Prune recent oneshots and notify
      this._pruneRecentOneshots();
    } catch (e) {
      console.error('[SFX] Environment loop error:', e);
      this._activeLoops.environment = null;
    }
  }
  
  async _pickEnvLoop(domain, tod) {
    if (!domain) return { best: null, pool: [] };
    const files = await this._listEnvFiles(domain);
    const pool = (files || []).slice();
    if (!pool || pool.length === 0) return { best: null, pool: [] };
    // Score files like Python does
    const scored = pool.map(url => {
      const filename = url.split('/').pop().toLowerCase();
      let score = 0;
      if (domain && filename.includes(domain)) score += 2;
      if (filename.includes('loop')) score += 1;
      if (tod && filename.includes(tod)) score += 2;
      return { url, score };
    });
    scored.sort((a,b) => b.score - a.score);
    const best = scored.length > 0 ? scored[0].url : pool[0];
    return { best, pool };
  }
  
  async _startWeatherLoop(url) {
    console.log(`[SFX] Starting weather loop: ${url}`);
    await this.enableAudio();
    try {
      if (this.weatherLoopEl) {
        try { this.weatherLoopEl.pause(); this.weatherLoopEl.src=''; } catch {}
        this.weatherLoopEl = null;
        this.weatherLoopSrc = null;
      }
      if (!url) {
        this._activeLoops.weather = null;
        return;
      }
      if (!this.ctx || !this.sfxGain) {
        console.warn('[SFX] Audio context or SFX gain not ready for weather loop');
        return;
      }
      const el = new Audio();
      el.src = url;
      el.crossOrigin = 'anonymous';
      el.loop = true;
      const src = this.ctx.createMediaElementSource(el);
      src.connect(this.sfxGain);
      await el.play().catch((e) => { 
        console.warn('[SFX] Weather loop play failed:', e);
        this._activeLoops.weather = null;
      });
      this.weatherLoopEl = el;
      this.weatherLoopSrc = src;
      this._activeLoops.weather = url;
      
      // Prune recent oneshots and notify
      this._pruneRecentOneshots();
    } catch (e) {
      console.error('[SFX] Weather loop error:', e);
      this._activeLoops.weather = null;
    }
  }
  
  _startRotator() {
    // Background rotation similar to Python's rotator worker
    if (this._rotatorInterval) return;
    this._rotatorInterval = setInterval(() => {
      try {
        const now = Date.now();
        for (const ch of ['environment', 'weather']) {
          const pool = this._loopPools[ch] || [];
          const current = this._activeLoops[ch];
          if (!current || pool.length <= 1) continue;
          if (now >= this._loopNextSwapTs[ch]) {
            // Pick a different file from pool
            const candidates = pool.filter(p => p !== current);
            if (candidates.length > 0) {
              const next = candidates[Math.floor(Math.random() * candidates.length)];
              if (ch === 'environment') {
                this._startEnvironmentLoop(next);
              } else {
                this._startWeatherLoop(next);
              }
              this._loopNextSwapTs[ch] = now + this._loopRotationPeriodMs;
            }
          }
        }
      } catch (e) {
        console.warn('[SFX] Rotator error:', e);
      }
    }, 1000); // Check every second
  }
  
  getPlaybackSnapshot() {
    // Prune expired oneshots first
    this._pruneRecentOneshots();
    
    // Return combined music + SFX for "Now Playing" display
    const items = [];
    if (this._lastMusicTrack) {
      items.push(`music: ${this._lastMusicTrack}`);
    }
    for (const [ch, url] of Object.entries(this._activeLoops)) {
      if (url) {
        const basename = url.split('/').pop();
        items.push(`sfx:${ch}: ${basename}`);
      }
    }
    // Recent oneshots are now just strings
    for (const path of this._recentOneshots.slice(-3)) {
      const basename = (typeof path === 'string' ? path : '').split('/').pop();
      if (basename) items.push(`sfx:oneshot: ${basename}`);
    }
    return items.slice(0, 5);
  }
  
  _pruneRecentOneshots() {
    // Python prunes by expiry timestamp
    const now = Date.now() / 1000;
    this._recentOneshots = this._recentOneshots.filter(item => {
      // If item is [path, expiry], check expiry
      if (Array.isArray(item) && item.length === 2) {
        return item[1] > now;
      }
      // Legacy string format - remove after 3 seconds
      return false;
    }).map(item => Array.isArray(item) ? item[0] : item);
  }
  
  onSfxUpdate(payload) {
    // Handle SFX updates from server (if backend sends them)
    try {
      const loops = payload.loops || {};
      const oneshots = payload.oneshots || [];
      // Normalize to web URLs in case server sent absolute paths
      const envUrl = this._normalizeToWebUrl(loops.environment) || loops.environment || null;
      const wUrl = this._normalizeToWebUrl(loops.weather) || loops.weather || null;
      if (envUrl) this._activeLoops.environment = envUrl;
      if (wUrl) this._activeLoops.weather = wUrl;
      // oneshots may come as urls already
      const normOnes = oneshots.map(p => this._normalizeToWebUrl(p) || p).filter(Boolean);
      // Track as most recent strings (not TTL, server snapshot is ephemeral)
      // We'll merge with our local TTL store by adding these with a short expiry
      const now = Date.now() / 1000;
      for (const p of normOnes) {
        this._recentOneshots.push([p, now + 2.0]);
      }
      this._pruneRecentOneshots();
    } catch (e) {
      console.error('[SFX] onSfxUpdate error:', e);
    }
  }
}

// Singleton
window.webMusicManager = new WebMusicManager();
// Apply any pending context captured before script load
try { if (window.__pendingCtx && typeof window.webMusicManager.applyContext === 'function') { window.webMusicManager.applyContext(window.__pendingCtx); window.__pendingCtx = null; } } catch {}
// Best-effort: attempt to enable audio shortly after load
try { setTimeout(()=>{ window.webMusicManager.enableAudio().catch(()=>{}); }, 200); } catch {}
