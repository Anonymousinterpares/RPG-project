/**
 * Agent Settings Manager for LLM Configuration
 * Provides UI for configuring provider/model settings for different agents
 */

class AgentSettingsManager {
    constructor() {
        this.agentTypes = ['narrator', 'rule_checker', 'context_evaluator'];
        this.agentDisplayNames = {
            'narrator': 'Narrator Agent',
            'rule_checker': 'Rule Checker Agent',
            'context_evaluator': 'Context Evaluator Agent'
        };
        this.providerTypes = {
            'OPENAI': 'OpenAI',
            'GOOGLE': 'Google',
            'ANTHROPIC': 'Anthropic',
            'OPENROUTER': 'OpenRouter'
        };
        
        // Settings will be loaded from the API
        this.settings = {
            providers: {},
            agents: {}
        };
        
        // Initialize DOM elements
        this.initElements();
        this.initEventListeners();
    }
    
    /**
     * Initialize DOM elements for agent settings
     */
    initElements() {
        // Check if the settings tab already exists
        if (document.getElementById('agent-settings-tab')) {
            return;
        }
        
        // Add the agents tab to LLM settings
        const tabsContainer = document.querySelector('#llm-settings-tabs');
        if (tabsContainer) {
            const agentTab = document.createElement('button');
            agentTab.className = 'tab-button';
            agentTab.id = 'agent-settings-tab';
            agentTab.textContent = 'Agent Settings';
            agentTab.dataset.target = 'agent-settings-content';
            tabsContainer.appendChild(agentTab);
            
            // Create the content container
            const contentArea = document.querySelector('#llm-settings-content');
            const agentContent = document.createElement('div');
            agentContent.className = 'tab-content';
            agentContent.id = 'agent-settings-content';
            agentContent.style.display = 'none';
            
            // Create the agent settings form
            agentContent.innerHTML = this.createAgentSettingsHTML();
            contentArea.appendChild(agentContent);
        }
    }
    
    /**
     * Create HTML for agent settings tab
     */
    createAgentSettingsHTML() {
        let html = `
            <h3>Agent Configuration</h3>
            <p>Configure which AI provider and model to use for each agent type.</p>
            <div class="settings-grid">
        `;
        
        // Create settings for each agent type
        this.agentTypes.forEach(agentType => {
            const displayName = this.agentDisplayNames[agentType] || agentType;
            
            html += `
                <div class="settings-section">
                    <h4>${displayName}</h4>
                    <div class="form-group">
                        <label for="${agentType}-provider">AI Provider:</label>
                        <select id="${agentType}-provider" class="agent-provider-select" data-agent="${agentType}">
                            ${Object.entries(this.providerTypes).map(([key, value]) => 
                                `<option value="${key}">${value}</option>`
                            ).join('')}
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="${agentType}-model">Model:</label>
                        <select id="${agentType}-model" class="agent-model-select" data-agent="${agentType}">
                            <!-- Models will be populated dynamically -->
                            <option value="">Loading models...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="${agentType}-temperature">Temperature:</label>
                        <input type="range" id="${agentType}-temperature" class="agent-temperature" data-agent="${agentType}"
                               min="0" max="1" step="0.1" value="0.7">
                        <span class="temperature-value" id="${agentType}-temperature-value">0.7</span>
                    </div>
                </div>
            `;
        });
        
        html += `</div>
            <div class="settings-actions">
                <button id="save-agent-settings" class="btn btn-primary">Save Agent Settings</button>
            </div>
        `;
        
        return html;
    }
    
    /**
     * Initialize event listeners for agent settings UI
     */
    initEventListeners() {
        // Wait for elements to be added to DOM
        setTimeout(() => {
            // Provider selection changes
            document.querySelectorAll('.agent-provider-select').forEach(select => {
                select.addEventListener('change', (e) => {
                    const agentType = e.target.dataset.agent;
                    const providerType = e.target.value;
                    this.updateModelOptions(agentType, providerType);
                });
            });
            
            // Temperature slider changes
            document.querySelectorAll('.agent-temperature').forEach(slider => {
                slider.addEventListener('input', (e) => {
                    const agentType = e.target.dataset.agent;
                    const value = e.target.value;
                    document.getElementById(`${agentType}-temperature-value`).textContent = value;
                });
            });
            
            // Save button
            const saveButton = document.getElementById('save-agent-settings');
            if (saveButton) {
                saveButton.addEventListener('click', () => this.saveAgentSettings());
            }
            
            // Tab selection
            const agentTab = document.getElementById('agent-settings-tab');
            if (agentTab) {
                agentTab.addEventListener('click', () => this.loadAgentSettings());
            }
        }, 500);
    }
    
    /**
     * Load LLM settings from the API
     */
    async loadAgentSettings() {
        try {
            const response = await apiClient.getLLMSettings();
            this.settings = response;
            
            // Update UI with loaded settings
            this.updateAgentSettingsUI();
        } catch (error) {
            console.error('Error loading agent settings:', error);
            alert('Failed to load agent settings. Please try again.');
        }
    }
    
    /**
     * Update the agent settings UI with loaded settings
     */
    updateAgentSettingsUI() {
        const agents = this.settings.agents || {};
        
        // Update each agent's settings
        for (const agentType of this.agentTypes) {
            const agentSettings = agents[agentType] || {};
            
            // Set provider
            const providerSelect = document.getElementById(`${agentType}-provider`);
            if (providerSelect && agentSettings.provider_type) {
                providerSelect.value = agentSettings.provider_type;
                
                // Update model options for this provider
                this.updateModelOptions(agentType, agentSettings.provider_type);
                
                // Set model after options are updated
                setTimeout(() => {
                    const modelSelect = document.getElementById(`${agentType}-model`);
                    if (modelSelect && agentSettings.model) {
                        modelSelect.value = agentSettings.model;
                    }
                }, 100);
            }
            
            // Set temperature
            const temperatureSlider = document.getElementById(`${agentType}-temperature`);
            const temperatureValue = document.getElementById(`${agentType}-temperature-value`);
            if (temperatureSlider && temperatureValue && agentSettings.temperature !== undefined) {
                temperatureSlider.value = agentSettings.temperature;
                temperatureValue.textContent = agentSettings.temperature;
            }
        }
    }
    
    /**
     * Update model options based on selected provider
     */
    updateModelOptions(agentType, providerType) {
        const modelSelect = document.getElementById(`${agentType}-model`);
        if (!modelSelect) return;
        
        // Clear current options
        modelSelect.innerHTML = '';
        
        // Get available models for this provider
        let availableModels = [];
        
        // Check providers in loaded settings
        const providers = this.settings.providers || {};
        const providerKey = providerType.toLowerCase();
        
        if (providers[providerKey] && providers[providerKey].available_models) {
            availableModels = providers[providerKey].available_models;
        } else {
            // Default models if not found in settings
            const defaultModels = {
                'OPENAI': ['gpt-4o', 'gpt-4-turbo', 'gpt-3.5-turbo'],
                'GOOGLE': ['gemini-2.0-flash', 'gemini-2.0-pro'],
                'ANTHROPIC': ['claude-3-opus', 'claude-3-sonnet', 'claude-3-haiku'],
                'OPENROUTER': ['anthropic/claude-3-haiku', 'anthropic/claude-3-sonnet', 'anthropic/claude-3-opus', 'google/gemini-pro']
            };
            
            availableModels = defaultModels[providerType] || [];
        }
        
        // Add options for available models
        availableModels.forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelSelect.appendChild(option);
        });
        
        // If no models found, add a placeholder
        if (availableModels.length === 0) {
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No models available';
            modelSelect.appendChild(option);
        }
    }
    
    /**
     * Save agent settings to the API
     */
    async saveAgentSettings() {
        try {
            // Collect settings from UI
            const agentSettings = {};
            
            for (const agentType of this.agentTypes) {
                const providerSelect = document.getElementById(`${agentType}-provider`);
                const modelSelect = document.getElementById(`${agentType}-model`);
                const temperatureSlider = document.getElementById(`${agentType}-temperature`);
                
                if (providerSelect && modelSelect && temperatureSlider) {
                    agentSettings[agentType] = {
                        provider_type: providerSelect.value,
                        model: modelSelect.value,
                        temperature: parseFloat(temperatureSlider.value)
                    };
                }
            }
            
            // Save to API
            await apiClient.updateLLMSettings({ agents: agentSettings });
            
            // Show success message
            alert('Agent settings saved successfully!');
            
        } catch (error) {
            console.error('Error saving agent settings:', error);
            alert('Failed to save agent settings. Please try again.');
        }
    }
}

// Initialize the agent settings manager
const agentSettingsManager = new AgentSettingsManager();