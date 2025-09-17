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
            settings: document.getElementById('settings-modal')
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

        // LLM settings
        this.llmSettings = {
            providers: {},
            agents: {}
        };
        
        // This flag is used to block any other code from modifying the model element
        this.isUpdatingModelOptions = false;
        
        // Set up MutationObserver to prevent INPUT elements being created
        this.setupMutationObserver();
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
        const messageElement = document.createElement('div');
        messageElement.className = `message ${type}`;
        messageElement.textContent = text;

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
        this.outputElement.scrollTop = this.outputElement.scrollHeight;
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
