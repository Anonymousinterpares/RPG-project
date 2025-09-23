/**
 * Character creator module for the RPG Game
 * Handles character creation UI, icon selection, and form validation
 */

// Character Creator Module
const CharacterCreator = (function() {
    // Private variables
    let characterIcons = [];
    let currentIconIndex = 0;
    let selectedIcon = null;

    // DOM elements
    let iconDisplay = null;
    let prevButton = null;
    let nextButton = null;
    let sexSelector = null;

    // Stats state
    const STAT_KEYS = ['STR','DEX','CON','INT','WIS','CHA','WIL','INS'];
    const BASE_DEFAULT = 8;
    let statBase = Object.fromEntries(STAT_KEYS.map(k=>[k, BASE_DEFAULT]));
    let statAdjust = Object.fromEntries(STAT_KEYS.map(k=>[k, 0]));
    let raceMods = Object.fromEntries(STAT_KEYS.map(k=>[k, 0]));
    let classMods = Object.fromEntries(STAT_KEYS.map(k=>[k, 0]));
    let pointPool = 27;
    let minStat = 3;
    let maxStat = 18;

    function getSpentPoints() { return STAT_KEYS.reduce((s,k)=> s + (statAdjust[k]||0), 0); }
    function getPointsRemaining() { return pointPool - getSpentPoints(); }

    function setAdjust(k, delta) {
        const newAdj = (statAdjust[k]||0) + delta;
        const newBase = (statBase[k]||BASE_DEFAULT) + newAdj;
        if (newBase < minStat || newBase > maxStat) return;
        // Respect point pool
        const spentIf = getSpentPoints() + delta;
        if (spentIf > pointPool) return;
        statAdjust[k] = newAdj;
        renderStatsUI();
    }

    function resetAlloc() {
        STAT_KEYS.forEach(k=> statAdjust[k] = 0);
        renderStatsUI();
    }

    function applyPreset(preset) {
        resetAlloc();
        const plan = {
            'Healer': { WIS: 6, CON: 4, INT: 2, DEX: 2 },
            'Crusader': { STR: 6, CON: 6, WIS: 2 },
            'Oracle': { WIS: 7, INS: 4, CON: 2 }
        }[preset] || {};
        for (const [k, v] of Object.entries(plan)) {
            for (let i=0;i<v;i++) setAdjust(k, +1);
        }
    }

    function modFromTotal(total) { return Math.floor((total - 10) / 2); }

    function renderStatsUI() {
        try {
            const grid = document.getElementById('cc-stats-grid');
            const prEl = document.getElementById('cc-points-remaining');
            const rcEl = document.getElementById('cc-stats-rc-display');
            const raceSel = document.getElementById('character-race-select');
            const classSel = document.getElementById('character-class-select');
            if (rcEl) rcEl.textContent = `${raceSel?.value||''} • ${classSel?.value||''}`;
            if (prEl) prEl.textContent = String(getPointsRemaining());
            if (!grid) return;
            const header = `<div class=\"cc-stat-name\">Stat</div><div class=\"cc-stat-base\">Base</div><div class=\"cc-stat-adjust\">Adjust</div><div class=\"cc-stat-race\">Race</div><div class=\"cc-stat-class\">Class</div><div class=\"cc-stat-total\">Total</div><div class=\"cc-stat-mod\">Mod</div>`;
            const rows = STAT_KEYS.map(k=>{
                const base = statBase[k]||BASE_DEFAULT;
                const adj = statAdjust[k]||0;
                const r = raceMods[k]||0;
                const c = classMods[k]||0;
                const total = base + adj + r + c;
                const mod = modFromTotal(total);
                return `<div class=\"cc-stat-row\">
                    <div class=\"cc-stat-name\">${k}</div>
                    <div class=\"cc-stat-base\">${base}</div>
                    <div class=\"cc-stat-adjust\"><div class=\"cc-stat-controls\"><button class=\"cc-stat-btn\" data-k=\"${k}\" data-d=\"-1\">-</button><span>${adj>=0?`+${adj}`:adj}</span><button class=\"cc-stat-btn\" data-k=\"${k}\" data-d=\"+1\">+</button></div></div>
                    <div class=\"cc-stat-race\">${r>=0?`+${r}`:r}</div>
                    <div class=\"cc-stat-class\">${c>=0?`+${c}`:c}</div>
                    <div class=\"cc-stat-total\">${total}</div>
                    <div class=\"cc-stat-mod\">${mod>=0?`+${mod}`:mod}</div>
                </div>`;
            }).join('');
            grid.innerHTML = header + rows;
            grid.querySelectorAll('.cc-stat-btn').forEach(btn=>{
                btn.addEventListener('click', ()=>{
                    const k = btn.getAttribute('data-k');
                    const d = parseInt(btn.getAttribute('data-d'), 10);
                    setAdjust(k, d);
                });
            });
        } catch (e) { console.warn('renderStatsUI error', e); }
    }

    function computeModifiersFromConfig() {
        try {
            const raceSel = document.getElementById('character-race-select');
            const classSel = document.getElementById('character-class-select');
            const raceName = raceSel?.value || '';
            const className = classSel?.value || '';
            // Use cached origins/classes/races from loadConfigAndPopulate scope variables
            // For races/classes we expect .names and maybe dict at CharacterCreator._config
            const cfg = CharacterCreator._config || {};
            const races = cfg.races || {};
            const classes = cfg.classes || {};
            const rEntry = Object.values(races).find(x => (x?.name||'') === raceName) || races[raceName] || {};
            const cEntry = Object.values(classes).find(x => (x?.name||'') === className) || classes[className] || {};
            raceMods = extractStatDict(rEntry);
            classMods = extractStatDict(cEntry);
            // Ensure all keys present
            STAT_KEYS.forEach(k=>{ if (raceMods[k]==null) raceMods[k]=0; if (classMods[k]==null) classMods[k]=0; });
        } catch (e) { /* ignore */ }
    }

    function extractStatDict(obj) {
        // Heuristically find a dict mapping stat keys -> numbers
        const candidates = ['stat_modifiers','modifiers','stats','stat_bonuses','primary_stats','base_stats'];
        for (const key of candidates) {
            if (obj && typeof obj[key] === 'object' && obj[key] !== null) {
                const out = {};
                const source = obj[key];
                for (const [k,v] of Object.entries(source)) {
                    const KK = (k||'').toString().toUpperCase().slice(0,3);
                    if (STAT_KEYS.includes(KK) && typeof v === 'number') out[KK] = v;
                }
                const keys = Object.keys(out);
                if (keys.length) return out;
            }
        }
        return Object.fromEntries(STAT_KEYS.map(k=>[k,0]));
    }

    function hookCreatorStepNav() {
        const tabs = document.querySelectorAll('.cc-tab-btn');
        tabs.forEach(btn=>{
            btn.addEventListener('click', ()=>{
                const step = btn.getAttribute('data-step');
                document.querySelectorAll('.cc-tab-btn').forEach(b=>b.classList.remove('active'));
                btn.classList.add('active');
                document.querySelectorAll('.cc-step').forEach(s=>{
                    if (s.getAttribute('data-step') === step) s.style.display='block'; else s.style.display='none';
                });
                if (step === 'stats') renderStatsUI();
            });
        });
    }
    
    // Initialize the module
    function init() {
        // Cache DOM elements
        iconDisplay = document.getElementById('character-icon-display');
        prevButton = document.getElementById('prev-icon-button');
        nextButton = document.getElementById('next-icon-button');
        sexSelector = document.getElementById('character-sex-select');
        
        // Add event listeners
        if (prevButton) prevButton.addEventListener('click', showPreviousIcon);
        if (nextButton) nextButton.addEventListener('click', showNextIcon);
        if (sexSelector) sexSelector.addEventListener('change', updateSexSelection);
        
        hookCreatorStepNav();
        // Load config-driven selects (races/classes/origins) and then icons
        loadConfigAndPopulate().then(()=>{
            loadFilteredIcons();
        }).catch(() => {
            // Fallback to flat icons list
            loadCharacterIcons();
        });

        // Stats controls
        const resetBtn = document.getElementById('cc-reset-btn');
        if (resetBtn) resetBtn.addEventListener('click', resetAlloc);
        const presetHealer = document.getElementById('cc-preset-healer');
        const presetCrusader = document.getElementById('cc-preset-crusader');
        const presetOracle = document.getElementById('cc-preset-oracle');
        if (presetHealer) presetHealer.addEventListener('click', ()=>applyPreset('Healer'));
        if (presetCrusader) presetCrusader.addEventListener('click', ()=>applyPreset('Crusader'));
        if (presetOracle) presetOracle.addEventListener('click', ()=>applyPreset('Oracle'));
        renderStatsUI();
    }
    
    // Load character icons from the server (flat, fallback)
    async function loadCharacterIcons() {
        try {
            if (!apiClient || typeof apiClient.getCharacterIcons !== 'function') {
                console.error('API client not available or getCharacterIcons method not found');
                throw new Error('API client not available');
            }
            
            const data = await apiClient.getCharacterIcons();
            
            if (data.status === 'success' && data.icons) {
                characterIcons = data.icons;
                // Display the first icon if available
                if (characterIcons.length > 0) {
                    displayIcon(0);
                } else {
                    displayNoIconsMessage();
                }
            } else {
                throw new Error('Invalid response format');
            }
        } catch (error) {
            console.error('Error loading character icons:', error);
            displayNoIconsMessage();
        }
    }
    
    // Display the icon at the specified index
    function displayIcon(index) {
        if (!iconDisplay || characterIcons.length === 0) return;
        
        // Ensure index is within bounds
        currentIconIndex = (index + characterIcons.length) % characterIcons.length;
        
        const icon = characterIcons[currentIconIndex];
        selectedIcon = icon;
        
        // Update the icon display
        iconDisplay.innerHTML = '';
        iconDisplay.style.backgroundImage = `url('${icon.url}')`;
        iconDisplay.style.backgroundSize = 'contain';
        iconDisplay.style.backgroundPosition = 'center';
        iconDisplay.style.backgroundRepeat = 'no-repeat';
        
        // Update the form value for icon
        const iconInput = document.getElementById('character-icon-input');
        if (iconInput) {
            iconInput.value = icon.path;
        }
        
        // Update counter display
        const counterDisplay = document.getElementById('icon-counter');
        if (counterDisplay) {
            counterDisplay.textContent = `${currentIconIndex + 1} / ${characterIcons.length}`;
        }
    }
    
    // Display a message when no icons are available
    function displayNoIconsMessage() {
        if (!iconDisplay) return;
        
        iconDisplay.innerHTML = '<div class="no-icons-message">No character icons available</div>';
        iconDisplay.style.backgroundImage = 'none';
        
        // Update counter display
        const counterDisplay = document.getElementById('icon-counter');
        if (counterDisplay) {
            counterDisplay.textContent = '0 / 0';
        }
    }
    
    // Show the next icon
    function showNextIcon() {
        displayIcon(currentIconIndex + 1);
    }
    
    // Show the previous icon
    function showPreviousIcon() {
        displayIcon(currentIconIndex - 1);
    }
    
    // Handle sex selection change
    function updateSexSelection(event) {
        try { loadFilteredIcons(); } catch (e) { console.warn(e); }
    }

    let _originsDict = {};
    let _originList = [];
    async function loadConfigAndPopulate() {
        try {
            // Populate races and classes
            const racesData = await apiClient.getConfigRaces();
            const classesData = await apiClient.getConfigClasses();
            const originsData = await apiClient.getConfigOrigins();
            _originsDict = originsData.origins || {};
            _originList = originsData.list || [];
            const raceSel = document.getElementById('character-race-select');
            const classSel = document.getElementById('character-class-select');
            const originSel = document.getElementById('character-background-select');
            // Clear current options
            function setOptions(sel, names) {
                if (!sel) return;
                sel.innerHTML = '';
                names.forEach(n => {
                    const opt = document.createElement('option');
                    opt.value = n; opt.textContent = n;
                    sel.appendChild(opt);
                });
            }
            setOptions(raceSel, (racesData.names||[]));
            setOptions(classSel, (classesData.names||[]));
            // Populate origins (use list, set data-origin-id)
            if (originSel) {
                originSel.innerHTML = '';
                const list = _originList;
                const placeholder = document.createElement('option');
                placeholder.value = '';
                placeholder.textContent = '-- Select an Origin ---';
                originSel.appendChild(placeholder);
                list.forEach(o => {
                    const opt = document.createElement('option');
                    opt.value = o.name || o.id || '';
                    opt.textContent = o.name || o.id || '';
                    if (o.id) opt.setAttribute('data-origin-id', o.id);
                    originSel.appendChild(opt);
                });
            }
            // On race/class change, reload icons and update stat modifiers
            if (raceSel) raceSel.addEventListener('change', () => { loadFilteredIcons(); computeModifiersFromConfig(); renderStatsUI(); });
            if (classSel) classSel.addEventListener('change', () => { loadFilteredIcons(); computeModifiersFromConfig(); renderStatsUI(); });
            if (originSel) originSel.addEventListener('change', () => updateOriginDetails());
            // Cache config for later
            CharacterCreator._config = { races: racesData.races||{}, classes: classesData.classes||{}, origins: originsData.origins||{} };
            // Initialize modifiers/details
            computeModifiersFromConfig();
            // Initialize origin details
            updateOriginDetails();
        } catch (e) {
            console.warn('Failed to populate selects from config', e);
            throw e;
        }
    }

    function _join(arr) {
        if (!Array.isArray(arr)) return '';
        return arr.map(x=> typeof x === 'string' ? x : (x && x.name) || String(x)).join(', ');
    }
    function _pick(obj, keys) {
        for (const k of keys) {
            if (obj && obj[k]!=null) return obj[k];
        }
        return null;
    }
    function _findOriginBySel(originSel) {
        if (!originSel) return null;
        const opt = originSel.selectedOptions && originSel.selectedOptions[0];
        if (!opt || !opt.value) return null;
        const oid = opt.getAttribute('data-origin-id');
        if (oid && _originsDict[oid]) return _originsDict[oid];
        const name = opt.value;
        return _originList.find(o => (o.name||o.id) === name) || null;
    }
    function updateOriginDetails() {
        try {
            const originSel = document.getElementById('character-background-select');
            const origin = _findOriginBySel(originSel);
            const descEl = document.getElementById('origin-description');
            const skillsEl = document.getElementById('origin-skills');
            const traitsEl = document.getElementById('origin-traits');
            const seedEl = document.getElementById('character-backstory-seed');
            if (!descEl || !skillsEl || !traitsEl || !seedEl) return;
            if (!origin) {
                descEl.textContent = 'Select an Origin to see details.';
                skillsEl.textContent = '-';
                traitsEl.textContent = '-';
                seedEl.value = '';
                return;
            }
            const description = _pick(origin, ['description','desc','summary','details']) || '';
            const profs = _pick(origin, ['skill_proficiencies','proficiencies','skills']) || [];
            const traits = _pick(origin, ['origin_traits','traits']) || [];
            // Backstory seed: try multiple possible fields
            let seed = _pick(origin, ['backstory_seed','seed','backstory','background_seed','starting_text']) || '';
            descEl.textContent = description || '-';
            skillsEl.textContent = _join(profs) || '-';
            traitsEl.textContent = _join(traits) || '-';
            if (!seedEl.value) seedEl.value = seed || '';
        } catch (e) {
            console.warn('Failed to update origin details', e);
        }
    }

    async function loadFilteredIcons() {
        try {
            const raceSel = document.getElementById('character-race-select');
            const classSel = document.getElementById('character-class-select');
            const sexSel = document.getElementById('character-sex-select');
            const race = raceSel ? raceSel.value : '';
            const clazz = classSel ? classSel.value : '';
            const sex = sexSel ? sexSel.value : 'Other';
            const data = await apiClient.getFilteredCharacterIcons(race, clazz, sex);
            if (data.status === 'success' && Array.isArray(data.icons)) {
                characterIcons = data.icons;
                if (characterIcons.length > 0) displayIcon(0); else displayNoIconsMessage();
            } else {
                displayNoIconsMessage();
            }
        } catch (e) {
            console.warn('Failed to load filtered icons', e);
            displayNoIconsMessage();
        }
    }
    
    // Get the currently selected icon
    function getSelectedIcon() {
        return selectedIcon;
    }
    
    // Validate the character creation form
    function validateForm() {
        const nameInput = document.getElementById('new-player-name');
        const originSel = document.getElementById('character-background-select');
        if (!nameInput || !nameInput.value.trim()) {
            alert('Please enter a character name');
            return false;
        }
        if (!originSel || !originSel.value) {
            alert('Please select an Origin');
            return false;
        }
        const remaining = getPointsRemaining();
        if (remaining < 0) {
            alert('You have allocated more points than available');
            return false;
        }
        return true;
    }
    
    // Public API
    return {
        init,
        getSelectedIcon,
        validateForm,
        getAllocatedStats: () => {
            // Return base + adjust only (engine will apply race/class modifiers)
            const out = {};
            STAT_KEYS.forEach(k=> out[k] = (statBase[k]||BASE_DEFAULT) + (statAdjust[k]||0));
            return out;
        }
    };
})();

// Initialize the module when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', CharacterCreator.init);

// Export the module for use in other scripts
window.CharacterCreator = CharacterCreator;
