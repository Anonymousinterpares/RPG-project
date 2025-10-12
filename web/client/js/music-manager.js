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
    this.useA = true;
    this.muted = false;
    this.master = 1.0; // 0..1
    this.music = 1.0;
    this.effects = 1.0;
    this.currentUrl = null;
    this.pendingState = null;
    this.overlay = null;
    this._ensureOverlay();
  }
  _ensureOverlay() {
    if (document.getElementById('enable-sound-overlay')) return;
    const overlay = document.createElement('div');
    overlay.id = 'enable-sound-overlay';
    overlay.style.position = 'fixed';
    overlay.style.inset = '0';
    overlay.style.background = 'rgba(0,0,0,0.6)';
    overlay.style.display = 'flex';
    overlay.style.alignItems = 'center';
    overlay.style.justifyContent = 'center';
    overlay.style.zIndex = '9999';
    overlay.innerHTML = '<button id="enable-sound-btn" style="padding:12px 18px;font-size:16px">Enable Sound</button>';
    document.body.appendChild(overlay);
    overlay.querySelector('#enable-sound-btn').addEventListener('click', ()=>{
      this.enableAudio().then(()=>{
        overlay.remove();
      }).catch(console.error);
    });
    this.overlay = overlay;
  }
  async enableAudio() {
    if (this.ctx) return;
    this.ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.masterGain = this.ctx.createGain();
    this.masterGain.gain.value = this.muted ? 0 : this.master;
    this.masterGain.connect(this.ctx.destination);

    this.musicGainA = this.ctx.createGain();
    this.musicGainB = this.ctx.createGain();
    this.musicGainA.gain.value = 0;
    this.musicGainB.gain.value = 0;
    this.musicGainA.connect(this.masterGain);
    this.musicGainB.connect(this.masterGain);

    // apply any pending state once enabled
    if (this.pendingState) {
      this.applyState(this.pendingState);
      this.pendingState = null;
    }
  }
  setVolumes(masterPct, musicPct, effectsPct, muted) {
    this.master = Math.max(0, Math.min(1, (masterPct||0)/100));
    this.music = Math.max(0, Math.min(1, (musicPct||0)/100));
    this.effects = Math.max(0, Math.min(1, (effectsPct||0)/100));
    this.muted = !!muted;
    if (this.masterGain) this.masterGain.gain.value = this.muted ? 0 : this.master;
  }
  async _createMediaElement(url) {
    const audio = new Audio();
    audio.src = url;
    audio.crossOrigin = 'anonymous';
    audio.loop = true; // keep looping long tracks
    await audio.play().catch(()=>{/* will be allowed once enabled */});
    return audio;
  }
  async applyState(state) {
    // state: { mood, intensity, url, muted, master, music, effects }
    if (!this.ctx) {
      this.pendingState = state;
      return;
    }
    // Update volumes
    this.setVolumes(state.master||100, state.music||100, state.effects||100, !!state.muted);

    const url = state.url || null;
    if (!url || url === this.currentUrl) {
      // nothing to do besides volume/mute
      return;
    }
    const fadeMs = 1500;
    try {
      const newEl = await this._createMediaElement(url);
      const newSrc = this.ctx.createMediaElementSource(newEl);
      const tgtGain = this.useA ? this.musicGainB : this.musicGainA;
      const curGain = this.useA ? this.musicGainA : this.musicGainB;

      newSrc.connect(tgtGain);
      // crossfade
      const now = this.ctx.currentTime;
      tgtGain.gain.cancelScheduledValues(now);
      curGain.gain.cancelScheduledValues(now);
      tgtGain.gain.setValueAtTime(0, now);
      tgtGain.gain.linearRampToValueAtTime(this.muted ? 0 : (this.master*this.music), now + fadeMs/1000);
      curGain.gain.setValueAtTime(curGain.gain.value, now);
      curGain.gain.linearRampToValueAtTime(0, now + fadeMs/1000);

      // flip active
      this.useA = !this.useA;
      this.currentUrl = url;
    } catch (e) {
      console.warn('WebMusicManager applyState error:', e);
    }
  }
}

// Singleton
window.webMusicManager = new WebMusicManager();