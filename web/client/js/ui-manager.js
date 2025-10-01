/**
 * UI Manager for RPG Game Web Interface
 * Handles DOM interactions and UI state
 */

class UiManager {
    constructor() {
        // Main UI elements
        this.outputElement = document.getElementById('game-output');
        this.commandInput = document.getElementById('command-input');
        this.sendButton = document.getElementById('send-command-btn');

        // Lightweight recent message de-duplication
        // Stores { key: string, ts: number } for last few seconds
        this._recentMsgKeys = [];

        // Game info elements
        this.playerNameElement = document.getElementById('player-name');
        this.playerLevelElement = document.getElementById('player-level');
        this.locationElement = document.getElementById('current-location');
        this.gameTimeElement = document.getElementById('game-time');

        // Menu buttons
        this.newGameButton = document.getElementById('new-game-btn');
        this.saveGameButton = document.getElementById('save-game-btn');
        this.loadGameButton = document.getElementById('load-game-btn');
        this.settingsButton = document.getElementById('settings-btn');

        // Modal elements
        this.modals = {
            newGame: document.getElementById('new-game-modal'),
            saveGame: document.getElementById('save-game-modal'),
            loadGame: document.getElementById('load-game-modal'),
            settings: document.getElementById('settings-modal'),
            itemInfo: document.getElementById('item-info-modal')
        };

        // Form elements
        this.newPlayerNameInput = document.getElementById('new-player-name');
        this.saveNameInput = document.getElementById('save-name');
        this.savesList = document.getElementById('saves-list');
        this.loadButton = document.getElementById('load-btn');

        // Notification container
        this.notificationContainer = document.getElementById('notification-container');

        // Command history
        this.commandHistory = [];
        this.historyIndex = -1;

        // Settings
        this.settings = {
            theme: localStorage.getItem('rpg_theme') || 'light',
            fontSize: localStorage.getItem('rpg_font_size') || '16',
            llmEnabled: localStorage.getItem('rpg_llm_enabled') === 'true' || false
        };

        // Initialize theme
        this.applyTheme(this.settings.theme);
        
        // Initialize font size
        this.applyFontSize(this.settings.fontSize);
        
        // Track mode transitions for auto-activating combat tab
        this._prevMode = null;
        this._autoCombatShown = false;
        
        // Enforce base layout anchors before loading any saved styles
        this.enforceMainLayoutAnchors();
        this.enforceCenterStackOrder();
        this.applySavedElementStyles();
        this.initStyleToolsBindings();
        // Final enforcement after all styles are loaded
        this.enforceMainLayoutAnchors();
        this.enforceCenterStackOrder();
        this.autoHealLayoutIfCorrupted();
        this.llmSettings = {
            providers: {},
            agents: {}
        };
        
        // This flag is used to block any other code from modifying the model element
        this.isUpdatingModelOptions = false;
        
        // Set up MutationObserver to prevent INPUT elements being created
        this.setupMutationObserver();

        // Apply background from server assets (matches Py GUI backgrounds)
        this.applyBackgroundFromServer();
    }
    
    // NEW FUNCTION: Prevent other code from replacing SELECT with INPUT
    setupMutationObserver() {
        // Create a MutationObserver to monitor for changes to the DOM
        this.observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                // Only act if we're not currently updating model options ourselves
                if (!this.isUpdatingModelOptions) {
                    if (mutation.type === 'childList') {
                        // Check if any INPUTs have been added with ID ending in -model
                        Array.from(mutation.addedNodes).forEach(node => {
                            if (node.nodeType === 1 && node.tagName === 'INPUT' && node.id && node.id.endsWith('-model')) {
                                console.log(`Detected INPUT added for ${node.id}, converting back to SELECT`);
                                const agent = node.id.split('-')[0];
                                const provider = document.getElementById(`${agent}-provider`)?.value || 'OPENAI';
                                
                                // Force create a SELECT to replace the INPUT
                                this.forceCreateSelect(agent, provider, node.value);
                            }
                        });
                    }
                    
                    // Also check if attributes have changed on model elements
                    if (mutation.type === 'attributes' && 
                        mutation.attributeName === 'type' && 
                        mutation.target.id && 
                        mutation.target.id.endsWith('-model')) {
                        
                        if (mutation.target.type === 'text') {
                            console.log(`Detected model element changed to INPUT type for ${mutation.target.id}`);
                            const agent = mutation.target.id.split('-')[0];
                            const provider = document.getElementById(`${agent}-provider`)?.value || 'OPENAI';
                            
                            // Force create a SELECT to replace the INPUT
                            this.forceCreateSelect(agent, provider, mutation.target.value);
                        }
                    }
                }
            });
        });
        
        // Start observing the entire document
        this.observer.observe(document.body, { 
            childList: true, 
            subtree: true,
            attributes: true,
            attributeFilter: ['type']
        });
    }
    
    // NEW FUNCTION: Force create a SELECT element to replace an INPUT
    forceCreateSelect(agent, provider, currentValue = '') {
        // Set flag to prevent observer from acting
        this.isUpdatingModelOptions = true;
        
        try {
            // Find the model form group
            const modelElement = document.getElementById(`${agent}-model`);
            if (!modelElement) {
                console.error(`Cannot find model element for ${agent}`);
                return;
            }
            
            const modelFormGroup = modelElement.closest('.form-group');
            if (!modelFormGroup) {
                console.error(`Cannot find form group for ${agent} model`);
                return;
            }
            
            // Clear the form group
            modelFormGroup.innerHTML = '';
            
            // Create label
            const label = document.createElement('label');
            label.setAttribute('for', `${agent}-model`);
            label.textContent = 'Model:';
            modelFormGroup.appendChild(label);
            
            // Create SELECT
            const select = document.createElement('select');
            select.id = `${agent}-model`;
            
            // Get models based on provider
            let models = [];
            
            if (provider === 'OPENROUTER') {
                // OpenRouter models
                models = [
                    { value: 'google/gemini-2.0-flash-lite-preview-02-05:free', label: 'Google Gemini 2.0 Flash Lite (Free)' },
                    { value: 'nousresearch/deephermes-3-llama-3-8b-preview:free', label: 'DeepHermes 3 Llama 3 8B (Free)' },
                    { value: 'google/gemini-2.0-pro-exp-02-05:free', label: 'Google Gemini 2.0 Pro (Free)' },
                    { value: 'mistralai/mistral-small-3.1-24b-instruct:free', label: 'Mistral Small 3.1 24B (Free)' },
                    { value: 'google/gemini-2.0-flash-exp:free', label: 'Google Gemini 2.0 Flash (Free)' }
                ];
                
                // Add current value if not empty and not already in the list
                if (currentValue && !models.some(m => m.value === currentValue)) {
                    models.push({ value: currentValue, label: currentValue });
                }
            } else if (provider === 'OPENAI') {
                // OpenAI models
                models = [
                    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                    { value: 'gpt-4o', label: 'GPT-4o' },
                ];
            } else if (provider === 'GOOGLE') {
                // Google models
                models = [
                    { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
                    { value: 'gemini-2.0-pro-latest', label: 'Gemini 2.0 Pro' },
                ];
            } else {
                models = [
                    { value: 'unknown-provider-model', label: 'Select Model' }
                ];
            }
            
            // Add options to the select
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.value;
                option.textContent = model.label;
                select.appendChild(option);
            });
            
            // Set the value if it exists in options
            if (currentValue) {
                const option = Array.from(select.options).find(opt => opt.value === currentValue);
                if (option) {
                    select.value = currentValue;
                }
            }
            
            // Append the select to the form group
            modelFormGroup.appendChild(select);
            
            console.log(`Successfully created SELECT for ${agent} with provider ${provider}`);
        } finally {
            // Reset flag
            this.isUpdatingModelOptions = false;
        }
    }

    /**
     * Initialize UI event listeners
     */
    initEventListeners() {
        // Initialize agent provider change listeners
        const agentNames = ['narrator', 'rule-checker', 'context-evaluator'];
        agentNames.forEach(agent => {
            const providerSelect = document.getElementById(`${agent}-provider`);
            if (providerSelect) {
                providerSelect.addEventListener('change', (e) => {
                    this.updateModelOptionsForAgent(agent, e.target.value);
                });

                // Initialize model options based on current provider selection
                // Use a single flag to prevent duplicate initialization
                if (!window._modelInitialized) {
                    window._modelInitialized = {};
                }
                
                if (!window._modelInitialized[agent]) {
                    window._modelInitialized[agent] = true;
                    setTimeout(() => {
                        this.updateModelOptionsForAgent(agent, providerSelect.value);
                    }, 200);
                }
            }
        });

        // Initialize close buttons on all modals
        document.querySelectorAll('.close-modal, .cancel-btn').forEach(element => {
            element.addEventListener('click', () => {
                this.closeAllModals();
            });
        });

        // Close modal when clicking outside
        window.addEventListener('click', (event) => {
            for (const modalName in this.modals) {
                const modal = this.modals[modalName];
                if (event.target === modal) {
                    this.closeModal(modalName);
                }
            }
        });

        // Initialize settings controls
        if (document.getElementById('theme-select')) {
            document.getElementById('theme-select').addEventListener('change', (e) => {
                this.applyTheme(e.target.value);
            });
        }
        // Background select
        const bgSelect = document.getElementById('background-select');
        if (bgSelect) {
            this.populateBackgroundsSelect();
            bgSelect.addEventListener('change', (e)=>{
                const filename = e.target.value || '';
                if (filename) {
                    document.body.style.setProperty('--bg-image-url', `url("/images/gui/background/${filename}")`);
                    document.body.classList.add('has-bg');
                    localStorage.setItem('rpg_bg_filename', filename);
                } else {
                    localStorage.removeItem('rpg_bg_filename');
                    this.applyBackgroundFromServer();
                }
            });
        }

        // Style Tools: load and bind
        this.applySavedLayoutSettings();
        this.applySavedElementStyles();
        this.initStyleToolsBindings();

        // History for editor actions
        this._history = [];
        this._historyIndex = -1;
        // Internal editor state
        this._resizeHandlesEnabled = false; // true when Resize mode ON; overlay can exist also for Move mode only
        this._editorListenersAttached = false;

        if (document.getElementById('font-size-slider')) {
            const fontSizeSlider = document.getElementById('font-size-slider');
            const fontSizeValue = document.getElementById('font-size-value');

            // Set initial value
            fontSizeSlider.value = this.settings.fontSize;
            fontSizeValue.textContent = `${this.settings.fontSize}px`;

            // Update when slider changes
            fontSizeSlider.addEventListener('input', (e) => {
                const size = e.target.value;
                fontSizeValue.textContent = `${size}px`;
                this.applyFontSize(size);
            });
        }

        if (document.getElementById('save-settings-btn')) {
            document.getElementById('save-settings-btn').addEventListener('click', () => {
                this.saveSettings();
                this.closeAllModals();
                this.showNotification('Settings saved successfully', 'success');
            });
        }

        // Initialize reset settings button
        if (document.getElementById('reset-settings-btn')) {
            document.getElementById('reset-settings-btn').addEventListener('click', () => {
                this.resetAgentSettingsToDefault();
                this.showNotification('Agent settings reset to default values', 'info');
            });
        }

        // Initialize tabs in settings modal
        const tabButtons = document.querySelectorAll('.tab-btn');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.getAttribute('data-tab');
                this.switchTab(targetTab);
            });
        });

        // Initialize right panel tabs (separate namespace to avoid clashing with settings tabs)
        const rpTabButtons = document.querySelectorAll('.right-tabs .rp-tab-btn');
        rpTabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetTab = button.getAttribute('data-tab');
                document.querySelectorAll('.right-tabs .rp-tab-btn').forEach(b => b.classList.remove('active'));
                document.querySelectorAll('.right-tabs .rp-tab-pane').forEach(p => p.classList.remove('active'));
                button.classList.add('active');
                const pane = document.getElementById(targetTab);
                if (pane) {
                    pane.classList.add('active');
                    // Ensure proper scrolling for the newly active tab
                    this.ensureRightPanelScrollable();
                }
            });
        });

        // Initialize password visibility toggles
        const showHideButtons = document.querySelectorAll('.show-hide-btn');
        showHideButtons.forEach(button => {
            button.addEventListener('click', () => {
                const targetId = button.getAttribute('data-target');
                this.togglePasswordVisibility(targetId, button);
            });
        });

        // Initialize LLM toggle
        const llmToggle = document.getElementById('llm-enabled-toggle');
        if (llmToggle) {
            llmToggle.checked = this.settings.llmEnabled;
            llmToggle.addEventListener('change', (e) => {
                this.settings.llmEnabled = e.target.checked;
                localStorage.setItem('rpg_llm_enabled', e.target.checked);

                // Update UI based on LLM toggle state
                const llmProviderSettings = document.getElementById('llm-provider-settings');
                if (llmProviderSettings) {
                    llmProviderSettings.style.opacity = e.target.checked ? '1' : '0.5';
                    llmProviderSettings.style.pointerEvents = e.target.checked ? 'auto' : 'none';
                }
            });

            // Apply initial state
            const llmProviderSettings = document.getElementById('llm-provider-settings');
            if (llmProviderSettings) {
                llmProviderSettings.style.opacity = this.settings.llmEnabled ? '1' : '0.5';
                llmProviderSettings.style.pointerEvents = this.settings.llmEnabled ? 'auto' : 'none';
            }
        }

        // Command history navigation
        this.commandInput.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') {
                if (this.historyIndex < this.commandHistory.length - 1) {
                    this.historyIndex++;
                    this.commandInput.value = this.commandHistory[this.commandHistory.length - 1 - this.historyIndex];
                }
                e.preventDefault();
            } else if (e.key === 'ArrowDown') {
                if (this.historyIndex > 0) {
                    this.historyIndex--;
                    this.commandInput.value = this.commandHistory[this.commandHistory.length - 1 - this.historyIndex];
                } else if (this.historyIndex === 0) {
                    this.historyIndex = -1;
                    this.commandInput.value = '';
                }
                e.preventDefault();
            }
        });

        // Window resize handler to adjust right panel scrolling
        window.addEventListener('resize', () => {
            // Debounce the resize handler
            clearTimeout(this._resizeTimeout);
            this._resizeTimeout = setTimeout(() => {
                this.ensureRightPanelScrollable();
            }, 150);
        });
    }

    /**
     * Enable the command input when a game is active
     */
    enableCommandInput() {
        this.commandInput.disabled = false;
        this.sendButton.disabled = false;
        this.saveGameButton.disabled = false;
    }

    /**
     * Disable the command input when no game is active
     */
    disableCommandInput() {
        this.commandInput.disabled = true;
        this.sendButton.disabled = true;
        this.saveGameButton.disabled = true;
    }

    /**
     * Update the game information display
     * @param {Object} gameInfo - Game information object
     */
    updateGameInfo(gameInfo) {
        if (gameInfo.player) {
            if (gameInfo.player.name) {
                this.playerNameElement.textContent = gameInfo.player.name;
            }
            if (gameInfo.player.level) {
                this.playerLevelElement.textContent = gameInfo.player.level;
            }
        }

        if (gameInfo.location) {
            this.locationElement.textContent = gameInfo.location;
        }

        if (gameInfo.time) {
            this.gameTimeElement.textContent = gameInfo.time;
        }
    }

    /**
     * Add a message to the game output area
     * @param {string} text - The message text
     * @param {string} type - The type of message (system, player, game)
     */
addMessage(text, type = 'game') {
        // Guard: ignore empty
        if (text == null) return;
        const txt = String(text);
        const key = `${type}|${txt}`;
        const now = Date.now();
        // Drop identical messages received within 1500ms window
        // Keep only recent window entries (5s)
        try {
            this._recentMsgKeys = (this._recentMsgKeys || []).filter(e => now - e.ts < 5000);
            const seen = this._recentMsgKeys.find(e => e.key === key && (now - e.ts) < 1500);
            if (seen) return; // skip duplicate burst
            this._recentMsgKeys.push({ key, ts: now });
            if (this._recentMsgKeys.length > 50) this._recentMsgKeys.shift();
        } catch {}

        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.textContent = txt;

        this.outputElement.appendChild(messageElement);
        this.scrollToBottom();
    }

    /**
     * Add a command to the history
     * @param {string} command - The command to add
     */
    addCommandToHistory(command) {
        this.commandHistory.push(command);
        // Limit history to 50 entries
        if (this.commandHistory.length > 50) {
            this.commandHistory.shift();
        }
        this.historyIndex = -1;
    }

    /**
     * Clear the command input
     */
    clearCommandInput() {
        this.commandInput.value = '';
    }

    /**
     * Clear the game output area
     */
    clearOutput() {
        this.outputElement.innerHTML = '';
    }

    /**
     * Scroll the output area to the bottom
     */
    scrollToBottom() {
        // Use requestAnimationFrame for smooth scrolling
        requestAnimationFrame(() => {
            this.outputElement.scrollTop = this.outputElement.scrollHeight;
        });
    }

    /**
     * Scroll a specific element to the bottom (for right panel tabs)
     * @param {HTMLElement} element - The element to scroll
     */
    scrollElementToBottom(element) {
        if (!element) return;
        requestAnimationFrame(() => {
            element.scrollTop = element.scrollHeight;
        });
    }

    /**
     * Ensure an element is visible by scrolling its container if needed
     * @param {HTMLElement} element - The element to make visible
     * @param {HTMLElement} container - The scrollable container (optional)
     */
    scrollIntoView(element, container = null) {
        if (!element) return;
        
        if (container) {
            // Scroll within a specific container
            const elementTop = element.offsetTop;
            const elementBottom = elementTop + element.offsetHeight;
            const containerTop = container.scrollTop;
            const containerBottom = containerTop + container.clientHeight;
            
            if (elementBottom > containerBottom) {
                // Element is below the visible area
                container.scrollTop = elementBottom - container.clientHeight;
            } else if (elementTop < containerTop) {
                // Element is above the visible area
                container.scrollTop = elementTop;
            }
        } else {
            // Use browser's built-in scrollIntoView
            element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    /**
     * Ensure the right panel content is properly scrollable and handle overflow
     */
    ensureRightPanelScrollable() {
        const rightPanel = document.querySelector('.right-panel');
        if (!rightPanel) return;

        // Get the currently active tab pane
        const activePane = rightPanel.querySelector('.rp-tab-pane.active');
        if (!activePane) return;

        // Check if content overflows and adjust scrolling
        requestAnimationFrame(() => {
            const rightPanelHeight = rightPanel.clientHeight;
            const tabButtonsHeight = rightPanel.querySelector('.tab-buttons')?.offsetHeight || 0;
            const availableHeight = rightPanelHeight - tabButtonsHeight - 20; // 20px for padding
            
            // Set max height for the active pane if not already set by CSS variable
            const maxHeight = getComputedStyle(document.documentElement)
                .getPropertyValue('--rp-pane-max');
            
            if (maxHeight === 'none' || !maxHeight) {
                // Only set max height if not controlled by CSS variable
                activePane.style.maxHeight = `${availableHeight}px`;
            }

            // If content is overflowing, ensure scrolling is enabled
            if (activePane.scrollHeight > activePane.clientHeight) {
                activePane.style.overflowY = 'auto';
                // Optional: scroll to a specific element if needed
                // For now, we'll keep the current scroll position
            }
        });
    }

    /**
     * Show a notification
     * @param {string} message - The notification message
     * @param {string} type - The type of notification (success, info, warning, error)
     * @param {number} duration - Duration in milliseconds
     */
    showNotification(message, type = 'info', duration = 3000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;

        const messageSpan = document.createElement('span');
        messageSpan.textContent = message;

        const closeBtn = document.createElement('span');
        closeBtn.className = 'notification-close';
        closeBtn.textContent = '×';
        closeBtn.addEventListener('click', () => {
            this.notificationContainer.removeChild(notification);
        });

        notification.appendChild(messageSpan);
        notification.appendChild(closeBtn);

        this.notificationContainer.appendChild(notification);

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentNode === this.notificationContainer) {
                    this.notificationContainer.removeChild(notification);
                }
            }, duration);
        }
    }

    applySavedLayoutSettings() {
        // Re-anchor layout before applying saved values
        this.enforceMainLayoutAnchors();
        this.enforceCenterStackOrder();
        try {
            const left = localStorage.getItem('rpg_layout_left');
            const right = localStorage.getItem('rpg_layout_right');
            const gap = localStorage.getItem('rpg_layout_gap');
            const rpMax = localStorage.getItem('rpg_rp_max');
            const grid = localStorage.getItem('rpg_grid_enabled') === 'true';
            const gsize = localStorage.getItem('rpg_grid_size');
            const inspector = localStorage.getItem('rpg_dev_inspector_enabled') === 'true';
            const centerH = localStorage.getItem('rpg_center_output_h');
            if (left) document.documentElement.style.setProperty('--left-menu-width', `${parseInt(left,10)}px`);
            if (right) document.documentElement.style.setProperty('--right-panel-width', `${parseInt(right,10)}px`);
            if (gap) document.documentElement.style.setProperty('--content-gap', `${parseInt(gap,10)}px`);
            if (rpMax && parseInt(rpMax,10) > 0) document.documentElement.style.setProperty('--rp-pane-max', `${parseInt(rpMax,10)}px`);
            if (rpMax && parseInt(rpMax,10) === 0) document.documentElement.style.setProperty('--rp-pane-max', `none`);
            if (gsize) document.documentElement.style.setProperty('--grid-size', `${parseInt(gsize,10)}px`);
            if (centerH && parseInt(centerH,10) > 0) {
                document.documentElement.style.setProperty('--center-output-track', `${parseInt(centerH,10)}px`);
            } else {
                document.documentElement.style.setProperty('--center-output-track', `1fr`);
            }
            // Sync inputs if present
            const setVal = (id, val)=>{ const el=document.getElementById(id); if (el && val!=null) el.value = String(val).replace('px',''); };
            setVal('layout-left-width', left||180);
            setVal('layout-right-width', right||420);
            setVal('layout-gap', gap||10);
            setVal('layout-rp-max', rpMax||0);
            setVal('layout-grid-size', gsize||16);
            const gridToggle = document.getElementById('layout-grid-toggle'); if (gridToggle) gridToggle.checked = grid;
            const inspToggle = document.getElementById('layout-debug-toggle'); if (inspToggle) inspToggle.checked = inspector;
            this.toggleGridOverlay(grid);
            this.enableLayoutInspector(inspector);
        } catch (e) { console.warn('applySavedLayoutSettings failed', e); }
    }

    initStyleToolsBindings() {
        const bindNum = (id, cb) => {
            const el = document.getElementById(id);
            if (!el) return;
            el.addEventListener('input', ()=> {
                const v = parseInt(el.value, 10);
                cb(isNaN(v)?0:v);
            });
        };
        bindNum('layout-left-width', (v)=>{ document.documentElement.style.setProperty('--left-menu-width', `${v}px`); localStorage.setItem('rpg_layout_left', v); });
        bindNum('layout-right-width', (v)=>{ document.documentElement.style.setProperty('--right-panel-width', `${v}px`); localStorage.setItem('rpg_layout_right', v); });
        bindNum('layout-gap', (v)=>{ document.documentElement.style.setProperty('--content-gap', `${v}px`); localStorage.setItem('rpg_layout_gap', v); });
        bindNum('layout-grid-size', (v)=>{ document.documentElement.style.setProperty('--grid-size', `${v}px`); localStorage.setItem('rpg_grid_size', v); });
        bindNum('layout-rp-max', (v)=>{ if (v>0) { document.documentElement.style.setProperty('--rp-pane-max', `${v}px`); } else { document.documentElement.style.setProperty('--rp-pane-max', `none`); } localStorage.setItem('rpg_rp_max', v); });
        const gridToggle = document.getElementById('layout-grid-toggle');
        if (gridToggle) gridToggle.addEventListener('change', ()=>{ const on=gridToggle.checked; localStorage.setItem('rpg_grid_enabled', on); this.toggleGridOverlay(on); });
        const inspToggle = document.getElementById('layout-debug-toggle');
        if (inspToggle) inspToggle.addEventListener('change', ()=>{ const on=inspToggle.checked; localStorage.setItem('rpg_dev_inspector_enabled', on); this.enableLayoutInspector(on); });
        const editorToggle = document.getElementById('layout-editor-toggle');
        if (editorToggle) editorToggle.addEventListener('change', ()=>{ 
            const on = editorToggle.checked;
            // enforce exclusivity: if turning resize ON, turn move OFF
            const moveToggleEl = document.getElementById('layout-move-toggle');
            if (on) {
                if (moveToggleEl) moveToggleEl.checked = false;
                this._moveMode = false;
                localStorage.setItem('rpg_dev_move_enabled', false);
            }
            localStorage.setItem('rpg_dev_editor_enabled', on);
            this._resizeHandlesEnabled = on;
            this.enableElementResizeMode(on); // will keep overlay active if move mode is on
        });
        const moveToggle = document.getElementById('layout-move-toggle');
        if (moveToggle) moveToggle.addEventListener('change', ()=>{ 
            const on = moveToggle.checked; 
            // enforce exclusivity: if turning move ON, turn resize OFF (handles hidden)
            const editorToggleEl = document.getElementById('layout-editor-toggle');
            if (on) {
                if (editorToggleEl) editorToggleEl.checked = false;
                localStorage.setItem('rpg_dev_editor_enabled', false);
                this._resizeHandlesEnabled = false;
            }
            localStorage.setItem('rpg_dev_move_enabled', on); 
            this._moveMode = on; 
            // ensure overlay exists or is removed based on combined state
            this.enableElementResizeMode(this._resizeHandlesEnabled);
            try { this._updateOverlayRef && this._updateOverlayRef(); } catch(e) {} 
        });
        const resetAllBtn = document.getElementById('layout-reset-all');
        if (resetAllBtn) resetAllBtn.addEventListener('click', (e)=>{ e.preventDefault(); this.resetLayoutToDefaults(true); });
        const restoreBtn = document.getElementById('layout-restore-saved');
        if (restoreBtn) restoreBtn.addEventListener('click', (e)=>{ e.preventDefault(); this.restoreFromSavedLayoutSnapshot(); });
        const hardResetBtn = document.getElementById('layout-hard-reset');
        if (hardResetBtn) hardResetBtn.addEventListener('click', (e)=> { e.preventDefault(); this.hardResetLayoutStorage(); location.reload(); });
        // If saved
        let savedEditor = localStorage.getItem('rpg_dev_editor_enabled') === 'true';
        let savedMove = localStorage.getItem('rpg_dev_move_enabled') === 'true';
        // Enforce exclusivity at startup: prefer Resize if both were true
        if (savedEditor && savedMove) { savedMove = false; localStorage.setItem('rpg_dev_move_enabled', false); }
        if (editorToggle) editorToggle.checked = savedEditor;
        if (moveToggle) moveToggle.checked = savedMove;
        this._moveMode = savedMove;
        this._resizeHandlesEnabled = savedEditor;
        this.enableElementResizeMode(savedEditor);
    }

    toggleGridOverlay(show) {
        try {
            let el = document.getElementById('layout-grid-overlay');
            if (show) {
                if (!el) { el = document.createElement('div'); el.id='layout-grid-overlay'; document.body.appendChild(el); }
            } else {
                if (el && el.parentNode) el.parentNode.removeChild(el);
            }
        } catch (e) { /* ignore */ }
    }

    enableLayoutInspector(enable) {
        if (enable) {
            if (!this._inspHover) this._inspHover = document.createElement('div');
            if (!this._inspPanel) this._inspPanel = document.createElement('div');
            this._inspHover.id = 'layout-hover-overlay';
            this._inspPanel.id = 'layout-inspector';
            if (!document.getElementById('layout-hover-overlay')) document.body.appendChild(this._inspHover);
            if (!document.getElementById('layout-inspector')) document.body.appendChild(this._inspPanel);
            // Track editing mode and last target to avoid re-rendering while typing
            if (!this._inspEditingBound) {
                this._inspPanel.addEventListener('focusin', ()=>{ this._inspEditing = true; });
                this._inspPanel.addEventListener('focusout', ()=>{ setTimeout(()=>{ this._inspEditing = false; }, 50); });
                this._inspEditingBound = true;
            }
            const readVars = ()=>{
                const left = getComputedStyle(document.documentElement).getPropertyValue('--left-menu-width').trim();
                const right = getComputedStyle(document.documentElement).getPropertyValue('--right-panel-width').trim();
                const gap = getComputedStyle(document.documentElement).getPropertyValue('--content-gap').trim();
                const rpmax = getComputedStyle(document.documentElement).getPropertyValue('--rp-pane-max').trim();
                const grid = getComputedStyle(document.documentElement).getPropertyValue('--grid-size').trim();
                const toNum = (v)=> v && v !== 'none' ? parseInt(v,10) : 0;
                return { left: toNum(left), right: toNum(right), gap: toNum(gap), rpmax: toNum(rpmax), grid: toNum(grid) };
            };
            const writeHandlers = ()=>{
                const L = this._inspPanel.querySelector('#insp-left');
                const R = this._inspPanel.querySelector('#insp-right');
                const G = this._inspPanel.querySelector('#insp-gap');
                const M = this._inspPanel.querySelector('#insp-rpmax');
                const S = this._inspPanel.querySelector('#insp-grid');
                const bind = (el, cb)=>{ if (!el) return; el.addEventListener('input', ()=>{ const v=parseInt(el.value,10)||0; cb(v); }); };
                bind(L, v=>{ document.documentElement.style.setProperty('--left-menu-width', `${v}px`); localStorage.setItem('rpg_layout_left', v); });
                bind(R, v=>{ document.documentElement.style.setProperty('--right-panel-width', `${v}px`); localStorage.setItem('rpg_layout_right', v); });
                bind(G, v=>{ document.documentElement.style.setProperty('--content-gap', `${v}px`); localStorage.setItem('rpg_layout_gap', v); });
                bind(M, v=>{ if (v>0) { document.documentElement.style.setProperty('--rp-pane-max', `${v}px`); } else { document.documentElement.style.setProperty('--rp-pane-max', `none`); } localStorage.setItem('rpg_rp_max', v); });
                bind(S, v=>{ document.documentElement.style.setProperty('--grid-size', `${v}px`); localStorage.setItem('rpg_grid_size', v); });
            };
            const renderInspector = (target)=>{
                const r = target.getBoundingClientRect();
                Object.assign(this._inspHover.style, { left:`${r.left}px`, top:`${r.top}px`, width:`${r.width}px`, height:`${r.height}px` });
                const cs = getComputedStyle(target);
                const id = target.id?`#${target.id}`:'';
                const cls = target.className?'.'+String(target.className).trim().split(/\s+/).join('.') : '';
                const tag = target.tagName.toLowerCase();
                const vars = readVars();
                this._inspPanel.style.left = `${Math.min(window.innerWidth-380, r.left+8)}px`;
                this._inspPanel.style.top = `${Math.min(window.innerHeight-160, r.top+8)}px`;
                this._inspPanel.innerHTML = `
                    <div style="font-weight:bold; margin-bottom:4px;">${tag}${id}${cls}</div>
                    <div>size: ${Math.round(r.width)}x${Math.round(r.height)} | overflowY: ${cs.overflowY} | maxH: ${cs.maxHeight}</div>
                    <div class="insp-row"><label for="insp-left">Left:</label><input type="number" id="insp-left" min="120" max="640" step="5" value="${vars.left}"><span>px</span></div>
                    <div class="insp-row"><label for="insp-right">Right:</label><input type="number" id="insp-right" min="320" max="800" step="5" value="${vars.right}"><span>px</span></div>
                    <div class="insp-row"><label for="insp-gap">Gap:</label><input type="number" id="insp-gap" min="0" max="24" step="1" value="${vars.gap}"><span>px</span></div>
                    <div class="insp-row"><label for="insp-rpmax">RP Max:</label><input type="number" id="insp-rpmax" min="0" max="1200" step="10" value="${vars.rpmax}"><span>px</span></div>
                    <div class="insp-row"><label for="insp-grid">Grid:</label><input type="number" id="insp-grid" min="4" max="64" step="2" value="${vars.grid}"><span>px</span></div>
                `;
                writeHandlers();
            };
            if (!this._inspHandler) {
                this._inspHandler = (e)=>{
                    try {
                        const target = e.target;
                        if (!target || target.id==='layout-hover-overlay' || target.id==='layout-inspector') return;
                        const r = target.getBoundingClientRect();
                        // Always update hover box position
                        Object.assign(this._inspHover.style, { left:`${r.left}px`, top:`${r.top}px`, width:`${r.width}px`, height:`${r.height}px` });
                        // Only re-render content when target changes and not editing/locked
                        if (this._inspEditing) return;
                        if (this._editorSelected) return; // locked via right-click
                        if (this._inspLastTarget !== target) {
                            this._inspLastTarget = target;
                            renderInspector(target);
                        } else {
                            // Still keep panel following cursor
                            this._inspPanel.style.left = `${Math.min(window.innerWidth-380, r.left+8)}px`;
                            this._inspPanel.style.top = `${Math.min(window.innerHeight-160, r.top+8)}px`;
                        }
                    } catch (err) { /* ignore */ }
                };
            }
            document.addEventListener('mousemove', this._inspHandler);
            // Right-click to lock inspector editing on element (independent of resize/move modes)
            if (!this._inspContextHandler) {
                this._inspContextHandler = (ev)=>{
                    try {
                        const t = ev.target;
                        if (!t || t.closest('#layout-inspector')) return;
                        // If right-clicked on overlay frame, ignore
                        if (t.closest && t.closest('#layout-resize-overlay')) return;
                        if (!this.isEditableTarget(t)) return;
                        ev.preventDefault();
                        this._editorSelected = t;
                        this._selectionSet = [t];
                        this._inspLastTarget = t;
                        renderInspector(t);
                        this.renderInspectorForSelected();
                    } catch {}
                };
            }
            document.addEventListener('contextmenu', this._inspContextHandler);
            if (!this._inspUnlockHandler) {
                this._inspUnlockHandler = (ev)=>{
                    const inside = ev.target && (ev.target.closest('#layout-inspector'));
                    if (!inside) { this._editorSelected = null; /* unlock editing */ }
                };
            }
            document.addEventListener('click', this._inspUnlockHandler);
        } else {
            if (this._inspHandler) document.removeEventListener('mousemove', this._inspHandler);
            if (this._inspContextHandler) document.removeEventListener('contextmenu', this._inspContextHandler);
            if (this._inspUnlockHandler) document.removeEventListener('click', this._inspUnlockHandler);
            const h = document.getElementById('layout-hover-overlay'); if (h) h.remove();
            const p = document.getElementById('layout-inspector'); if (p) p.remove();
            this._inspLastTarget = null; this._inspEditing = false; this._editorSelected = null;
        }
    }

    applySavedElementStyles() {
        try {
            // Prefer the toolbar snapshot if present, otherwise fall back to the direct map
            let incoming = null;
            try {
                const snapRaw = localStorage.getItem('rpg_layout_saved');
                if (snapRaw) {
                    const snap = JSON.parse(snapRaw);
                    if (snap && snap.element_styles && typeof snap.element_styles === 'object') {
                        incoming = snap.element_styles;
                    }
                }
            } catch {}
            if (!incoming) {
                const raw = localStorage.getItem('rpg_element_styles');
                if (!raw) return;
                incoming = JSON.parse(raw);
            }
            const sanitized = {};
            Object.entries(incoming || {}).forEach(([selector, styles])=>{
                try {
                    document.querySelectorAll(selector).forEach(el=>{
                        const filtered = this.filterStylesForElement(el, styles);
                        if (Object.keys(filtered).length) {
                            Object.assign(el.style, filtered);
                            const sel = this.getUniqueSelectorFor(el);
                            if (sel) sanitized[sel] = { ...(sanitized[sel]||{}), ...filtered };
                        }
                    });
                } catch (e) { /* ignore */ }
            });
            // Keep both stores in sync with the sanitized, actually-applied map
            try { localStorage.setItem('rpg_element_styles', JSON.stringify(sanitized)); } catch {}
            try {
                const saved = JSON.parse(localStorage.getItem('rpg_layout_saved') || '{}');
                if (saved && typeof saved === 'object') {
                    saved.element_styles = sanitized;
                    localStorage.setItem('rpg_layout_saved', JSON.stringify(saved));
                }
            } catch {}
            // After applying, enforce anchors again in case any stray positions slipped in
            this.enforceMainLayoutAnchors();
            this.enforceCenterStackOrder();
        } catch (e) { console.warn('applySavedElementStyles failed', e);}        
    }

    // Disallow editing of outer/root containers
    isEditableTarget(el) {
        if (!el) return false;
        const tag = (el.tagName||'').toUpperCase();
        if (tag === 'HTML' || tag === 'BODY') return false;
        // Block app root frames
        if (el.classList && (el.classList.contains('app-container') || el.classList.contains('game-frame'))) return false;
        const gameFrame = document.querySelector('.game-frame');
        if (el === gameFrame) return false;
        return true;
    }

    // Build a stable CSS selector that is reproducible across reloads
    getStableSelector(el) {
        if (!el) return null;
        if (el.id) return `#${el.id}`;
        const parts = [];
        let node = el;
        while (node && node !== document.body && node !== document.documentElement) {
            if (node.id) { parts.unshift(`#${node.id}`); break; }
            const parent = node.parentElement;
            if (!parent) break;
            const tag = node.tagName.toLowerCase();
            // nth-of-type to avoid class name dependence
            const siblingsOfType = Array.from(parent.children).filter(ch => ch.tagName === node.tagName);
            const index = siblingsOfType.indexOf(node) + 1;
            parts.unshift(`${tag}:nth-of-type(${index})`);
            if (parent.classList && (parent.classList.contains('game-frame') || parent.classList.contains('app-container'))) {
                parts.unshift(parent.classList.contains('game-frame') ? '.game-frame' : '.app-container');
                break;
            }
            node = parent;
        }
        return parts.join(' > ');
    }

    getUniqueSelectorFor(el) {
        if (!el) return null;
        if (!this.isEditableTarget(el)) return null;
        return this.getStableSelector(el);
    }

    persistElementStyle(el) {
        try {
            if (!this.isEditableTarget(el)) return;
            const selector = this.getUniqueSelectorFor(el);
            if (!selector) return;
            const raw = localStorage.getItem('rpg_element_styles');
            const map = raw ? JSON.parse(raw) : {};
            map[selector] = map[selector] || {};
            const styles = {};
            const allowProp = (k)=>{
                // Never persist positioning for protected sections or their descendants
                const inMainSection = !!(el.closest('.left-menu, .center-stack, .right-panel, .banner-bar, .status-bar'));
                if (inMainSection && (k==='position' || k==='left' || k==='top' || k==='zIndex' || k==='transform')) return false;
                return true;
            };
            ['width','height','maxHeight','overflowY','position','left','top','zIndex','transform'].forEach(k=>{ if (el.style[k] && allowProp(k)) styles[k] = el.style[k]; });
            map[selector] = { ...map[selector], ...styles };
            localStorage.setItem('rpg_element_styles', JSON.stringify(map));
        } catch (e) { console.warn('persistElementStyle failed', e); }
    }

    // Layout protection helpers
    isProtectedLayoutElement(el) {
        if (!el) return false;
        // Main grid sections
        if (el.classList && (el.classList.contains('left-menu') || el.classList.contains('center-stack') || el.classList.contains('right-panel') || el.classList.contains('banner-bar') || el.classList.contains('status-bar'))) {
            return true;
        }
        // Critical widgets that must retain order and position
        if (el.id === 'game-output' || el.classList?.contains('game-output')) return true;
        if (el.id === 'command-input' || el.classList?.contains('command-input-container')) return true;
        return false;
    }

    filterStylesForElement(el, styles) {
        try {
            const filtered = { ...styles };
            // For main sections and anything inside them, strip absolute positioning/transform
            if (el.closest('.left-menu, .center-stack, .right-panel, .banner-bar, .status-bar')) {
                delete filtered.position;
                delete filtered.left;
                delete filtered.top;
                delete filtered.zIndex;
                delete filtered.transform;
            }
            return filtered;
        } catch { return styles; }
    }

    enforceCenterStackOrder() {
        try {
            const cs = document.querySelector('.center-stack');
            if (!cs) return;
            const out = cs.querySelector('.game-output');
            const inp = cs.querySelector('.command-input-container');
            if (out && inp) {
                if (out.nextElementSibling !== inp) {
                    cs.insertBefore(inp, null); // move to end
                    cs.insertBefore(out, inp); // ensure out before inp
                }
                // Clear any rogue transforms/positions
                [out, inp].forEach(el=>{ try { el.style.position=''; el.style.left=''; el.style.top=''; el.style.transform=''; el.style.zIndex=''; } catch {} });
            }
        } catch {}
    }

    enforceMainLayoutAnchors() {
        try {
            const anchors = [
                document.querySelector('.left-menu'),
                document.querySelector('.center-stack'),
                document.querySelector('.right-panel'),
                document.querySelector('.banner-bar'),
                document.querySelector('.status-bar')
            ].filter(Boolean);
            anchors.forEach(el=>{ try { el.style.position=''; el.style.left=''; el.style.top=''; el.style.transform=''; el.style.zIndex=''; el.style.gridColumn=''; el.style.gridColumnStart=''; el.style.gridColumnEnd=''; } catch {} });
        } catch {}
    }

    hardResetLayoutStorage() {
        try {
            const keys = [
                'rpg_element_styles','rpg_layout_saved','rpg_layout_left','rpg_layout_right','rpg_layout_gap','rpg_rp_max','rpg_grid_size',
                'rpg_dev_inspector_enabled','rpg_dev_editor_enabled','rpg_dev_move_enabled','rpg_grid_enabled'
            ];
            keys.forEach(k=> localStorage.removeItem(k));
            // Reset CSS variables to defaults
            document.documentElement.style.setProperty('--left-menu-width', '180px');
            document.documentElement.style.setProperty('--right-panel-width', '420px');
            document.documentElement.style.setProperty('--content-gap', '10px');
            document.documentElement.style.setProperty('--rp-pane-max', 'none');
            document.documentElement.style.setProperty('--grid-size', '16px');
            // Re-anchor
            this.enforceMainLayoutAnchors();
            this.enforceCenterStackOrder();
        } catch (e) { console.warn('hardResetLayoutStorage failed', e); }
    }

    autoHealLayoutIfCorrupted() {
        try {
            // Only perform once per browser until the next explicit reset
            if (localStorage.getItem('rpg_layout_auto_healed') === 'true') return;
            const left = document.querySelector('.left-menu');
            const center = document.querySelector('.center-stack');
            const right = document.querySelector('.right-panel');
            const out = document.querySelector('.center-stack .game-output');
            const inp = document.querySelector('.center-stack .command-input-container');
            if (!left || !center || !right) return;
            const lr = left.getBoundingClientRect();
            const cr = center.getBoundingClientRect();
            const rr = right.getBoundingClientRect();
            const problems = [];
            // Right panel should be to the right of center
            if (rr.left < cr.left) problems.push('rightPanelLeftOfCenter');
            // Right panel should not massively overlap center (allow small margin)
            if (rr.left < cr.right - 40 && rr.right > cr.left + 40) problems.push('rightPanelOverlapsCenter');
            // Input should be below output
            if (out && inp) {
                const orc = out.getBoundingClientRect();
                const irc = inp.getBoundingClientRect();
                if (irc.top < orc.bottom - 5) problems.push('inputAboveOutput');
            }
            if (problems.length) {
                console.warn('Layout corruption detected:', problems);
                this.hardResetLayoutStorage();
                localStorage.setItem('rpg_layout_auto_healed', 'true');
                // Notify once
                try { this.showNotification('Layout auto-healed to defaults due to corrupted saved layout', 'warning', 5000); } catch {}
            }
        } catch (e) { /* ignore */ }
    }

    // Helper: get current translate offsets from CSS transform
    getCurrentTranslate(el) {
        try {
            const t = getComputedStyle(el).transform || '';
            if (!t || t === 'none') return { tx: 0, ty: 0 };
            if (t.startsWith('matrix3d(')) {
                const vals = t.slice(9, -1).split(',').map(parseFloat);
                return { tx: vals[12] || 0, ty: vals[13] || 0 };
            }
            if (t.startsWith('matrix(')) {
                const vals = t.slice(7, -1).split(',').map(parseFloat);
                return { tx: vals[4] || 0, ty: vals[5] || 0 };
            }
        } catch {}
        return { tx: 0, ty: 0 };
    }

    enableElementResizeMode(enable) {
        // enable controls whether resize handles are enabled; overlay remains active if either resize OR move is enabled
        this._resizeHandlesEnabled = !!enable;
        const wantsActive = this._resizeHandlesEnabled || !!this._moveMode;
        if (wantsActive) {
            if (!this._resizeOverlay) {
                const ov = document.createElement('div');
                ov.id = 'layout-resize-overlay';
                // Drag surface (for move mode)
                const ds = document.createElement('div'); ds.className='drag-surface'; ov.appendChild(ds);
                ['n','s','e','w','ne','nw','se','sw'].forEach(n=>{ const h=document.createElement('div'); h.className=`handle ${n}`; ov.appendChild(h); });
                // Toolbar
                const tb = document.createElement('div');
                tb.className = 'toolbar';
                const unlockBtn = document.createElement('button'); unlockBtn.id = 'resize-unlock-btn'; unlockBtn.textContent='Unlock'; tb.appendChild(unlockBtn);
                const resetWH = document.createElement('button'); resetWH.id = 'resize-resetwh-btn'; resetWH.textContent='Reset WH'; tb.appendChild(resetWH);
                const resetPos = document.createElement('button'); resetPos.id = 'resize-resetpos-btn'; resetPos.textContent='Reset Pos'; tb.appendChild(resetPos);
                const clearSel = document.createElement('button'); clearSel.id = 'resize-clearsel-btn'; clearSel.textContent='Clear Sel'; tb.appendChild(clearSel);
                const undoBtn = document.createElement('button'); undoBtn.id = 'resize-undo-btn'; undoBtn.textContent='Undo'; tb.appendChild(undoBtn);
                const redoBtn = document.createElement('button'); redoBtn.id = 'resize-redo-btn'; redoBtn.textContent='Redo'; tb.appendChild(redoBtn);
                const saveBtn = document.createElement('button'); saveBtn.id = 'resize-save-layout-btn'; saveBtn.textContent='Save Layout'; saveBtn.classList.add('save'); tb.appendChild(saveBtn);
                const restoreBtn = document.createElement('button'); restoreBtn.id = 'resize-restore-layout-btn'; restoreBtn.textContent='Restore'; tb.appendChild(restoreBtn);
                const resetAllBtn = document.createElement('button'); resetAllBtn.id = 'resize-resetall-btn'; resetAllBtn.textContent='Reset All'; resetAllBtn.classList.add('danger'); tb.appendChild(resetAllBtn);
                ov.appendChild(tb);
                document.body.appendChild(ov);
                this._resizeOverlay = ov;
            }
            const getBounds = (els)=>{
                if (!els || !els.length) return null;
                let l=Infinity,t=Infinity,r=-Infinity,b=-Infinity;
                els.forEach(el=>{ const rc=el.getBoundingClientRect(); l=Math.min(l, rc.left); t=Math.min(t, rc.top); r=Math.max(r, rc.right); b=Math.max(b, rc.bottom); });
                return { left:l, top:t, width: r-l, height: b-t };
            };
            const updateOverlay = (elOrEls)=>{
                const els = Array.isArray(elOrEls)? elOrEls : (this._selectionSet && this._selectionSet.length? this._selectionSet : [elOrEls]);
                // Filter out non-editable elements
                const filtered = (els||[]).filter(el=> this.isEditableTarget(el));
                if (!filtered.length) return;
                const rb = getBounds(filtered);
                if (!rb) return;
                Object.assign(this._resizeOverlay.style, { left:`${rb.left}px`, top:`${rb.top}px`, width:`${rb.width}px`, height:`${rb.height}px`, display:'block' });
                
                // Classification of selection for smart handles
                const selectedEl = filtered.length === 1 ? filtered[0] : null;
                const isSidePanel = !!(selectedEl && selectedEl.classList && (selectedEl.classList.contains('left-menu') || selectedEl.classList.contains('right-panel')));
                const isOutput = !!(selectedEl && selectedEl.classList && selectedEl.classList.contains('game-output'));
                const isCore = !!(selectedEl && selectedEl.classList && (selectedEl.classList.contains('left-menu') || selectedEl.classList.contains('right-panel') || selectedEl.classList.contains('center-stack') || selectedEl.classList.contains('banner-bar') || selectedEl.classList.contains('status-bar')));

                // Show controls only when a selection is locked
                const showControls = !!(this._selectionSet && this._selectionSet.length);
                const tb = this._resizeOverlay.querySelector('.toolbar'); if (tb) {
                    tb.style.display = showControls ? 'flex' : 'none';
                    if (showControls) {
                        // Keep toolbar always on-screen using fixed positioning
                        try {
                            tb.style.position = 'fixed';
                            const tbw = tb.offsetWidth || 120;
                            const tbh = tb.offsetHeight || 28;
                            const pad = 8;
                            let left = Math.max(pad, Math.min(window.innerWidth - tbw - pad, rb.left));
                            // Prefer above the box, otherwise place below
                            let top = rb.top - tbh - 6;
                            if (top < pad) top = Math.min(window.innerHeight - tbh - pad, rb.top + rb.height + 6);
                            tb.style.left = `${Math.round(left)}px`;
                            tb.style.top = `${Math.round(top)}px`;
                            tb.style.right = 'auto';
                            tb.style.bottom = 'auto';
                        } catch {}
                    }
                }
                const showHandles = showControls && !!this._resizeHandlesEnabled;
                this._resizeOverlay.querySelectorAll('.handle').forEach(h=> {
                    const dir = [...h.classList].find(c=> c!=='handle') || '';
                    let shouldShow = showHandles;
                    // For side panels, only allow horizontal resizing
                    if (isSidePanel && !['e','w'].includes(dir)) shouldShow = false;
                    // For game output, only allow vertical resizing
                    if (isOutput && !['n','s'].includes(dir)) shouldShow = false;
                    h.style.display = shouldShow ? 'block' : 'none';
                });
                const ds = this._resizeOverlay.querySelector('.drag-surface');
                if (ds) {
                    // For protected/anchored selections, disable move mode entirely
                    if (showControls && this._moveMode && !(isCore || isOutput)) {
                        ds.style.pointerEvents='auto';
                        ds.style.cursor='move';
                    } else {
                        ds.style.pointerEvents='none';
                        ds.style.cursor='default';
                    }
                }
            };
            // expose a refresher so external toggles can re-evaluate pointer events
            this._updateOverlayRef = ()=>{ try { const els = (this._selectionSet && this._selectionSet.length)? this._selectionSet : (this._editorSelected?[this._editorSelected]:null); if (els) updateOverlay(els); } catch(e) {} };
            const onMove = (e)=>{
                // When a selection exists and not dragging, freeze overlay on the selected element
                if (this._editorSelected || this._draggingHandle) return;
                const t = e.target;
                if (!t || t.id==='layout-resize-overlay' || t.closest('#layout-inspector')) return;
                if (!this.isEditableTarget(t)) return;
                this._hoverTarget = t;
                updateOverlay(t);
            };
            // Attach listeners only once
            if (!this._editorListenersAttached) {
                this._onEditorMove = onMove;
                document.addEventListener('mousemove', this._onEditorMove);
            }
            // Activate selection only on right-click (contextmenu)
            this._onEditorContext = (e)=>{
                const t = e.target;
                if (!t || t.closest('#layout-inspector')) return;
                const clickedOverlay = t.closest && t.closest('#layout-resize-overlay');
                // Ignore right-clicks on overlay frame or controls
                if (clickedOverlay) return;
                if (!this.isEditableTarget(t)) return;
                e.preventDefault();
                const ov = this._resizeOverlay;
                if (e.ctrlKey) {
                    this._selectionSet = this._selectionSet || [];
                    const idx = this._selectionSet.indexOf(t);
                    if (idx===-1) this._selectionSet.push(t); else this._selectionSet.splice(idx,1);
                    if (this._selectionSet.length) { this._editorSelected = this._selectionSet[0]; updateOverlay(this._selectionSet); this.renderInspectorForSelected(); }
                    else { this._editorSelected = null; if (ov) ov.style.display='none'; }
                    return;
                }
                // Normal right-click selects a single element
                this._selectionSet = [t];
                this._editorSelected = t;
                updateOverlay(this._selectionSet);
                this.renderInspectorForSelected();
            };
            if (!this._editorListenersAttached) {
                document.addEventListener('contextmenu', this._onEditorContext);
            }
            // expose updater after selection change
            this._updateOverlayRef && this._updateOverlayRef();
            // Drag handles
            const startDrag = (dir, startX, startY)=>{
                if (!this._editorSelected) return;
                
                const el = this._editorSelected;
                if (!this.isEditableTarget(el)) return;

                // Branch: Special handling for side panels
                const isSidePanel = (el.classList.contains('left-menu') || el.classList.contains('right-panel'));
                if (isSidePanel) {
                    const varName = el.classList.contains('left-menu') ? '--left-menu-width' : '--right-panel-width';
                    const storageKey = el.classList.contains('left-menu') ? 'rpg_layout_left' : 'rpg_layout_right';
                    const startW = el.getBoundingClientRect().width;

                    const onMM = (ev)=>{
                        let dx = ev.clientX - startX;
                        let newWidth = dir.includes('w') ? startW - dx : startW + dx;
                        newWidth = Math.max(120, Math.min(800, newWidth)); // Clamp width
                        document.documentElement.style.setProperty(varName, `${Math.round(newWidth)}px`);
                    };
                    const onMU = ()=>{
                        document.removeEventListener('mousemove', onMM);
                        document.removeEventListener('mouseup', onMU);
                        const finalWidth = parseInt(getComputedStyle(document.documentElement).getPropertyValue(varName));
                        localStorage.setItem(storageKey, finalWidth);
                    };
                    document.addEventListener('mousemove', onMM);
                    document.addEventListener('mouseup', onMU);
                    return; // End special handling
                }

                // Branch: Special handling for game output vertical resizing
                if (el.classList.contains('game-output')) {
                    const csEl = document.querySelector('.center-stack');
                    const startH = el.getBoundingClientRect().height;
                    const onMM = (ev)=>{
                        let dy = ev.clientY - startY;
                        let newHeight = dir.includes('n') ? startH - dy : startH + dy;
                        newHeight = Math.max(240, Math.min(1000, newHeight));
                        document.documentElement.style.setProperty('--center-output-track', `${Math.round(newHeight)}px`);
                    };
                    const onMU = ()=>{
                        document.removeEventListener('mousemove', onMM);
                        document.removeEventListener('mouseup', onMU);
                        const v = getComputedStyle(document.documentElement).getPropertyValue('--center-output-track');
                        const px = parseInt(v,10);
                        if (!isNaN(px)) localStorage.setItem('rpg_center_output_h', px);
                    };
                    document.addEventListener('mousemove', onMM);
                    document.addEventListener('mouseup', onMU);
                    return; // End special handling
                }

                // Default handling for all other elements
                const r = el.getBoundingClientRect();
                const startW = r.width; const startH = r.height; const startL = r.left; const startT = r.top;
                // Record action snapshot
                this.beginEditorAction('resize', [el]);
                const onMM = (ev)=>{
                    let dx = ev.clientX - startX; let dy = ev.clientY - startY;
                    let w = startW, h = startH;
                    if (dir.includes('e')) w = Math.max(50, startW + dx);
                    if (dir.includes('s')) h = Math.max(30, startH + dy);
                    if (dir.includes('w')) w = Math.max(50, startW - dx);
                    if (dir.includes('n')) h = Math.max(30, startH - dy);
                    el.style.width = `${Math.round(w)}px`;
                    el.style.height = `${Math.round(h)}px`;
                    this.persistElementStyle(el);
                    const rr = el.getBoundingClientRect();
                    Object.assign(this._resizeOverlay.style, { width:`${rr.width}px`, height:`${rr.height}px` });
                    this.renderInspectorForSelected();
                };
                const onMU = ()=>{ document.removeEventListener('mousemove', onMM); document.removeEventListener('mouseup', onMU); this._draggingHandle = null; this.commitEditorAction(); };
                document.addEventListener('mousemove', onMM);
                document.addEventListener('mouseup', onMU);
                this._draggingHandle = dir;
            };
            this._resizeOverlay.querySelectorAll('.handle').forEach(h=>{
                h.addEventListener('mousedown', (ev)=>{ ev.preventDefault(); ev.stopPropagation(); const cls = [...h.classList].find(c=> c!=='handle'); startDrag(cls, ev.clientX, ev.clientY); });
            });
            // Drag to move (move mode)
            const dragSurface = this._resizeOverlay.querySelector('.drag-surface');
            if (dragSurface) {
                dragSurface.addEventListener('mousedown', (ev)=>{
                    if (!this._moveMode) return; ev.preventDefault(); ev.stopPropagation();
                    const startX = ev.clientX, startY = ev.clientY;
                    let els = (this._selectionSet && this._selectionSet.length)? [...this._selectionSet] : (this._editorSelected?[this._editorSelected]:[]);
                    els = els.filter(el=> this.isEditableTarget(el));
                    if (!els.length) return;
                    // Record action snapshot
                    this.beginEditorAction('move', els);
                    // Precompute rects, containers, and starting transforms
                    const movedSet = new Set(els);
                    const state = els.map(el=>{
                        const rc = el.getBoundingClientRect();
                        const parent = el.parentElement || document.body;
                        const containerRect = parent.getBoundingClientRect();
                        const { tx, ty } = this.getCurrentTranslate(el);
                        // blocker rects = siblings not in movedSet
                        const blockers = [];
                        try {
                            Array.from(parent.children||[]).forEach(ch=>{ if (!movedSet.has(ch) && this.isEditableTarget(ch)) { const r = ch.getBoundingClientRect(); if (r.width>0 && r.height>0) blockers.push({ el: ch, rect: r }); } });
                        } catch {}
                        return { el, startRect: rc, containerRect, startTx: tx, startTy: ty, blockers };
                    });
                    // Compute container clamping once
                    const dxMin = Math.max(...state.map(s=> s.containerRect.left - s.startRect.left));
                    const dxMax = Math.min(...state.map(s=> s.containerRect.right - s.startRect.right));
                    const dyMin = Math.max(...state.map(s=> s.containerRect.top - s.startRect.top));
                    const dyMax = Math.min(...state.map(s=> s.containerRect.bottom - s.startRect.bottom));
                    let lastGoodDx = 0, lastGoodDy = 0;
                    let swapCandidateEl = null;
                    const onMM = (e2)=>{
                        let dx = e2.clientX - startX; let dy = e2.clientY - startY;
                        // Snap-to-grid when Shift is held
                        try {
                            if (e2.shiftKey) {
                                const g = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--grid-size')||'16',10) || 16;
                                dx = Math.round(dx / g) * g;
                                dy = Math.round(dy / g) * g;
                            }
                        } catch {}
                        // Clamp to container
                        dx = Math.max(dxMin, Math.min(dxMax, dx));
                        dy = Math.max(dyMin, Math.min(dyMax, dy));
                        // Check overlap against blockers; if any, revert to last good
                        const intersects = (a,b)=> a.left < b.right && a.right > b.left && a.top < b.bottom && a.bottom > b.top;
                        let ok = true;
                        for (let i=0;i<state.length;i++) {
                            const s = state[i];
                            const nr = { left: s.startRect.left + dx, right: s.startRect.right + dx, top: s.startRect.top + dy, bottom: s.startRect.bottom + dy };
                            for (const br of s.blockers) { if (intersects(nr, br.rect)) { ok = false; if (!swapCandidateEl && i===0) swapCandidateEl = br.el; break; } }
                            if (!ok) break;
                        }
                        if (!ok) { dx = lastGoodDx; dy = lastGoodDy; }
                        else { lastGoodDx = dx; lastGoodDy = dy; }
                        // Apply transforms without changing dimensions
                        state.forEach(s=>{ s.el.style.transform = `translate(${Math.round(s.startTx + dx)}px, ${Math.round(s.startTy + dy)}px)`; this.persistElementStyle(s.el); });
                        updateOverlay(els);
                    };
                    const onMU = ()=>{ 
                        document.removeEventListener('mousemove', onMM); document.removeEventListener('mouseup', onMU);
                        // If we detected a swap candidate for the anchor element, perform a swap of transforms
                        try {
                            if (swapCandidateEl && state && state.length) {
                                const a = state[0];
                                // ensure we track candidate before/after in history
                                if (this._pendingAction) {
                                    const sel = this.getUniqueSelectorFor(swapCandidateEl);
                                    if (sel) {
                                        const beforeSnap = this.captureStylesForElements([swapCandidateEl]);
                                        this._pendingAction.before = { ...(this._pendingAction.before||{}), ...(beforeSnap||{}) };
                                        this._pendingAction.elements.push(sel);
                                    }
                                }
                                // Find candidate rect captured during mousedown
                                let candRect = null;
                                for (const br of a.blockers) { if (br.el === swapCandidateEl) { candRect = br.rect; break; } }
                                const bTxTy = this.getCurrentTranslate(swapCandidateEl);
                                if (candRect) {
                                    const newATx = (a.startTx||0) + (candRect.left - a.startRect.left);
                                    const newATy = (a.startTy||0) + (candRect.top - a.startRect.top);
                                    const newBTx = (bTxTy.tx||0) + (a.startRect.left - candRect.left);
                                    const newBTy = (bTxTy.ty||0) + (a.startRect.top - candRect.top);
                                    a.el.style.transform = `translate(${Math.round(newATx)}px, ${Math.round(newATy)}px)`;
                                    swapCandidateEl.style.transform = `translate(${Math.round(newBTx)}px, ${Math.round(newBTy)}px)`;
                                    this.persistElementStyle(a.el);
                                    this.persistElementStyle(swapCandidateEl);
                                }
                            }
                        } catch {}
                        this.commitEditorAction();
                        // For elements anchored within main sections, never keep transform after drop
                        try {
                            (els||[]).forEach(el=>{ if (el && el.closest && el.closest('.left-menu, .center-stack, .right-panel, .banner-bar, .status-bar')) { el.style.transform=''; this.persistElementStyle(el); } });
                        } catch {}
                    };
                    document.addEventListener('mousemove', onMM);
                    document.addEventListener('mouseup', onMU);
                });
            }
            const unlock = ()=>{ this._editorSelected = null; this._selectionSet = []; if (this._resizeOverlay) { this._resizeOverlay.style.display='none'; const tb=this._resizeOverlay.querySelector('.toolbar'); if (tb) tb.style.display='none'; this._resizeOverlay.querySelectorAll('.handle').forEach(h=> h.style.display='none'); const ds=this._resizeOverlay.querySelector('.drag-surface'); if (ds) { ds.style.pointerEvents='none'; ds.style.cursor='default'; } } };
            const unlockBtn = this._resizeOverlay.querySelector('#resize-unlock-btn'); if (unlockBtn) unlockBtn.addEventListener('click', (e)=>{ e.stopPropagation(); unlock(); });
            const resetBtn = this._resizeOverlay.querySelector('#resize-resetwh-btn'); if (resetBtn) resetBtn.addEventListener('click', (e)=>{ e.stopPropagation(); const targets=(this._selectionSet&&this._selectionSet.length)?this._selectionSet:[this._editorSelected]; const filtered=(targets||[]).filter(el=> this.isEditableTarget(el)); this.beginEditorAction('reset-size', filtered); filtered.forEach(el=>{ if (el){ el.style.width=''; el.style.height=''; this.persistElementStyle(el); } }); this.commitEditorAction(); this.renderInspectorForSelected(); if (this._editorSelected){ const rr=this._editorSelected.getBoundingClientRect(); Object.assign(this._resizeOverlay.style, { width:`${rr.width}px`, height:`${rr.height}px` }); } });
            const resetPosBtn = this._resizeOverlay.querySelector('#resize-resetpos-btn'); if (resetPosBtn) resetPosBtn.addEventListener('click', (e)=>{ e.stopPropagation(); const targets=(this._selectionSet&&this._selectionSet.length)?this._selectionSet:[this._editorSelected]; const filtered=(targets||[]).filter(el=> this.isEditableTarget(el)); this.beginEditorAction('reset-position', filtered); filtered.forEach(el=>{ if (el){ el.style.position=''; el.style.left=''; el.style.top=''; el.style.zIndex=''; el.style.transform=''; this.persistElementStyle(el); } }); this.commitEditorAction(); updateOverlay(filtered.length?filtered:[this._editorSelected]); });
            const clearSelBtn = this._resizeOverlay.querySelector('#resize-clearsel-btn'); if (clearSelBtn) clearSelBtn.addEventListener('click',(e)=>{ e.stopPropagation(); this._selectionSet=[this._editorSelected].filter(Boolean); updateOverlay(this._selectionSet); });
            const undoBtn = this._resizeOverlay.querySelector('#resize-undo-btn'); if (undoBtn) undoBtn.addEventListener('click',(e)=>{ e.stopPropagation(); this.undoEditorAction(); });
            const redoBtn = this._resizeOverlay.querySelector('#resize-redo-btn'); if (redoBtn) redoBtn.addEventListener('click',(e)=>{ e.stopPropagation(); this.redoEditorAction(); });
            const saveBtn = this._resizeOverlay.querySelector('#resize-save-layout-btn'); if (saveBtn) saveBtn.addEventListener('click',(e)=>{ e.stopPropagation(); this.saveCurrentLayoutSnapshot(); this.showNotification('Layout saved','success', 1500); });
            const restoreBtn = this._resizeOverlay.querySelector('#resize-restore-layout-btn'); if (restoreBtn) restoreBtn.addEventListener('click',(e)=>{ e.stopPropagation(); this.restoreFromSavedLayoutSnapshot(); });
            const resetAllBtn = this._resizeOverlay.querySelector('#resize-resetall-btn'); if (resetAllBtn) resetAllBtn.addEventListener('click',(e)=>{ e.stopPropagation(); this.resetLayoutToDefaults(true); });
            // Escape to unlock + shortcuts
            this._onEditorKey = (ev)=>{ 
                if (ev.key === 'Escape') { unlock(); }
                if (ev.ctrlKey && ev.key.toLowerCase()==='z') { ev.preventDefault(); this.undoEditorAction(); }
                if ((ev.ctrlKey && ev.shiftKey && ev.key.toLowerCase()==='z') || (ev.ctrlKey && ev.key.toLowerCase()==='y')) { ev.preventDefault(); this.redoEditorAction(); }
            };
            if (!this._editorListenersAttached) {
                document.addEventListener('keydown', this._onEditorKey);
                this._editorListenersAttached = true;
            }
            // Initialize buttons state
            this.updateUndoRedoButtons();
        } else {
            // Only tear down if move mode is also off
            if (!this._moveMode) {
                if (this._onEditorMove) document.removeEventListener('mousemove', this._onEditorMove);
                if (this._onEditorContext) document.removeEventListener('contextmenu', this._onEditorContext);
                if (this._onEditorKey) document.removeEventListener('keydown', this._onEditorKey);
                this._editorListenersAttached = false;
                const ov = document.getElementById('layout-resize-overlay'); if (ov) ov.remove();
                this._resizeOverlay = null; this._editorSelected = null; this._selectionSet = []; this._hoverTarget = null; this._updateOverlayRef = null;
            } else {
                // Keep overlay for move mode, just hide handles
                if (this._resizeOverlay) this._resizeOverlay.querySelectorAll('.handle').forEach(h=> h.style.display='none');
            }
        }
    }

    // -------- Layout persistence & history helpers --------
    getCurrentLayoutVariables() {
        const cs = getComputedStyle(document.documentElement);
        const toNum = (v)=>{ v=v.trim(); return v && v !== 'none' ? parseInt(v,10) : 0; };
        return {
            left: toNum(cs.getPropertyValue('--left-menu-width')||'0'),
            right: toNum(cs.getPropertyValue('--right-panel-width')||'0'),
            gap: toNum(cs.getPropertyValue('--content-gap')||'0'),
            rpmax: toNum(cs.getPropertyValue('--rp-pane-max')||'0'),
            grid: toNum(cs.getPropertyValue('--grid-size')||'16'),
            center_output: (function(){ const v = cs.getPropertyValue('--center-output-track')||'1fr'; return /px/.test(v)? toNum(v): 0; })()
        };
    }

    // Collect a full snapshot of editable elements, including computed transform if present
    collectAllEditableStyles() {
        const props = ['width','height','maxHeight','overflowY','position','left','top','zIndex','transform','fontSize','fontFamily','fontWeight','textAlign','lineHeight','color','backgroundColor','paddingTop','paddingRight','paddingBottom','paddingLeft'];
        const map = {};
        try {
            const all = Array.from(document.body.querySelectorAll('*'));
            for (const el of all) {
                if (!this.isEditableTarget(el)) continue;
                const selector = this.getUniqueSelectorFor(el);
                if (!selector) continue;
                const styles = {};
                const cs = getComputedStyle(el);
                for (const k of props) {
                    let v = el.style[k];
                    if (!v || v === '') {
                        // If not set inline, capture computed for robustness (fonts/colors/padding/line-height/position, etc.)
                        if (k === 'transform') {
                            const ct = cs.transform; if (ct && ct !== 'none') v = ct;
                        } else {
                            const cv = cs[k]; if (cv && cv !== '' && cv !== 'initial' && cv !== 'auto' && cv !== 'normal' && cv !== 'none') v = cv;
                        }
                    }
                    if (v && v !== '') styles[k] = v;
                }
                if (Object.keys(styles).length > 0) map[selector] = styles;
            }
        } catch (e) { /* ignore */ }
        return map;
    }

    saveCurrentLayoutSnapshot() {
        try {
            const vars = this.getCurrentLayoutVariables();
            const element_styles = this.collectAllEditableStyles();
            const payload = { vars, element_styles, saved_at: Date.now() };
            // 1) Save the snapshot that the toolbar "Restore" uses
            localStorage.setItem('rpg_layout_saved', JSON.stringify(payload));
            // 2) Also update the auto-applied map so a simple reload reflects the new layout
            //    (we store the raw capture here; application time will sanitize if needed)
            try { localStorage.setItem('rpg_element_styles', JSON.stringify(element_styles)); } catch {}
        } catch (e) { console.warn('saveCurrentLayoutSnapshot failed', e); }
    }

    resetLayoutToDefaults(showMsg = true) {
        try {
            // Clear saved element styles and remove inline styles from affected elements
            const raw = localStorage.getItem('rpg_element_styles');
            if (raw) {
                try {
                    const map = JSON.parse(raw);
                    Object.entries(map).forEach(([selector, styles])=>{
                        try {
                            document.querySelectorAll(selector).forEach(el=>{
                                ['width','height','maxHeight','overflowY','position','left','top','zIndex','transform','fontSize','fontFamily','fontWeight','textAlign','lineHeight','color','backgroundColor','paddingTop','paddingRight','paddingBottom','paddingLeft'].forEach(k=>{ el.style[k] = ''; });
                            });
                        } catch { /* ignore */ }
                    });
                } catch { /* ignore */ }
            }
            localStorage.removeItem('rpg_element_styles');
            // Reset CSS variables to defaults as defined in CSS
            document.documentElement.style.setProperty('--left-menu-width', '180px');
            document.documentElement.style.setProperty('--right-panel-width', '420px');
            document.documentElement.style.setProperty('--content-gap', '10px');
            document.documentElement.style.setProperty('--rp-pane-max', 'none');
            document.documentElement.style.setProperty('--grid-size', '16px');
            // Clear saved variable overrides
            ['rpg_layout_left','rpg_layout_right','rpg_layout_gap','rpg_rp_max','rpg_grid_size'].forEach(k=> localStorage.removeItem(k));
            // Turn off editor/move by default
            localStorage.setItem('rpg_dev_editor_enabled', 'false');
            localStorage.setItem('rpg_dev_move_enabled', 'false');
            // Remove overlays
            this.toggleGridOverlay(false);
            this.enableLayoutInspector(false);
            this.enableElementResizeMode(false);
            // Re-anchor layout and restore expected order
            this.enforceMainLayoutAnchors();
            this.enforceCenterStackOrder();
            if (showMsg) this.showNotification('Layout reset to defaults', 'success');
        } catch (e) { console.warn('resetLayoutToDefaults failed', e); }
    }

    captureStylesForElements(els) {
        const snap = {};
        els.forEach(el=>{
            if (!this.isEditableTarget(el)) return;
            const selector = this.getUniqueSelectorFor(el);
            if (!selector) return;
            snap[selector] = {};
            ['width','height','maxHeight','overflowY','position','left','top','zIndex','transform','fontSize','fontFamily','fontWeight','textAlign','lineHeight','color','backgroundColor','paddingTop','paddingRight','paddingBottom','paddingLeft'].forEach(k=>{ if (el.style[k]) snap[selector][k] = el.style[k]; });
        });
        return snap;
    }

    applySnapshot(snap) {
        Object.entries(snap||{}).forEach(([selector, styles])=>{
            try {
                document.querySelectorAll(selector).forEach(el=>{ Object.assign(el.style, styles||{}); this.persistElementStyle(el); });
            } catch { /* ignore */ }
        });
    }

    beginEditorAction(label, els) {
        try {
            const elements = (els||[]).filter(Boolean);
            this._pendingAction = { label, before: this.captureStylesForElements(elements), elements: elements.map(el=> this.getUniqueSelectorFor(el)) };
        } catch { this._pendingAction = null; }
    }

    commitEditorAction() {
        if (!this._pendingAction) { this.updateUndoRedoButtons(); return; }
        try {
            const after = {};
            (this._pendingAction.elements||[]).forEach(sel=>{
                document.querySelectorAll(sel).forEach(el=>{
                    after[sel] = after[sel] || {};
                    ['width','height','maxHeight','overflowY','position','left','top','zIndex','transform','fontSize','fontFamily','fontWeight','textAlign','lineHeight','color','backgroundColor','paddingTop','paddingRight','paddingBottom','paddingLeft'].forEach(k=>{ if (el.style[k]) after[sel][k] = el.style[k]; });
                });
            });
            const action = { label: this._pendingAction.label, before: this._pendingAction.before, after };
            // Truncate any redo tail
            if (this._historyIndex < this._history.length - 1) this._history = this._history.slice(0, this._historyIndex + 1);
            this._history.push(action);
            this._historyIndex = this._history.length - 1;
        } finally {
            this._pendingAction = null;
            this.updateUndoRedoButtons();
        }
    }

    undoEditorAction() {
        if (this._historyIndex < 0) return;
        const action = this._history[this._historyIndex];
        this.applySnapshot(action.before);
        this._historyIndex--;
        this.updateUndoRedoButtons();
    }

    redoEditorAction() {
        if (this._historyIndex >= this._history.length - 1) return;
        this._historyIndex++;
        const action = this._history[this._historyIndex];
        this.applySnapshot(action.after);
        this.updateUndoRedoButtons();
    }

    updateUndoRedoButtons() {
        try {
            const ov = this._resizeOverlay;
            if (!ov) return;
            const canUndo = this._historyIndex >= 0;
            const canRedo = this._historyIndex < this._history.length - 1;
            const u = ov.querySelector('#resize-undo-btn'); if (u) u.disabled = !canUndo;
            const r = ov.querySelector('#resize-redo-btn'); if (r) r.disabled = !canRedo;
        } catch { /* ignore */ }
    }

    restoreFromSavedLayoutSnapshot() {
        try {
            const raw = localStorage.getItem('rpg_layout_saved');
            if (!raw) { this.showNotification('No saved snapshot found','warning'); return; }
            const saved = JSON.parse(raw);
            const v = saved.vars || {};
            const setVar = (name, val)=>{ 
                if (name==='--rp-pane-max') {
                    if (val && parseInt(val,10)>0) document.documentElement.style.setProperty(name, `${parseInt(val,10)}px`); 
                    else document.documentElement.style.setProperty(name, 'none'); 
                } else if (name==='--center-output-track') {
                    if (val && parseInt(val,10)>0) document.documentElement.style.setProperty(name, `${parseInt(val,10)}px`);
                    else document.documentElement.style.setProperty(name, '1fr');
                } else if (val!=null) { 
                    document.documentElement.style.setProperty(name, `${parseInt(val,10)}px`); 
                } 
            };
            setVar('--left-menu-width', v.left||180);
            setVar('--right-panel-width', v.right||420);
            setVar('--content-gap', v.gap||10);
            setVar('--rp-pane-max', v.rpmax||0);
            setVar('--grid-size', v.grid||16);
            setVar('--center-output-track', v.center_output||0);
            localStorage.setItem('rpg_layout_left', v.left||180);
            localStorage.setItem('rpg_layout_right', v.right||420);
            localStorage.setItem('rpg_layout_gap', v.gap||10);
            localStorage.setItem('rpg_rp_max', v.rpmax||0);
            localStorage.setItem('rpg_grid_size', v.grid||16);
            const map = saved.element_styles || {};
            localStorage.setItem('rpg_element_styles', JSON.stringify(map));
            // Clear inline styles for known edited elements and reapply
            try { Object.keys(map).forEach(sel=>{ document.querySelectorAll(sel).forEach(el=>{ ['width','height','maxHeight','overflowY','position','left','top','zIndex','transform','fontSize','fontFamily','fontWeight','textAlign','lineHeight','color','backgroundColor','paddingTop','paddingRight','paddingBottom','paddingLeft'].forEach(k=>{ el.style[k]=''; }); }); }); } catch(e) {}
            Object.entries(map).forEach(([selector, styles])=>{ try { document.querySelectorAll(selector).forEach(el=>{ Object.assign(el.style, styles||{}); }); } catch(e) {} });
            this.applySavedLayoutSettings();
            if (this._updateOverlayRef) this._updateOverlayRef();
            this.showNotification('Layout restored from saved snapshot','success');
        } catch (e) { console.warn('restoreFromSavedLayoutSnapshot failed', e); this.showNotification('Failed to restore layout','error'); }
    }

    rgbToHex(rgb) {
        try {
            if (!rgb) return '#000000';
            if (rgb.startsWith('#')) return rgb;
            const m = rgb.match(/rgba?\((\d+),\s*(\d+),\s*(\d+)/i);
            if (!m) return '#000000';
            const toHex = (n)=> ('0'+(parseInt(n,10)||0).toString(16)).slice(-2);
            return `#${toHex(m[1])}${toHex(m[2])}${toHex(m[3])}`;
        } catch { return '#000000'; }
    }

    renderInspectorForSelected() {
        if (!this._editorSelected || !this._inspPanel) return;
        try {
            const el = this._editorSelected;
            const r = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            const id = el.id?`#${el.id}`:''; const cls = el.className?'.'+String(el.className).trim().split(/\s+/).join('.') : '';
            const tag = el.tagName.toLowerCase();
            const w = parseInt(cs.width,10)||Math.round(r.width); const h = parseInt(cs.height,10)||Math.round(r.height);
            const ov = cs.overflowY || 'visible'; const mh = cs.maxHeight || 'none';
            const base = this._inspPanel.innerHTML;
            // Append editor controls if not already present
            if (!this._inspPanel.querySelector('#insp-el-width')) {
                this._inspPanel.innerHTML = base + `
                    <hr style=\"opacity:0.4;margin:6px 0;\">
                    <div style=\"font-weight:bold;margin-bottom:4px;\">Selected: ${tag}${id}${cls}</div>
                    <div class=\"insp-row\"><label for=\"insp-el-width\">Width:</label><input type=\"number\" id=\"insp-el-width\" min=\"50\" max=\"2000\" step=\"1\" value=\"${w}\"><span>px</span></div>
                    <div class=\"insp-row\"><label for=\"insp-el-height\">Height:</label><input type=\"number\" id=\"insp-el-height\" min=\"30\" max=\"2000\" step=\"1\" value=\"${h}\"><span>px</span></div>
                    <div class=\"insp-row\"><label for=\"insp-el-maxh\">MaxH:</label><input type=\"number\" id=\"insp-el-maxh\" min=\"0\" max=\"4000\" step=\"10\" value=\"${mh==='none'?0:parseInt(mh,10)||0}\"><span>px</span></div>
                    <div class=\"insp-row\"><label for=\"insp-el-over\">Overflow:</label><input type=\"text\" id=\"insp-el-over\" value=\"${ov}\"></div>
                    <div class=\"insp-row\"><button id=\"insp-el-reset\" class=\"cancel-btn\">Reset</button></div>
                    <hr style=\"opacity:0.3;margin:6px 0;\">
                    <div style=\"font-weight:bold;margin-bottom:4px;\">Typography & Colors</div>
                    <div class=\"insp-row\"><label for=\"insp-font-size\">Font Size:</label><input type=\"number\" id=\"insp-font-size\" min=\"8\" max=\"64\" step=\"1\" value=\"${parseInt(cs.fontSize,10)||14}\"><span>px</span></div>
                    <div class=\"insp-row\"><label for=\"insp-font-family\">Font:</label><input type=\"text\" id=\"insp-font-family\" list=\"font-family-list\" value=\"${(cs.fontFamily||'').replace(/\"/g,'&quot;')}\"></div>
                    <datalist id=\"font-family-list\">${[
                        "system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif",
                        "Segoe UI, Tahoma, Geneva, Verdana, sans-serif",
                        "Roboto, system-ui, -apple-system, Segoe UI, sans-serif",
                        "Inter, system-ui, -apple-system, Segoe UI, sans-serif",
                        "Open Sans, Segoe UI, Verdana, sans-serif",
                        "Lato, Segoe UI, Verdana, sans-serif",
                        "Montserrat, Segoe UI, Verdana, sans-serif",
                        "Nunito, Segoe UI, Verdana, sans-serif",
                        "Poppins, Segoe UI, Verdana, sans-serif",
                        "Garamond, 'Palatino Linotype', Palatino, serif",
                        "Georgia, 'Times New Roman', Times, serif",
                        "Times New Roman, Times, serif",
                        "Palatino Linotype, Book Antiqua, Palatino, serif",
                        "Trebuchet MS, Helvetica, sans-serif",
                        "Lucida Grande, Lucida Sans Unicode, Lucida Sans, Geneva, Verdana, sans-serif",
                        "Courier New, Courier, monospace",
                        "Consolas, 'Liberation Mono', Menlo, monospace"
                    ].map(f=>`<option value=\"${f.replace(/\"/g,'&quot;')}\"></option>`).join('')}</datalist>
                    <div class=\"insp-row\"><label for=\"insp-font-weight\">Weight:</label><select id=\"insp-font-weight\"><option value=\"normal\">normal</option><option value=\"bold\">bold</option><option value=\"100\">100</option><option value=\"200\">200</option><option value=\"300\">300</option><option value=\"400\">400</option><option value=\"500\">500</option><option value=\"600\">600</option><option value=\"700\">700</option><option value=\"800\">800</option><option value=\"900\">900</option></select></div>
                    <div class=\"insp-row\"><label for=\"insp-text-align\">Text Align:</label><select id=\"insp-text-align\"><option value=\"left\">left</option><option value=\"center\">center</option><option value=\"right\">right</option></select></div>
                    <div class=\"insp-row\"><label for=\"insp-line-height\">Line Height:</label><input type=\"number\" id=\"insp-line-height\" min=\"0\" max=\"400\" step=\"1\" value=\"${parseInt(cs.lineHeight,10)||0}\"><span>px</span></div>
                    <div class=\"insp-row\"><label for=\"insp-color\">Text Color:</label><input type=\"color\" id=\"insp-color\" value=\"${this.rgbToHex(cs.color||'#000000')}\"></div>
                    <div class=\"insp-row\"><label for=\"insp-bgcolor\">Background:</label><input type=\"color\" id=\"insp-bgcolor\" value=\"${this.rgbToHex(cs.backgroundColor||'#000000')}\"></div>
                    <div class=\"insp-row\"><label>Padding:</label>
                        <input type=\"number\" id=\"insp-pad-top\" style=\"width:60px\" value=\"${parseInt(cs.paddingTop,10)||0}\" title=\"Top\"> 
                        <input type=\"number\" id=\"insp-pad-right\" style=\"width:60px\" value=\"${parseInt(cs.paddingRight,10)||0}\" title=\"Right\"> 
                        <input type=\"number\" id=\"insp-pad-bottom\" style=\"width:60px\" value=\"${parseInt(cs.paddingBottom,10)||0}\" title=\"Bottom\"> 
                        <input type=\"number\" id=\"insp-pad-left\" style=\"width:60px\" value=\"${parseInt(cs.paddingLeft,10)||0}\" title=\"Left\">
                        <span>px</span>
                    </div>
                `;
                const wI = this._inspPanel.querySelector('#insp-el-width');
                const hI = this._inspPanel.querySelector('#insp-el-height');
                const mI = this._inspPanel.querySelector('#insp-el-maxh');
                const oI = this._inspPanel.querySelector('#insp-el-over');
                const resetBtn = this._inspPanel.querySelector('#insp-el-reset');
                const bind = (elInput, cssProp, parse=(v)=>v+"px")=>{
                    if (!elInput) return; 
                    elInput.addEventListener('focusin', ()=>{ this.beginEditorAction('insp-edit', [el]); });
                    elInput.addEventListener('input', ()=>{ let v = elInput.value; if (cssProp==='maxHeight' && (v===0 || v==='0')) { el.style.maxHeight = ''; } else { el.style[cssProp] = (cssProp==='overflowY' || cssProp==='fontFamily' || cssProp==='fontWeight' || cssProp==='textAlign' || cssProp==='color' || cssProp==='backgroundColor')? v : `${parseInt(v,10)||0}px`; } this.persistElementStyle(el); });
                    elInput.addEventListener('focusout', ()=>{ this.commitEditorAction(); });
                };
                bind(wI,'width'); bind(hI,'height'); bind(mI,'maxHeight');
                if (oI) { oI.addEventListener('focusin', ()=>{ this.beginEditorAction('insp-edit', [el]); }); oI.addEventListener('input', ()=>{ el.style.overflowY = oI.value||''; this.persistElementStyle(el); }); oI.addEventListener('focusout', ()=>{ this.commitEditorAction(); }); }
                if (resetBtn) resetBtn.addEventListener('click', ()=>{ this.beginEditorAction('insp-reset', [el]); el.style.width=''; el.style.height=''; el.style.maxHeight=''; el.style.overflowY=''; this.persistElementStyle(el); this.commitEditorAction(); });
                // Typography & colors bindings
                const fsI = this._inspPanel.querySelector('#insp-font-size'); bind(fsI,'fontSize');
                const ffI = this._inspPanel.querySelector('#insp-font-family'); bind(ffI,'fontFamily');
                const fwI = this._inspPanel.querySelector('#insp-font-weight'); if (fwI) { fwI.value = cs.fontWeight || 'normal'; bind(fwI,'fontWeight'); }
                const taI = this._inspPanel.querySelector('#insp-text-align'); if (taI) { taI.value = cs.textAlign || 'left'; bind(taI,'textAlign'); }
                const lhI = this._inspPanel.querySelector('#insp-line-height'); bind(lhI,'lineHeight');
                const colorI = this._inspPanel.querySelector('#insp-color'); if (colorI) { colorI.addEventListener('input', ()=>{ el.style.color = colorI.value; this.persistElementStyle(el); }); }
                const bgI = this._inspPanel.querySelector('#insp-bgcolor'); if (bgI) { bgI.addEventListener('input', ()=>{ el.style.backgroundColor = bgI.value; this.persistElementStyle(el); }); }
                const ptI = this._inspPanel.querySelector('#insp-pad-top'); bind(ptI,'paddingTop');
                const prI = this._inspPanel.querySelector('#insp-pad-right'); bind(prI,'paddingRight');
                const pbI = this._inspPanel.querySelector('#insp-pad-bottom'); bind(pbI,'paddingBottom');
                const plI = this._inspPanel.querySelector('#insp-pad-left'); bind(plI,'paddingLeft');
            }
        } catch (e) { /* ignore */ }
    }

    /**
     * Open a modal dialog
     * @param {string} modalName - The name of the modal to open
     */
    openModal(modalName) {
        this.closeAllModals();

        if (this.modals[modalName]) {
            this.modals[modalName].classList.add('active');

            // Focus first input in modal, if any
            const firstInput = this.modals[modalName].querySelector('input, select, button');
            if (firstInput) {
                firstInput.focus();
            }
        }
    }

    /**
     * Close a specific modal
     * @param {string} modalName - The name of the modal to close
     */
    closeModal(modalName) {
        if (this.modals[modalName]) {
            this.modals[modalName].classList.remove('active');
        }
    }

    /**
     * Close all modals
     */
    closeAllModals() {
        for (const modalName in this.modals) {
            this.closeModal(modalName);
        }
    }

    /**
     * Populate the saves list in the load game modal
     * @param {Array} saves - Array of save objects
     */
    populateSavesList(saves) {
        this.savesList.innerHTML = '';

        if (!saves || saves.length === 0) {
            const message = document.createElement('div');
            message.className = 'no-saves';
            message.textContent = 'No saved games found.';
            this.savesList.appendChild(message);
            this.loadButton.disabled = true;
            return;
        }

        this.loadButton.disabled = true;
        let selectedSaveId = null;

        saves.forEach(save => {
            const saveItem = document.createElement('div');
            saveItem.className = 'save-item';
            saveItem.dataset.saveId = save.save_id;

            const header = document.createElement('div');
            header.className = 'save-item-header';

            const name = document.createElement('div');
            name.className = 'save-item-name';
            name.textContent = save.save_name;

            const time = document.createElement('div');
            time.className = 'save-item-time';
            time.textContent = save.formatted_save_time || new Date(save.save_time * 1000).toLocaleString();

            header.appendChild(name);
            header.appendChild(time);

            const details = document.createElement('div');
            details.className = 'save-item-details';
            details.textContent = `${save.player_name} (Level ${save.player_level}) - ${save.location}`;

            saveItem.appendChild(header);
            saveItem.appendChild(details);

            // Add click event to select the save
            saveItem.addEventListener('click', () => {
                // Remove selection from all saves
                document.querySelectorAll('.save-item').forEach(item => {
                    item.classList.remove('selected');
                });

                // Select this save
                saveItem.classList.add('selected');
                selectedSaveId = save.save_id;
                this.loadButton.disabled = false;
            });

            this.savesList.appendChild(saveItem);
        });

        // Set up load button to return the selected save
        this.loadButton.onclick = () => {
            if (selectedSaveId) {
                const event = new CustomEvent('load-save', {
                    detail: { saveId: selectedSaveId }
                });
                document.dispatchEvent(event);
                this.closeAllModals();
            }
        };
    }

    /**
     * Apply a theme to the UI
     * @param {string} theme - The theme name
     */
    applyTheme(theme) {
        document.body.classList.remove('light-theme', 'dark-theme', 'fantasy-theme');
        document.body.classList.add(`${theme}-theme`);
        this.settings.theme = theme;

        // Update theme selector if it exists
        const themeSelect = document.getElementById('theme-select');
        if (themeSelect) {
            themeSelect.value = theme;
        }

        localStorage.setItem('rpg_theme', theme);
    }

    async populateBackgroundsSelect() {
        try {
            const resp = await fetch('/api/ui/backgrounds');
            if (!resp.ok) return;
            const data = await resp.json();
            const select = document.getElementById('background-select');
            if (!select) return;
            const saved = localStorage.getItem('rpg_bg_filename') || '';
            (data.backgrounds||[]).forEach(fn=>{
                const opt = document.createElement('option');
                opt.value = fn;
                opt.textContent = fn;
                select.appendChild(opt);
            });
            if (saved) select.value = saved;
        } catch (e) { /* ignore */ }
    }

    /** Render the right panel using UI state */
    renderRightPanel(ui) {
        // Ensure combat tab presence if in combat mode
        if ((ui.mode||'').toUpperCase() === 'COMBAT') {
            this.ensureCombatTab();
        }
        // Character tab content
        const charPane = document.getElementById('tab-character');
        if (charPane) {
            const res = ui.resources || {};
            const bar = (name, key, color) => {
                const r = res[key] || { current: 0, max: 0 };
                const pct = r.max ? Math.min(100, (r.current / r.max) * 100) : 0;
                return `<div class=\"rp-bar\" data-bar-type=\"${key}\">
                    <div class=\"rp-bar-title\" data-bar-type=\"${key}\">${name}: ${Math.round(r.current)}/${Math.round(r.max)}</div>
                    <div class=\"rp-bar-track\"><div class=\"rp-bar-fill\" data-bar-type=\"${key}\" style=\"width:${pct}%; background:${color}\"></div></div>
                </div>`;
            };
            const statList = (title, dict) => {
                const rows = Object.keys(dict||{}).map(k=>{
                    const s=dict[k];
                    return `<div class=\"rp-row stat-row\" data-stat-key=\"${k}\"><span>${s.name||k}</span><span>${Math.round(s.value)}</span></div>`;
                }).join('');
                return `<div class=\"rp-group\"><div class=\"rp-title\">${title}</div>${rows||'<div class=\"rp-empty\">—</div>'}</div>`;
            };
            const statusRows = (ui.status_effects||[]).map(e=>`<div class="rp-row"><span>${e.name}</span><span>${e.duration??''}</span></div>`).join('');
            const turnRows = (ui.turn_order||[]).map(t=>`<div class="rp-row"><span>${t}</span></div>`).join('');
            const initiativeVal = (ui.initiative==null||ui.initiative===undefined)?'0':Math.round(ui.initiative);
            
            // Build paperdoll
            const paperdollHtml = this.renderPaperdoll(ui);
            charPane.innerHTML = `
                <div class="rp-header">
                    <div class="rp-name">${ui.player.name}</div>
                    <div class="rp-sub">Race: ${ui.player.race} | Class: ${ui.player.path}</div>
                    <div class="rp-sub">Level: ${ui.player.level} | Experience: ${ui.player.experience_current}/${ui.player.experience_max}</div>
                </div>
                ${bar('Health', 'health', '#CC3333')}
                ${bar('Mana', 'mana', '#3366CC')}
                ${bar('Stamina', 'stamina', '#66CC33')}
                <div class="rp-columns">
                    <div class="rp-col">${statList('Primary Stats', ui.primary_stats)}</div>
                    <div class="rp-col">${statList('Derived Stats', ui.derived_stats)}</div>
                </div>
                <div class="rp-columns">
                    <div class="rp-col">${statList('Social', ui.social_stats)}</div>
                    <div class="rp-col">${statList('Other', ui.other_stats)}</div>
                </div>
                <div class="rp-group"><div class="rp-title">Combat Info</div>
                    <div class="rp-row"><span>Initiative</span><span>${initiativeVal}</span></div>
                    <div class="rp-subtitle">Status Effects</div>${statusRows||'<div class="rp-empty">—</div>'}
                    <div class="rp-subtitle">Turn Order</div>${turnRows||'<div class="rp-empty">—</div>'}
                </div>
                ${paperdollHtml}
            `;
            // Attach character tab handlers (context menus, tooltips, paperdoll)
            this.attachCharacterTabHandlers();
            this.attachPaperdollHandlers();
        }
        // Inventory tab
        const invPane = document.getElementById('tab-inventory');
        if (invPane) {
            this.renderInventoryPane();
        }
        // Journal tab
        const jPane = document.getElementById('tab-journal');
        if (jPane) {
            this.renderJournalPane(ui);
        }
        
        // Auto-scroll the active right panel tab if content overflows
        this.ensureRightPanelScrollable();
    }

    // Ensure the 'Combat' tab exists in the right panel
    ensureCombatTab() {
        try {
            const tabs = document.querySelector('.right-tabs');
            if (!tabs) return;
            const btnRow = tabs.querySelector('.tab-buttons');
            const content = tabs.querySelector('.tab-content');
            if (!btnRow || !content) return;
            let btn = btnRow.querySelector('[data-tab="tab-combat"]');
            let pane = document.getElementById('tab-combat');
            if (!btn) {
                btn = document.createElement('button');
                btn.className = 'rp-tab-btn';
                btn.setAttribute('data-tab', 'tab-combat');
                btn.textContent = 'Combat';
                btnRow.insertBefore(btn, btnRow.firstChild); // put Combat first
                // wire click like others
                btn.addEventListener('click', () => {
                    document.querySelectorAll('.right-tabs .rp-tab-btn').forEach(b => b.classList.remove('active'));
                    document.querySelectorAll('.right-tabs .rp-tab-pane').forEach(p => p.classList.remove('active'));
                    btn.classList.add('active');
                    const pane = document.getElementById('tab-combat');
                    if (pane) pane.classList.add('active');
                    this.ensureRightPanelScrollable();
                });
            }
            if (!pane) {
                pane = document.createElement('div');
                pane.className = 'rp-tab-pane';
                pane.id = 'tab-combat';
                pane.innerHTML = '<div class="placeholder">Combat log</div>';
                content.insertBefore(pane, content.firstChild);
            }
        } catch (e) { /* ignore */ }
    }

    // Remove the 'Combat' tab from the right panel
    removeCombatTab() {
        try {
            const tabs = document.querySelector('.right-tabs');
            if (!tabs) return;
            const btnRow = tabs.querySelector('.tab-buttons');
            const content = tabs.querySelector('.tab-content');
            if (!btnRow || !content) return;
            
            const btn = btnRow.querySelector('[data-tab="tab-combat"]');
            const pane = document.getElementById('tab-combat');
            
            // If the combat tab is currently active, switch to Character tab
            const wasActive = btn && btn.classList.contains('active');
            
            // Remove the button and pane
            if (btn) btn.remove();
            if (pane) pane.remove();
            
            // If combat tab was active, activate the Character tab
            if (wasActive) {
                this.activateRightPanelTab('tab-character');
            }
        } catch (e) {
            console.warn('Failed to remove combat tab:', e);
        }
    }

    // Programmatically activate a right panel tab
    activateRightPanelTab(tabId) {
        const btn = document.querySelector(`.right-tabs .rp-tab-btn[data-tab="${tabId}"]`);
        const pane = document.getElementById(tabId);
        if (!btn || !pane) return;
        document.querySelectorAll('.right-tabs .rp-tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.right-tabs .rp-tab-pane').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        pane.classList.add('active');
        this.ensureRightPanelScrollable();
    }

    // Update combat log HTML content
    setCombatLogHtml(html) {
        this.ensureCombatTab();
        const pane = document.getElementById('tab-combat');
        if (pane) {
            pane.innerHTML = html || '<div class="placeholder">Combat log</div>';
        }
    }

    attachCharacterTabHandlers() {
        const charPane = document.getElementById('tab-character');
        if (!charPane) return;
        // Stat tooltips on right-click
        charPane.querySelectorAll('.stat-row').forEach(row => {
            row.addEventListener('contextmenu', async (e) => {
                e.preventDefault();
                const key = row.getAttribute('data-stat-key');
                if (!key) return;
                try {
                    const data = await apiClient.getStatModifiers(key);
                    const lines = (data.modifiers||[]).map(m => {
                        const sign = (typeof m.value==='number' && m.value>0)?'+':'';
                        const perc = m.is_percentage?'%':'';
                        const dur = (m.duration!=null)?` (${m.duration} turns)`:'';
                        return `${m.source||'Source'}: ${sign}${m.value}${perc}${dur}`;
                    });
                    this.showTemporaryTooltip(e.pageX, e.pageY, `<b>${key}</b><br>${lines.length?lines.join('<br>'):'No active modifiers.'}`);
                } catch (err) {
                    this.showTemporaryTooltip(e.pageX, e.pageY, `<b>${key}</b><br>Failed to load modifiers.`);
                }
            });
        });
        // Equipment context menu on right-click
        charPane.querySelectorAll('.equip-item').forEach(el => {
            el.addEventListener('contextmenu', (ev) => {
                ev.preventDefault();
                const slot = el.getAttribute('data-slot');
                const itemId = el.getAttribute('data-item-id');
                const items = [];
                if (itemId) {
                    items.push({label: 'Unequip', action: async ()=>{ try{ await apiClient.unequip(slot||itemId); await this.refreshUI(); } catch(e){ this.showNotification('Unequip failed','error'); } }});
                    items.push({label: 'Item Info', action: ()=>{ this.showNotification('Item info not implemented yet','info'); }});
                    items.push({label: 'Drop', action: async ()=>{ try{ await apiClient.unequip(slot||itemId); await apiClient.dropItem(itemId); await this.refreshUI(); } catch(e){ this.showNotification('Drop failed','error'); } }});
                } else {
                    items.push({label: 'Empty Slot', action: ()=>{}});
                }
                this.showContextMenu(ev.pageX, ev.pageY, items);
            });
        });
    }

    renderJournalPane(ui) {
        const jPane = document.getElementById('tab-journal');
        if (!jPane) return;
        const j = ui.journal || {};
        const quests = j.quests || {};
        const ids = Object.keys(quests);
        // Selected quest tracking
        if (!this._selectedQuestId || !quests[this._selectedQuestId]) {
            this._selectedQuestId = ids.length ? ids[0] : null;
        }
        const selected = this._selectedQuestId ? quests[this._selectedQuestId] : null;
        // Build left quest list
        const listHtml = ids.map(qid => {
            const q = quests[qid] || {}; const active = qid===this._selectedQuestId ? ' style="font-weight:bold;"' : '';
            const status = (q.status||'').toString();
            return `<div class="rp-row" data-quest-id="${qid}"><span${active}>${q.name||qid}</span><span>${status}</span></div>`;
        }).join('');
        // Build right detail
        let objHtml = '';
        if (selected && Array.isArray(selected.objectives)) {
            objHtml = selected.objectives.map(o=>{
                const c = o.completed? 'checked' : '';
                const f = o.failed? 'checked' : '';
                return `<div class="rp-row">
                    <span>${o.text||o.description||o.name||o.id}</span>
                    <span>
                        <label style="margin-right:8px;"><input type="checkbox" class="obj-complete" data-quest-id="${selected.id||this._selectedQuestId}" data-obj-id="${o.id}" ${c}> Completed</label>
                        <label><input type="checkbox" class="obj-fail" data-quest-id="${selected.id||this._selectedQuestId}" data-obj-id="${o.id}" ${f}> Failed</label>
                    </span>
                </div>`;
            }).join('');
        } else {
            objHtml = '<div class="rp-empty">No objectives</div>';
        }
        const charText = (j.character||'').toString();
        const notes = Array.isArray(j.notes)? j.notes : [];
        const notesList = notes.map(n=>`<div class=\"rp-row\"><span>${(n.text||'').toString().replace(/</g,'&lt;')}</span><span><button class=\"cancel-btn\" data-del-note=\"${n.id}\">Delete</button></span></div>`).join('');
        jPane.innerHTML = `
            <div class="rp-columns">
                <div class="rp-col">
                    <div class="rp-group"><div class="rp-title">Quests</div>${listHtml||'<div class="rp-empty">—</div>'}</div>
                </div>
                <div class="rp-col">
                    <div class="rp-group"><div class="rp-title">Character Notes</div>
                        <textarea id="journal-character-text" rows="5" style="width:100%">${charText.replace(/</g,'&lt;')}</textarea>
                        <div style="text-align:right; margin-top:6px;"><button id="journal-save-character" class="primary-btn">Save</button></div>
                    </div>
                    <div class="rp-group"><div class="rp-title">Notes</div>
                        <div>${notesList || '<div class=\"rp-empty\">No notes</div>'}</div>
                        <div style="display:flex; gap:6px; margin-top:6px;"><input type="text" id="journal-new-note" placeholder="Add a note..." style="flex:1;"><button id="journal-add-note" class="primary-btn">Add</button></div>
                    </div>
                    <div class="rp-group"><div class="rp-title">${selected?(selected.name||selected.id||'Quest'): 'Quest Details'}</div>
                        ${selected?`<div class="rp-row"><span>Status</span><span>${selected.status||''}</span></div>`:''}
                        <div class="rp-subtitle">Objectives</div>
                        ${objHtml}
                        ${selected?`<div style="text-align:right; margin-top:6px;"><button id="journal-abandon" class="cancel-btn" data-quest-id="${selected.id||this._selectedQuestId}">Abandon Quest</button></div>`:''}
                    </div>
                </div>
            </div>`;
        // Attach handlers
        jPane.querySelectorAll('.rp-row[data-quest-id]').forEach(row=>{
            row.addEventListener('click', ()=>{ this._selectedQuestId = row.getAttribute('data-quest-id'); this.renderJournalPane(ui); });
        });
        const saveBtn = jPane.querySelector('#journal-save-character');
        if (saveBtn) saveBtn.addEventListener('click', async ()=>{
            try { await apiClient.updateJournalCharacter(document.getElementById('journal-character-text').value||''); this.showNotification('Character notes saved','success'); } catch(e){ this.showNotification('Save failed','error'); }
        });
        jPane.querySelectorAll('.obj-complete, .obj-fail').forEach(cb=>{
            cb.addEventListener('change', async ()=>{
                const questId = cb.getAttribute('data-quest-id');
                const objId = cb.getAttribute('data-obj-id');
                const completed = jPane.querySelector(`.obj-complete[data-quest-id="${questId}"][data-obj-id="${objId}"]`).checked;
                const failed = jPane.querySelector(`.obj-fail[data-quest-id="${questId}"][data-obj-id="${objId}"]`).checked;
                try { await apiClient.updateObjectiveStatus(questId, objId, { completed, failed }); } catch(e){ this.showNotification('Update failed','error'); }
            });
        });
        const abandonBtn = jPane.querySelector('#journal-abandon');
        if (abandonBtn) abandonBtn.addEventListener('click', async ()=>{
            const qid = abandonBtn.getAttribute('data-quest-id');
            try { await apiClient.abandonQuest(qid); this.showNotification('Quest abandoned','info'); } catch(e){ this.showNotification('Abandon failed','error'); }
        });
        const addBtn = jPane.querySelector('#journal-add-note');
        if (addBtn) addBtn.addEventListener('click', async ()=>{
            const inp = jPane.querySelector('#journal-new-note');
            const text = (inp && inp.value || '').trim();
            if (!text) return;
            try { await apiClient.addJournalNote(text); inp.value=''; } catch(e){ this.showNotification('Add note failed','error'); }
        });
        jPane.querySelectorAll('button[data-del-note]').forEach(btn=>{
            btn.addEventListener('click', async ()=>{
                const id = btn.getAttribute('data-del-note');
                try { await apiClient.deleteJournalNote(id); } catch(e){ this.showNotification('Delete note failed','error'); }
            });
        });
    }

    showTemporaryTooltip(x, y, html) {
        const tip = document.createElement('div');
        tip.className = 'ui-tooltip';
        tip.innerHTML = html;
        Object.assign(tip.style, { position:'absolute', left:`${x}px`, top:`${y}px`, zIndex:10000, background:'#222', color:'#eee', border:'1px solid #555', borderRadius:'4px', padding:'8px', maxWidth:'280px' });
        document.body.appendChild(tip);
        setTimeout(()=>{ if (tip.parentNode) tip.parentNode.removeChild(tip); }, 2000);
    }

    showContextMenu(x, y, items) {
        const existing = document.getElementById('ui-context-menu');
        if (existing) existing.remove();
        const menu = document.createElement('div');
        menu.id = 'ui-context-menu';
        menu.className = 'ui-context-menu';
        Object.assign(menu.style, { position:'absolute', left:`${x}px`, top:`${y}px`, zIndex:10001, background:'#2b2b2b', color:'#e0e0e0', border:'1px solid #3a3a3a', borderRadius:'4px', minWidth:'160px' });
        (items||[]).forEach(it => {
            const a = document.createElement('div');
            a.textContent = it.label || '';
            Object.assign(a.style, { padding:'6px 12px', cursor:'pointer' });
            a.addEventListener('mouseover', ()=>{ a.style.background='#3a3a3a'; });
            a.addEventListener('mouseout', ()=>{ a.style.background='transparent'; });
            a.addEventListener('click', ()=>{ try{ it.action && it.action(); } finally { menu.remove(); } });
            menu.appendChild(a);
        });
        document.body.appendChild(menu);
        const close = ()=>{ if (menu.parentNode) menu.parentNode.removeChild(menu); document.removeEventListener('click', close); };
        setTimeout(()=>{ document.addEventListener('click', close); }, 0);
    }

    async renderInventoryPane() {
        const invPane = document.getElementById('tab-inventory');
        try {
            const inv = await apiClient.getInventory();
            const items = inv.items||[];
            const money = inv.currency||{};
            
            // Currency display
            const header = `<div class="currency-section">
                <div class="currency-grid">
                    <div class="currency-item currency-gold">
                        <div class="currency-label">Gold</div>
                        <div class="currency-value">${money.gold||0}</div>
                    </div>
                    <div class="currency-item currency-silver">
                        <div class="currency-label">Silver</div>
                        <div class="currency-value">${money.silver||0}</div>
                    </div>
                    <div class="currency-item currency-copper">
                        <div class="currency-label">Copper</div>
                        <div class="currency-value">${money.copper||0}</div>
                    </div>
                </div>
            </div>`;
            
            // Weight display
            const currentWeight = inv.weight?.current||0;
            const maxWeight = inv.weight?.max||1;
            const overLimit = currentWeight > maxWeight ? ' over-limit' : '';
            const weight = `<div class="weight-section">
                <div class="weight-label">Encumbrance</div>
                <div class="weight-value${overLimit}">${currentWeight.toFixed(1)} / ${maxWeight.toFixed(1)}</div>
            </div>`;
            
            // Filter controls
            const currentType = this._invFilterType || 'All';
            const currentSearch = this._invFilterSearch || '';
            const types = Array.from(new Set(items.map(i => (i.type||'miscellaneous').toLowerCase()))).sort();
            const typeOptions = ['All', ...types].map(t => `<option value="${t}" ${t===currentType?'selected':''}>${t.charAt(0).toUpperCase()+t.slice(1)}</option>`).join('');
            const filters = `<div class="rp-group"><div class="rp-title">Filters</div>
                <div class="rp-row"><span>Type</span><span><select id="inv-filter-type">${typeOptions}</select></span></div>
                <div class="rp-row"><span>Search</span><span><input id="inv-filter-search" type="text" value="${currentSearch.replace(/"/g,'&quot;')}" placeholder="Item name..."></span></div>
            </div>`;
            
            // Apply filters
            const filteredItems = items.filter(it => {
                const matchType = (currentType==='All') || ((it.type||'').toLowerCase()===currentType.toLowerCase());
                const matchName = !currentSearch || (it.name||'').toLowerCase().includes(currentSearch.toLowerCase());
                return matchType && matchName;
            });
            
            // Render grid
            const gridCells = filteredItems.map(it=>{
                const rarity = (it.rarity||'common').toLowerCase();
                const iconPath = it.icon_path || '/images/icons/miscellaneous/generic_1.png';
                const count = it.quantity > 1 ? it.quantity : (it.count || 0);
                const stackHtml = count > 1 ? `<span class="item-stack-count">x${count}</span>` : '';
                const questHtml = it.is_quest_item ? `<span class="item-quest-marker">★</span>` : '';
                const equippedHtml = it.equipped ? `<span class="item-equipped-marker">✓</span>` : '';
                
                // Durability badge
                let durabilityHtml = '';
                if (it.durability != null && it.current_durability != null) {
                    const pct = (it.current_durability / it.durability) * 100;
                    const durClass = pct < 25 ? 'low' : pct < 60 ? 'medium' : 'high';
                    durabilityHtml = `<span class="item-durability-badge ${durClass}">${Math.round(pct)}%</span>`;
                }
                
                return `<div class="inventory-cell" 
                            data-id="${it.id}" 
                            data-rarity="${rarity}"
                            data-type="${it.type||'miscellaneous'}"
                            title="${it.name}">
                    <img src="${iconPath}" class="inventory-cell-icon" alt="${it.name}" onerror="this.src='/images/icons/miscellaneous/generic_1.png'">
                    <div class="item-overlay">
                        ${equippedHtml}
                        ${questHtml}
                        ${durabilityHtml}
                        ${stackHtml}
                    </div>
                </div>`;
            }).join('');
            
            const gridHtml = `<div class="inventory-grid-container">
                <div class="inventory-grid">${gridCells || '<div class="rp-empty">No items</div>'}</div>
            </div>`;
            
            invPane.innerHTML = header + weight + filters + gridHtml;
            
            // Attach filter handlers
            const typeSel = invPane.querySelector('#inv-filter-type');
            const searchInp = invPane.querySelector('#inv-filter-search');
            if (typeSel) typeSel.addEventListener('change', ()=>{ this._invFilterType = typeSel.value; this.renderInventoryPane(); });
            if (searchInp) searchInp.addEventListener('input', ()=>{ this._invFilterSearch = searchInp.value||''; this.renderInventoryPane(); });
            
            // Attach click handlers to cells
            invPane.querySelectorAll('.inventory-cell').forEach(cell=>{
                cell.addEventListener('click', async () => {
                    const id = cell.getAttribute('data-id');
                    await this.showItemInfo(id);
                });
                
                // Right-click for context menu (future: equip/drop options)
                cell.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    const id = cell.getAttribute('data-id');
                    this.showItemContextMenu(e.pageX, e.pageY, id, items.find(i => i.id === id));
                });
            });
        } catch (e) {
            console.error('Inventory render error:', e);
            invPane.innerHTML = `<div class="rp-empty">Failed to load inventory</div>`;
        }
    }
    
    renderPaperdoll(ui) {
        // Determine silhouette path based on race and gender
        const race = (ui.player.race || 'human').toLowerCase();
        const gender = (ui.player.sex || ui.player.gender || 'male').toLowerCase();
        
        // Try race-specific, fallback to default, then to generic default
        const silhouettePath = `/images/character/paperdoll/${race}_${gender}.png`;
        const fallbackPath = `/images/character/paperdoll/default_${gender}.png`;
        const finalFallback = `/images/character/paperdoll/default_male.png`;
        
        // Build equipment map
        const eqMap = {};
        console.log('=== PAPERDOLL DEBUG ===');
        console.log('ui.equipment array:', ui.equipment);
        (ui.equipment||[]).forEach(e=>{ 
            const slotKey = e.slot ? e.slot.toUpperCase() : '';
            console.log(`Mapping: slot="${e.slot}" -> key="${slotKey}" | item="${e.item_name}" | icon="${e.icon_path}"`);
            eqMap[slotKey] = e; 
        });
        console.log('Final equipment map:', eqMap);
        console.log('Checking CHEST slot:', eqMap['CHEST']);
        console.log('Checking MAIN_HAND slot:', eqMap['MAIN_HAND']);
        
        // Define all equipment slots
        const allSlots = [
            'HEAD', 'NECK', 'SHOULDERS', 'CHEST', 'BACK', 'WRISTS', 'HANDS', 'WAIST', 'LEGS', 'FEET',
            'MAIN_HAND', 'OFF_HAND', 'RANGED',
            'FINGER_1', 'FINGER_2', 'FINGER_3', 'FINGER_4', 'FINGER_5',
            'FINGER_6', 'FINGER_7', 'FINGER_8', 'FINGER_9', 'FINGER_10',
            'TRINKET_1', 'TRINKET_2'
        ];
        
        const slotsHtml = allSlots.map(slot => {
            const eq = eqMap[slot];
            const hasItem = eq && eq.item_id;
            // Fallback to generic icon if icon_path is missing
            const iconPath = (eq && eq.icon_path) ? eq.icon_path : '/images/icons/miscellaneous/generic_1.png';
            const rarity = eq && eq.rarity ? eq.rarity.toLowerCase() : 'common';
            const itemName = eq && eq.item_name ? eq.item_name : '';
            const slotDisplay = slot.replace(/_/g, ' ').toLowerCase().replace(/(^|\s)\S/g, t => t.toUpperCase());
            
            return `<div class=\"equipment-slot ${hasItem ? 'has-item' : 'empty'}\" 
                        data-slot=\"${slot.toLowerCase()}\" 
                        data-rarity=\"${rarity}\"
                        ${hasItem ? `data-item-id=\"${eq.item_id}\"` : ''}>
                ${hasItem ? `<img src=\"${iconPath}\" class=\"equipment-slot-icon\" alt=\"${itemName}\" onerror=\"this.src='/images/icons/miscellaneous/generic_1.png'\">` : ''}
                <div class=\"equipment-slot-label\">${hasItem ? itemName : slotDisplay}</div>
            </div>`;
        }).join('');
        
        return `<div class="rp-group">
            <div class="rp-title">Equipment</div>
            <div class="paperdoll-container">
                <div class="paperdoll-wrapper">
                    <img src="${silhouettePath}" 
                         class="paperdoll-silhouette" 
                         alt="Character" 
                         style="display:none;" 
                         onload="this.style.display='block';" 
                         onerror="this.style.display='none';this.onerror=null;"
                    <div class="paperdoll-slots">
                        ${slotsHtml}
                    </div>
                </div>
                <div class="paperdoll-info">
                    <div class="paperdoll-race-class">${ui.player.race} ${ui.player.path}</div>
                    <div>Click slots to manage equipment</div>
                </div>
            </div>
        </div>`;
    }
    
    attachPaperdollHandlers() {
        const charPane = document.getElementById('tab-character');
        if (!charPane) return;
        
        charPane.querySelectorAll('.equipment-slot').forEach(slot => {
            slot.addEventListener('click', async () => {
                const slotName = slot.getAttribute('data-slot');
                const itemId = slot.getAttribute('data-item-id');
                
                if (itemId) {
                    // Slot has item - show item info
                    await this.showItemInfo(itemId);
                } else {
                    // Empty slot - show notification
                    const slotDisplay = slotName.replace(/_/g, ' ').toUpperCase();
                    this.showNotification(`${slotDisplay} slot is empty`, 'info', 2000);
                }
            });
            
            // Right-click for context menu
            slot.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                const slotName = slot.getAttribute('data-slot');
                const itemId = slot.getAttribute('data-item-id');
                
                if (itemId) {
                    this.showEquipmentSlotContextMenu(e.pageX, e.pageY, slotName, itemId);
                } else {
                    this.showNotification('Slot is empty', 'info', 1500);
                }
            });
        });
    }
    
    showEquipmentSlotContextMenu(x, y, slotName, itemId) {
        const menuItems = [
            { label: '📖 Examine', action: () => this.showItemInfo(itemId) },
            { label: '✖ Unequip', action: async () => {
                try {
                    // Unequip by slot name for reliability
                    await apiClient.unequip(slotName);
                    await this.refreshUI();
                    this.showNotification('Item unequipped', 'success');
                } catch(e) {
                    this.showNotification(e.message || 'Failed to unequip', 'error');
                }
            }}
        ];
        
        this.showContextMenu(x, y, menuItems);
    }
    
    showItemContextMenu(x, y, itemId, item) {
        if (!item) return;
        
        const menuItems = [
            { label: '📖 Examine', action: () => this.showItemInfo(itemId) }
        ];
        
        // Add equip/unequip option
        if (item.is_equippable || ['weapon','armor','shield','accessory'].includes((item.type||'').toLowerCase())) {
            if (item.equipped) {
                menuItems.push({ label: '✖ Unequip', action: async () => {
                    try {
                        await apiClient.unequip(itemId);
                        await this.refreshUI();
                    } catch(e) { this.showNotification(e.message||'Failed to unequip','error'); }
                }});
            } else {
                menuItems.push({ label: '✓ Equip', action: async () => {
                    try {
                        await apiClient.equipItem(itemId);
                        await this.refreshUI();
                    } catch(e) { this.showNotification(e.message||'Failed to equip','error'); }
                }});
            }
        }
        
        // Add use option for consumables
        if (item.is_consumable || (item.type||'').toLowerCase() === 'consumable') {
            menuItems.push({ label: '🍴 Use', action: async () => {
                try {
                    await apiClient.useItem(itemId);
                    await this.refreshUI();
                } catch(e) { this.showNotification(e.message||'Failed to use','error'); }
            }});
        }
        
        // Add drop option
        menuItems.push({ label: '🗑 Drop', action: async () => {
            try {
                await apiClient.dropItem(itemId);
                await this.refreshUI();
            } catch(e) { this.showNotification(e.message||'Failed to drop','error'); }
        }});
        
        this.showContextMenu(x, y, menuItems);
    }

    /** Update resource bar label/width for Phase 1 (preview) */
    updateResourceBarPhase1(barTypeKey, update) {
        const map = { hp:'health', stamina:'stamina', mana:'mana', resolve:'resolve', mp:'mana' };
        const key = map[String(barTypeKey||'').toLowerCase()] || barTypeKey;
        const titleEl = document.querySelector(`.rp-bar-title[data-bar-type="${key}"]`);
        const fillEl = document.querySelector(`.rp-bar-fill[data-bar-type="${key}"]`);
        if (!titleEl || !fillEl) return;
        const max = update.max_value!=null ? parseInt(update.max_value,10) : 0;
        const cur = update.new_value_preview!=null ? parseInt(update.new_value_preview,10) : 0;
        const barName = key.charAt(0).toUpperCase()+key.slice(1);
        titleEl.textContent = `${barName}: ${cur}/${max}`;
        const pct = max? Math.min(100, (cur/max)*100) : 0;
        fillEl.style.width = `${pct}%`;
    }

    /** Update resource bar label/width for Phase 2 (finalize) */
    updateResourceBarPhase2(barTypeKey, update) {
        const map = { hp:'health', stamina:'stamina', mana:'mana', resolve:'resolve', mp:'mana' };
        const key = map[String(barTypeKey||'').toLowerCase()] || barTypeKey;
        const titleEl = document.querySelector(`.rp-bar-title[data-bar-type="${key}"]`);
        const fillEl = document.querySelector(`.rp-bar-fill[data-bar-type="${key}"]`);
        if (!titleEl || !fillEl) return;
        const max = update.max_value!=null ? parseInt(update.max_value,10) : 0;
        const cur = update.final_new_value!=null ? parseInt(update.final_new_value,10) : 0;
        const barName = key.charAt(0).toUpperCase()+key.slice(1);
        titleEl.textContent = `${barName}: ${cur}/${max}`;
        const pct = max? Math.min(100, (cur/max)*100) : 0;
        fillEl.style.width = `${pct}%`;
    }

    async showItemInfo(itemId) {
        try {
            const data = await (async ()=>{
                const resp = await fetch(apiClient.buildUrl(`items/${apiClient.sessionId}/${encodeURIComponent(itemId)}`), { headers: apiClient.getHeaders() });
                if (!resp.ok) throw new Error('Failed to fetch item details');
                return await resp.json();
            })();
            // Populate modal
            const modal = document.getElementById('item-info-modal');
            const body = document.getElementById('item-info-body');
            if (!modal || !body) { this.showNotification('Item info UI not available','error'); return; }
            const rows = [];
            const esc = (t)=> (t==null?'' : String(t)).replace(/</g,'&lt;');
            rows.push(`<div class=\"rp-row\"><span><b>Type</b></span><span>${esc(data.item_type)}</span></div>`);
            if (data.description) rows.push(`<div class=\"rp-row\"><span><b>Description</b></span><span>${esc(data.description)}</span></div>`);
            rows.push(`<div class=\"rp-row\"><span><b>Weight</b></span><span>${data.weight!=null?data.weight:'?'}</span></div>`);
            rows.push(`<div class=\"rp-row\"><span><b>Value</b></span><span>${data.value!=null?data.value:'?'}</span></div>`);
            rows.push(`<div class=\"rp-row\"><span><b>Quantity</b></span><span>${data.quantity||1}</span></div>`);
            if (data.durability!=null || data.current_durability!=null) rows.push(`<div class=\"rp-row\"><span><b>Durability</b></span><span>${data.current_durability!=null?data.current_durability:'?'} / ${data.durability!=null?data.durability:'?'}</span></div>`);
            if (Array.isArray(data.equip_slots) && data.equip_slots.length>0) rows.push(`<div class=\"rp-row\"><span><b>Equip Slots</b></span><span>${data.equip_slots.map(s=>esc(s.replace(/_/g,' '))).join(', ')}</span></div>`);
            // Stats
            if (Array.isArray(data.stats) && data.stats.length>0) {
                const srows = data.stats.map(s=>`<li>${esc(s.display_name||s.name)}: ${s.value}${s.is_percentage?'%':''}</li>`).join('');
                rows.push(`<div class=\"rp-subtitle\">Stats & Effects</div><ul>${srows}</ul>`);
            }
            // Custom props
            const keys = Object.keys(data.custom_properties||{});
            if (keys.length>0) {
                const plist = keys.map(k=>`<li><b>${esc(k.replace(/_/g,' '))}:</b> ${esc(data.custom_properties[k])}</li>`).join('');
                rows.push(`<div class=\"rp-subtitle\">Properties</div><ul>${plist}</ul>`);
            }
            // Tags
            if (Array.isArray(data.tags) && data.tags.length>0) rows.push(`<div class=\"rp-row\"><span><b>Tags</b></span><span>${data.tags.map(esc).join(', ')}</span></div>`);
            body.innerHTML = `<h3>${esc(data.name||'Item')}</h3>` + rows.join('');
            this.openModal('itemInfo');
        } catch (e) {
            console.error('Item info error', e);
            this.showNotification('Failed to load item info','error');
        }
    }

    /** Refresh UI: fetch UI state and render panels + status bar */
    async refreshUI() {
        try {
            const ui = await apiClient.getUIState();
            // Normalize mode value from server
            let modeRaw = ui.mode;
            let modeStr = '';
            try { modeStr = String(modeRaw || '').toUpperCase(); } catch { modeStr = ''; }
            const inCombat = modeStr.includes('COMBAT');
            
            // Handle combat mode changes
            if (inCombat) {
                // Entering or staying in combat - ensure combat tab exists
                this.ensureCombatTab();
                if (!this._autoCombatShown || this._prevMode !== 'COMBAT') {
                    this.activateRightPanelTab('tab-combat');
                    this._autoCombatShown = true;
                }
            } else if (this._prevMode === 'COMBAT') {
                // Exiting combat - remove combat tab
                this.removeCombatTab();
                this._autoCombatShown = false;
            }
            
            // Update previous mode for next comparison
            this._prevMode = inCombat ? 'COMBAT' : modeStr;
            
            // Status bar
            const locEl = document.getElementById('current-location');
            const timeEl = document.getElementById('game-time');
            const pName = document.getElementById('player-name');
            const pLvl = document.getElementById('player-level');
            if (locEl) locEl.textContent = ui.location||'-';
            if (timeEl) timeEl.textContent = ui.time||'-';
            if (pName) pName.textContent = ui.player.name||'-';
            if (pLvl) pLvl.textContent = ui.player.level||'1';
            
            // Render right panel content
            this.renderRightPanel(ui);
        } catch (e) {
            console.warn('refreshUI failed', e);
        }
    }

    /**
     * Load background list from server and apply the first available (to mirror Py GUI default).
     */
    async applyBackgroundFromServer() {
        try {
            const saved = localStorage.getItem('rpg_bg_filename');
            if (saved) {
                document.body.style.setProperty('--bg-image-url', `url("/images/gui/background/${saved}")`);
                document.body.classList.add('has-bg');
                return;
            }
        } catch (e) { /* ignore */ }
        try {
            const resp = await fetch('/api/ui/backgrounds');
            if (!resp.ok) return;
            const data = await resp.json();
            if (data && Array.isArray(data.backgrounds) && data.backgrounds.length > 0) {
                const filename = data.backgrounds[0];
                document.body.style.setProperty('--bg-image-url', `url("/images/gui/background/${filename}")`);
                document.body.classList.add('has-bg');
            }
        } catch (e) {
            console.warn('Failed to apply background from server:', e);
        }
    }

    /**
     * Apply font size to the output area
     * @param {string} size - Font size in pixels
     */
    applyFontSize(size) {
        this.outputElement.style.fontSize = `${size}px`;
        this.settings.fontSize = size;

        // Update font size slider if it exists
        const fontSizeSlider = document.getElementById('font-size-slider');
        if (fontSizeSlider) {
            fontSizeSlider.value = size;
        }

        const fontSizeValue = document.getElementById('font-size-value');
        if (fontSizeValue) {
            fontSizeValue.textContent = `${size}px`;
        }

        localStorage.setItem('rpg_font_size', size);
    }

    /**
     * Switch to a different tab in the settings modal
     * @param {string} tabId - The ID of the tab to switch to
     */
    switchTab(tabId) {
        // Deactivate all tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });

        document.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.remove('active');
        });

        // Activate the target tab
        document.querySelector(`.tab-btn[data-tab="${tabId}"]`).classList.add('active');
        document.getElementById(tabId).classList.add('active');
    }

    /**
     * Toggle password field visibility
     * @param {string} inputId - The ID of the password input field
     * @param {HTMLElement} button - The button element that toggles visibility
     */
    togglePasswordVisibility(inputId, button) {
        const input = document.getElementById(inputId);
        const icon = button.querySelector('i');

        if (input.type === 'password') {
            input.type = 'text';
            icon.className = 'fas fa-eye-slash';
        } else {
            input.type = 'password';
            icon.className = 'fas fa-eye';
        }
    }

    /**
     * Reset agent settings to default values
     */
    resetAgentSettingsToDefault() {
        console.log('Resetting agent settings to defaults');

        // Default settings for each agent
        const defaultSettings = {
            'narrator': {
                provider: 'OPENAI',
                model: 'gpt-4o-mini', 
                temperature: 0.7,
                enabled: true
            },
            'rule-checker': {
                provider: 'GOOGLE',
                model: 'gemini-2.0-flash', 
                temperature: 0.3,
                enabled: true
            },
            'context-evaluator': {
                provider: 'GOOGLE',
                model: 'gemini-2.0-flash', 
                temperature: 0.2,
                enabled: true
            }
        };

        // Apply default settings to UI
        for (const [agent, settings] of Object.entries(defaultSettings)) {
            console.log(`Applying default settings for ${agent}`);

            // Set provider
            const providerSelect = document.getElementById(`${agent}-provider`);
            if (providerSelect) {
                providerSelect.value = settings.provider;

                // Update the model dropdown first
                this.updateModelOptionsForAgent(agent, settings.provider);

                // Give time for the model options to update
                setTimeout(() => {
                    // Try to find the model select - it should exist now after updateModelOptionsForAgent
                    const modelSelect = document.getElementById(`${agent}-model`);
                    if (!modelSelect || modelSelect.tagName !== 'SELECT') { // Ensure it's a select
                        console.error(`Model select not found or not a SELECT for ${agent} after updateModelOptionsForAgent`);
                        return;
                    }

                    // Set model value
                    // For selecting options, first check if the desired value exists
                    let optionExists = false;
                    for (let i = 0; i < modelSelect.options.length; i++) {
                        if (modelSelect.options[i].value === settings.model) {
                            optionExists = true;
                            modelSelect.selectedIndex = i;
                            break;
                        }
                    }

                    // If option doesn't exist, select the first one
                    if (!optionExists && modelSelect.options.length > 0) {
                        console.warn(`Default model ${settings.model} not found for ${agent}, selecting first option.`);
                        modelSelect.selectedIndex = 0;
                    }

                    // Set temperature
                    const tempSlider = document.getElementById(`${agent}-temperature`);
                    const tempValue = document.getElementById(`${agent}-temperature-value`);
                    if (tempSlider) {
                        tempSlider.value = settings.temperature;
                        if (tempValue) {
                            tempValue.textContent = settings.temperature;
                        }
                    }

                    // Set enabled state
                    const enabledToggle = document.getElementById(`${agent}-enabled-toggle`);
                    if (enabledToggle) {
                        enabledToggle.checked = settings.enabled;
                    }
                }, 150); // Slightly increased wait time for DOM updates
            } else {
                console.error(`Provider select not found for ${agent}`);
            }
        }

        console.log('Reset to defaults completed');
    }

    /**
     * Load LLM settings from the API
     */
    async loadLLMSettings() {
        try {
            const settings = await apiClient.getLLMSettings();
            this.llmSettings = settings;

            // Update UI with loaded settings
            this.updateLLMSettingsUI(settings);

            // Initialize model options for each agent based on current provider selection
            const agentNames = ['narrator', 'rule-checker', 'context-evaluator'];
            agentNames.forEach(agent => {
                const providerSelect = document.getElementById(`${agent}-provider`);
                if (providerSelect) {
                    // Ensure model options are updated AFTER settings are loaded
                    this.updateModelOptionsForAgent(agent, providerSelect.value);
                    // Schedule setting the value after options are populated
                     setTimeout(() => {
                         this.setAgentModelValueFromSettings(agent, settings);
                     }, 100);
                }
            });

            return settings;
        } catch (error) {
            console.error('Error loading LLM settings:', error);
            this.showNotification('Failed to load LLM settings', 'error');
            return null;
        }
    }

    /**
     * Helper to set agent model value after options are populated
     */
    setAgentModelValueFromSettings(agent, settings) {
        const modelSelect = document.getElementById(`${agent}-model`);
        const agentConfig = settings?.agents?.[agent.replace('-', '_')];

        if (modelSelect && modelSelect.tagName === 'SELECT' && agentConfig) {
            const modelValue = agentConfig.model;
            // Safely check if options exists and has items before using Array.from
            if (modelSelect.options && modelSelect.options.length > 0) {
                const option = Array.from(modelSelect.options).find(opt => opt.value === modelValue);
                if (option) {
                    modelSelect.value = modelValue;
                } else {
                    // Model from settings not found in options, select first option
                    console.warn(`Model ${modelValue} for agent ${agent} not found in options. Selecting first available.`);
                    modelSelect.value = modelSelect.options[0].value;
                }
            }
        } else if (modelSelect) {
             console.warn(`Model element for agent ${agent} is not a SELECT or config is missing.`);
             // Try to fix it if it's not a SELECT
             if (modelSelect.tagName !== 'SELECT') {
                 const provider = document.getElementById(`${agent}-provider`)?.value || 'OPENAI';
                 this.forceCreateSelect(agent, provider, modelSelect.value || '');
             }
        }
    }


    /**
     * Update model options for an agent based on selected provider
     * @param {string} agent - The agent name (e.g., 'narrator', 'rule-checker', 'context-evaluator')
     * @param {string} provider - The selected provider (e.g., 'OPENAI', 'GOOGLE', 'OPENROUTER')
     */
    updateModelOptionsForAgent(agent, provider) {
        console.log(`Updating model options for ${agent} with provider ${provider}`);
        
        // Set the flag to prevent other code from interfering
        this.isUpdatingModelOptions = true;
        
        try {
            // Find the agent section
            const agentSection = document.querySelector(`#${agent}-provider`).closest('.agent-section');
            if (!agentSection) {
                console.error(`Could not find agent section for ${agent}`);
                return;
            }
            
            // Find all form groups in the section
            const formGroups = agentSection.querySelectorAll('.form-group');
            let modelFormGroup = null;
            
            // Find the form group for the model
            for (const group of formGroups) {
                const label = group.querySelector('label');
                if (label && label.getAttribute('for') === `${agent}-model`) {
                    modelFormGroup = group;
                    break;
                }
            }
            
            // Get current value if there's an existing model element
            let currentValue = '';
            const existingModel = document.getElementById(`${agent}-model`);
            if (existingModel) {
                currentValue = existingModel.value || '';
            }
            
            // If we couldn't find it, create a new one
            if (!modelFormGroup) {
                console.log(`Creating new form group for models`);
                modelFormGroup = document.createElement('div');
                modelFormGroup.className = 'form-group';
                
                // Insert it after the provider form group
                const providerFormGroup = agentSection.querySelector(`#${agent}-provider`).closest('.form-group');
                if (providerFormGroup && providerFormGroup.nextSibling) {
                    agentSection.insertBefore(modelFormGroup, providerFormGroup.nextSibling);
                } else {
                    agentSection.appendChild(modelFormGroup);
                }
            }
            
            // Check what's in the form group before clearing
            console.log('Current model form group content:', modelFormGroup.innerHTML);
            
            // Clear the existing form group
            modelFormGroup.innerHTML = '';
            
            // Create model label
            const label = document.createElement('label');
            label.setAttribute('for', `${agent}-model`);
            label.textContent = 'Model:';
            modelFormGroup.appendChild(label);
            
            // Create select element
            const select = document.createElement('select');
            select.id = `${agent}-model`;
            
            // Get models based on provider
            let models = [];
            
            if (provider === 'OPENROUTER') {
                // OpenRouter models
                models = [
                    { value: 'google/gemini-2.0-flash-lite-preview-02-05:free', label: 'Google Gemini 2.0 Flash Lite (Free)' },
                    { value: 'nousresearch/deephermes-3-llama-3-8b-preview:free', label: 'DeepHermes 3 Llama 3 8B (Free)' },
                    { value: 'google/gemini-2.0-pro-exp-02-05:free', label: 'Google Gemini 2.0 Pro (Free)' },
                    { value: 'mistralai/mistral-small-3.1-24b-instruct:free', label: 'Mistral Small 3.1 24B (Free)' },
                    { value: 'google/gemini-2.0-flash-exp:free', label: 'Google Gemini 2.0 Flash (Free)' }
                ];
                
                // Add current value if not empty and not already in the list
                if (currentValue && !models.some(m => m.value === currentValue)) {
                    models.push({ value: currentValue, label: currentValue });
                }
            } else if (provider === 'OPENAI') {
                // OpenAI models
                models = [
                    { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                    { value: 'gpt-4o', label: 'GPT-4o' },
                ];
            } else if (provider === 'GOOGLE') {
                // Google models
                models = [
                    { value: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash' },
                    { value: 'gemini-2.0-pro-latest', label: 'Gemini 2.0 Pro' },
                ];
            } else {
                models = [
                    { value: 'unknown-provider-model', label: 'Select Model' }
                ];
            }
            
            // Add options to the select
            models.forEach(model => {
                const option = document.createElement('option');
                option.value = model.value;
                option.textContent = model.label;
                select.appendChild(option);
            });
            
            // Set the value if it exists in options
            if (currentValue) {
                const option = Array.from(select.options).find(opt => opt.value === currentValue);
                if (option) {
                    select.value = currentValue;
                }
            }
            
            // Append the select to the form group
            modelFormGroup.appendChild(select);
            
            // Ensure the element is a SELECT by checking it
            setTimeout(() => {
                const modelElement = document.getElementById(`${agent}-model`);
                if (modelElement && modelElement.tagName !== 'SELECT') {
                    console.error(`Model element for ${agent} is not a SELECT after creation!`);
                    // Attempt to force replace
                    this.forceCreateSelect(agent, provider, modelElement.value || '');
                }
            }, 50);
            
            console.log('Element created:', select.tagName);
            console.log('Form group after update:', modelFormGroup.innerHTML);
        } finally {
            // Reset flag
            this.isUpdatingModelOptions = false;
        }
    }

    /**
     * Update the LLM settings UI with the given settings
     * @param {Object} settings - The LLM settings object
     */
    updateLLMSettingsUI(settings) {
        if (!settings) return;

        // Update LLM enabled toggle
        const llmToggle = document.getElementById('llm-enabled-toggle');
        if (llmToggle) {
            llmToggle.checked = settings.llm_enabled;
            this.settings.llmEnabled = settings.llm_enabled;
            localStorage.setItem('rpg_llm_enabled', settings.llm_enabled);
        }

        // Update provider settings
        if (settings.providers) {
            for (const [provider, config] of Object.entries(settings.providers)) {
                if (provider !== 'openai' && provider !== 'google' && provider !== 'openrouter') continue;

                // API Key
                const apiKeyInput = document.getElementById(`${provider}-api-key`);
                if (apiKeyInput) {
                    apiKeyInput.value = config.api_key || '';
                }

                // Enabled toggle
                const enabledToggle = document.getElementById(`${provider}-enabled-toggle`);
                if (enabledToggle) {
                    enabledToggle.checked = config.enabled !== false;
                }
            }
        }

        // Update agent settings
        if (settings.agents) {
            for (const [agent, config] of Object.entries(settings.agents)) {
                // Provider
                const providerSelect = document.getElementById(`${agent}-provider`);
                if (providerSelect) {
                    providerSelect.value = config.provider_type || 'OPENAI';
                    // Model options will be updated and value set by loadLLMSettings caller
                }

                // Temperature
                const tempSlider = document.getElementById(`${agent}-temperature`);
                const tempValue = document.getElementById(`${agent}-temperature-value`);
                if (tempSlider) {
                    const temp = config.temperature !== undefined ? config.temperature : 0.7;
                    tempSlider.value = temp;
                    if (tempValue) {
                        tempValue.textContent = temp;
                    }
                }

                // Enabled toggle
                const enabledToggle = document.getElementById(`${agent}-enabled-toggle`);
                if (enabledToggle) {
                    enabledToggle.checked = config.enabled !== false;
                }
            }
        }
    }

    /**
     * Collect LLM settings from the UI
     * @returns {Object} The collected LLM settings
     */
    collectLLMSettings() {
        const settings = {
            providers: {
                openai: {
                    api_key: document.getElementById('openai-api-key')?.value || '',
                    enabled: document.getElementById('openai-enabled-toggle')?.checked !== false
                },
                google: {
                    api_key: document.getElementById('google-api-key')?.value || '',
                    enabled: document.getElementById('google-enabled-toggle')?.checked !== false
                },
                openrouter: {
                    api_key: document.getElementById('openrouter-api-key')?.value || '',
                    enabled: document.getElementById('openrouter-enabled-toggle')?.checked !== false
                }
            },
            agents: {}
        };

        // Collect agent settings
        const agentNames = ['narrator', 'rule-checker', 'context-evaluator'];

        for (const agent of agentNames) {
            const providerSelect = document.getElementById(`${agent}-provider`);
            let modelElement = document.getElementById(`${agent}-model`);
            const temperatureElement = document.getElementById(`${agent}-temperature`);
            const enabledElement = document.getElementById(`${agent}-enabled-toggle`);

            if (!providerSelect) continue;

            const provider = providerSelect.value;
            let model = '';

            // Check if model element is not a SELECT, and fix it if needed
            if (modelElement && modelElement.tagName !== 'SELECT') {
                console.warn(`Model element for ${agent} is not a SELECT when collecting settings, fixing...`);
                this.forceCreateSelect(agent, provider, modelElement.value || '');
                // Get the new SELECT
                modelElement = document.getElementById(`${agent}-model`);
            }

            // Get model value
            if (modelElement && modelElement.tagName === 'SELECT') {
                model = modelElement.value;
                // Handle case where no models were available
                if (model === 'no-models-available') {
                    console.warn(`Agent ${agent} has no model selected. Using empty string.`);
                    model = '';
                }
            } else if (modelElement) {
                // If it's an INPUT somehow, at least get its value
                model = modelElement.value || '';
                console.error(`Model element for ${agent} is still not a SELECT! Using value: ${model}`);
            } else {
                console.error(`Model element for ${agent} not found!`);
            }

            // Create agent setting
            settings.agents[agent.replace('-', '_')] = {
                provider_type: provider,
                model: model,
                temperature: parseFloat(temperatureElement?.value || 0.7),
                enabled: enabledElement?.checked !== false
            };
        }

        return settings;
    }

    /**
     * Toggle LLM functionality for the current game session
     * @param {boolean} enabled - Whether to enable LLM functionality
     */
    async toggleLLM(enabled) {
        try {
            if (!apiClient.hasActiveSession()) {
                this.showNotification('No active game session', 'warning');
                return;
            }

            const result = await apiClient.toggleLLM(enabled);

            if (result.status === 'success') {
                this.settings.llmEnabled = enabled;
                localStorage.setItem('rpg_llm_enabled', enabled);
                this.showNotification(`LLM functionality ${enabled ? 'enabled' : 'disabled'}`, 'success');
            } else {
                this.showNotification(`Failed to ${enabled ? 'enable' : 'disable'} LLM functionality`, 'error');
            }

            return result;
        } catch (error) {
            console.error('Error toggling LLM:', error);
            this.showNotification(`Failed to ${enabled ? 'enable' : 'disable'} LLM functionality`, 'error');
            return null;
        }
    }

    /**
     * Save settings to localStorage and backend
     */
    async saveSettings() {
        let hasSession = apiClient.hasActiveSession();

        // Save UI preferences locally immediately
        const themeSelect = document.getElementById('theme-select');
        const fontSizeSlider = document.getElementById('font-size-slider');
        const llmEnabledToggle = document.getElementById('llm-enabled-toggle');

        if (themeSelect) {
            this.settings.theme = themeSelect.value;
            localStorage.setItem('rpg_theme', this.settings.theme);
        }

        if (fontSizeSlider) {
            this.settings.fontSize = fontSizeSlider.value;
            localStorage.setItem('rpg_font_size', this.settings.fontSize);
        }

        if (llmEnabledToggle) {
            this.settings.llmEnabled = llmEnabledToggle.checked;
            localStorage.setItem('rpg_llm_enabled', llmEnabledToggle.checked);
        }


        // Save LLM settings to backend
        if (document.getElementById('llm-settings')) {
            const llmSettings = this.collectLLMSettings();

            // Ensure session exists before saving LLM settings or toggling LLM
            if (!hasSession) {
                try {
                    this.addMessage('Creating a temporary session to save settings...', 'system');
                    const result = await apiClient.createNewGame('TemporarySettingsSave');
                    apiClient.sessionId = result.session_id;
                    apiClient.saveSession();

                    // Let main.js handle WebSocket connection if needed
                    const event = new CustomEvent('session-created', { detail: { sessionId: result.session_id } });
                    document.dispatchEvent(event);

                    hasSession = true; // Now we have a session
                } catch (error) {
                    console.error('Failed to create session for LLM settings save:', error);
                    uiManager.showNotification('Failed to create session to save LLM settings', 'error');
                    return; // Abort saving LLM settings if session creation fails
                }
            }

            // Now save LLM settings to backend
            try {
                const result = await apiClient.updateLLMSettings(llmSettings);
                if (result.status === 'success') {
                    console.log('LLM settings saved successfully to backend');
                    // Optionally show a specific notification for LLM settings save
                    // this.showNotification('LLM settings saved', 'success');
                } else {
                    console.error('Failed to save LLM settings to backend:', result);
                    this.showNotification('Failed to save LLM settings', 'error');
                }
            } catch (error) {
                console.error('Error saving LLM settings via API:', error);
                this.showNotification('Error saving LLM settings', 'error');
            }

            // Apply LLM enabled setting to current game session if active
            if (apiClient.hasActiveSession()) {
                 // Use the state from the toggle just saved
                 const currentLLMEnabledState = llmEnabledToggle ? llmEnabledToggle.checked : this.settings.llmEnabled;
                 this.toggleLLM(currentLLMEnabledState)
                     .catch(error => console.error('Error toggling LLM after save:', error));
            }
        } else {
            // No LLM settings tab? Just log it.
             console.log("LLM settings tab not found, skipping backend save for LLM settings.");
        }
    }
}

// Make sure there's only one instance of UiManager
window.uiManager = window.uiManager || new UiManager();
