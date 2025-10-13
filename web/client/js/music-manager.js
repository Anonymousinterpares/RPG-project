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
    this.currentUrl = null;
    this.pendingState = null;
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
    this.musicGainA.connect(this.masterGain);
    this.musicGainB.connect(this.masterGain);

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
  setVolumes(masterPct, musicPct, effectsPct, muted) {
    this.master = Math.max(0, Math.min(1, (masterPct||0)/100));
    this.music = Math.max(0, Math.min(1, (musicPct||0)/100));
    this.effects = Math.max(0, Math.min(1, (effectsPct||0)/100));
    this.muted = !!muted;
    if (this.masterGain) this.masterGain.gain.value = this.muted ? 0 : this.master;
    // Also update the currently active music gain node to apply music volume change immediately
    const activeGain = this.useA ? this.musicGainA : this.musicGainB;
    if (activeGain) {
      activeGain.gain.value = this.muted ? 0 : (this.master * this.music);
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
      const oldElement = this.useA ? this.audioElementB : this.audioElementA;

      newSrc.connect(tgtGain);
      // crossfade
      const now = this.ctx.currentTime;
      tgtGain.gain.cancelScheduledValues(now);
      curGain.gain.cancelScheduledValues(now);
      tgtGain.gain.setValueAtTime(0, now);
      tgtGain.gain.linearRampToValueAtTime(this.muted ? 0 : (this.master*this.music), now + fadeMs/1000);
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
    } catch (e) {
      console.warn('WebMusicManager applyState error:', e);
    }
  }
}

// Singleton
window.webMusicManager = new WebMusicManager();
