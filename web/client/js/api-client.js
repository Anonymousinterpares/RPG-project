/**
 * API Client for RPG Game Web Interface
 * Handles all API communication with the backend server
 */

class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
        this.sessionId = null;
        this.token = null;

        // Attempt to load session from localStorage
        this.loadSession();
    }

    /**
     * Save the current session to localStorage
     */
    saveSession() {
        if (this.sessionId) {
            localStorage.setItem('rpg_session_id', this.sessionId);
        }
        if (this.token) {
            localStorage.setItem('rpg_auth_token', this.token);
        }
    }

    /**
     * Load session from localStorage
     */
    loadSession() {
        this.sessionId = localStorage.getItem('rpg_session_id');
        this.token = localStorage.getItem('rpg_auth_token');
    }

    /**
     * Clear the current session
     */
    clearSession() {
        this.sessionId = null;
        this.token = null;
        localStorage.removeItem('rpg_session_id');
        localStorage.removeItem('rpg_auth_token');
    }

    /**
     * Check if there's an active session
     */
    hasActiveSession() {
        return !!this.sessionId;
    }

    /**
     * Set the authentication token
     */
    setAuthToken(token) {
        this.token = token;
        this.saveSession();
    }

    /**
     * Helper method to build the full URL for an API endpoint
     */
    buildUrl(endpoint) {
        return `${this.baseUrl}/api/${endpoint}`;
    }

    /**
     * Helper method to build request headers
     */
    getHeaders() {
        const headers = {
            'Content-Type': 'application/json',
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        return headers;
    }

    /**
     * Login to the server
     */
    async login(username, password) {
        try {
            // Create form data
            const formData = new URLSearchParams();
            formData.append('username', username);
            formData.append('password', password);

            const response = await fetch(`${this.baseUrl}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData,
            });

            if (!response.ok) {
                throw new Error('Login failed');
            }

            const data = await response.json();
            this.setAuthToken(data.access_token);
            return data;

        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    /**
     * Start a new game with extended character creation options
     * 
     * @param {string} playerName - The name of the player character
     * @param {Object} options - Additional character creation options
     * @param {string} [options.race="Human"] - Character race
     * @param {string} [options.path="Wanderer"] - Character class/path
     * @param {string} [options.background="Commoner"] - Character background
     * @param {string} [options.sex="Male"] - Character sex/gender
     * @param {string} [options.characterImage=null] - Path to character portrait image
     * @param {boolean} [options.useLLM=true] - Whether to enable LLM functionality
     * @returns {Promise<Object>} - Promise resolving to session data
     */
    async createNewGame(playerName, options = {}) {
        try {
            const defaults = {
                race: "Human",
                path: "Wanderer", 
                background: "Commoner",
                sex: "Male",
                characterImage: null,
                useLLM: true
            };
            
            const settings = { ...defaults, ...options };
            
            const requestBody = {
                player_name: playerName,
                race: settings.race,
                path: settings.path,
                background: settings.background,
                sex: settings.sex,
                character_image: settings.characterImage,
                use_llm: settings.useLLM,
                origin_id: settings.origin_id || null,
                stats: settings.stats || null
            };
            
            const response = await fetch(this.buildUrl('new_game'), {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                throw new Error('Failed to create new game');
            }

            const data = await response.json();
            this.sessionId = data.session_id;
            this.saveSession();
            return data;

        } catch (error) {
            console.error('Create game error:', error);
            throw error;
        }
    }

    /**
     * Send a command to the game
     */
    async sendCommand(command) {
        if (!this.sessionId) {
            throw new Error('No active game session');
        }

        try {
            const response = await fetch(this.buildUrl(`command/${this.sessionId}`), {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ command }),
            });

            if (!response.ok) {
                throw new Error('Failed to process command');
            }

            return await response.json();

        } catch (error) {
            console.error('Command error:', error);
            throw error;
        }
    }

    /**
     * Save the current game
     */
    async saveGame(saveName = null) {
        if (!this.sessionId) {
            throw new Error('No active game session');
        }

        try {
            const response = await fetch(this.buildUrl(`save_game/${this.sessionId}`), {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ save_name: saveName }),
            });

            if (!response.ok) {
                throw new Error('Failed to save game');
            }

            return await response.json();

        } catch (error) {
            console.error('Save game error:', error);
            throw error;
        }
    }

    /**
     * Load a saved game
     */
    async loadGame(saveId) {
        if (!this.sessionId) {
            throw new Error('No active game session');
        }

        try {
            const response = await fetch(this.buildUrl(`load_game/${this.sessionId}`), {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ save_id: saveId }),
            });

            if (!response.ok) {
                throw new Error('Failed to load game');
            }

            return await response.json();

        } catch (error) {
            console.error('Load game error:', error);
            throw error;
        }
    }

    /**
     * Get a list of all saves
     */
    async listSaves() {
        try {
            const response = await fetch(this.buildUrl('list_saves'), {
                method: 'GET',
                headers: this.getHeaders(),
            });

            if (!response.ok) {
                throw new Error('Failed to list saves');
            }

            return await response.json();

        } catch (error) {
            console.error('List saves error:', error);
            throw error;
        }
    }

    /**
     * End the current game session
     */
    async endSession() {
        if (!this.sessionId) {
            return;
        }

        try {
            const response = await fetch(this.buildUrl(`end_session/${this.sessionId}`), {
                method: 'DELETE',
                headers: this.getHeaders(),
            });

            if (!response.ok) {
                console.warn('Failed to end session properly');
            }

            this.clearSession();
            return true;

        } catch (error) {
            console.error('End session error:', error);
            this.clearSession();
            return false;
        }
    }

    /**
     * Get LLM settings.
     * @returns {Promise<Object>} - Promise resolving to LLM settings
     */
    async getLLMSettings() {
        try {
            const response = await fetch(this.buildUrl('llm/settings'), {
                method: 'GET',
                headers: this.getHeaders()
            });
            
            if (!response.ok) {
                throw new Error('Failed to retrieve LLM settings');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Get LLM settings error:', error);
            throw error;
        }
    }

    /**
     * Update LLM settings.
     * @param {Object} settings - LLM settings to update
     * @param {Object} settings.providers - Provider settings (optional)
     * @param {Object} settings.agents - Agent settings (optional)
     * @returns {Promise<Object>} - Promise resolving to response data
     */
    async updateLLMSettings(settings) {
        try {
            const response = await fetch(this.buildUrl('llm/settings'), {
                method: 'POST',
                headers: {
                    ...this.getHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(settings)
            });
            
            if (!response.ok) {
                throw new Error('Failed to update LLM settings');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Update LLM settings error:', error);
            throw error;
        }
    }

    /**
     * Toggle LLM functionality for the current game session.
     * @param {boolean} enabled - Whether to enable LLM functionality
     * @returns {Promise<Object>} - Promise resolving to response data
     */
    async toggleLLM(enabled) {
        if (!this.sessionId) {
            throw new Error('No active game session');
        }
        
        try {
            const response = await fetch(this.buildUrl(`llm/toggle/${this.sessionId}`), {
                method: 'POST',
                headers: {
                    ...this.getHeaders(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ enabled })
            });
            
            if (!response.ok) {
                throw new Error('Failed to toggle LLM functionality');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Toggle LLM error:', error);
            throw error;
        }
    }

    /**
     * Get a list of all available character icons
     * @returns {Promise<Object>} - Promise resolving to icon data
     */
    async getCharacterIcons() {
        try {
            const response = await fetch(this.buildUrl('character-icons'), {
                method: 'GET',
                headers: this.getHeaders(),
            });

            if (!response.ok) {
                throw new Error('Failed to get character icons');
            }

            return await response.json();

        } catch (error) {
            console.error('Get character icons error:', error);
            throw error;
        }
    }

    /** Filtered character icons by race/class/sex */
    async getFilteredCharacterIcons(race, path, sex='Other') {
        try {
            const params = new URLSearchParams({ race, path, sex });
            const response = await fetch(this.buildUrl(`character-icons/filter?${params.toString()}`), {
                method: 'GET', headers: this.getHeaders()
            });
            if (!response.ok) throw new Error('Failed to get filtered character icons');
            return await response.json();
        } catch (e) {
            console.error('Get filtered icons error:', e);
            throw e;
        }
    }

    /** Config endpoints */
    async getConfigRaces() {
        const r = await fetch(this.buildUrl('config/races'), { headers: this.getHeaders() });
        if (!r.ok) throw new Error('Failed to load races');
        return await r.json();
    }
    async getConfigClasses() {
        const r = await fetch(this.buildUrl('config/classes'), { headers: this.getHeaders() });
        if (!r.ok) throw new Error('Failed to load classes');
        return await r.json();
    }
    async getConfigOrigins() {
        const r = await fetch(this.buildUrl('config/origins'), { headers: this.getHeaders() });
        if (!r.ok) throw new Error('Failed to load origins');
        return await r.json();
    }

    /**
     * Check if the server is available
     */
    async checkServerStatus() {
        try {
            const response = await fetch(`${this.baseUrl}/api/list_saves`, {
                method: 'GET',
                headers: this.getHeaders(),
            });

            return response.ok;

        } catch (error) {
            console.error('Server check error:', error);
            return false;
        }
    }
    /** Fetch detailed UI state for the right panel and status bar */
    async getUIState() {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`ui/state/${this.sessionId}`), { headers: this.getHeaders() });
        if (!resp.ok) throw new Error('Failed to fetch UI state');
        return await resp.json();
    }

    /** Fetch inventory listing/currency/weight */
    async getInventory() {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`inventory/${this.sessionId}`), { headers: this.getHeaders() });
        if (!resp.ok) throw new Error('Failed to fetch inventory');
        return await resp.json();
    }

    async equipItem(itemId, slot = null) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`inventory/equip/${this.sessionId}`), {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ item_id: itemId, slot })
        });
        if (!resp.ok) throw new Error('Failed to equip');
        return await resp.json();
    }

    async unequip(slotOrItemId) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`inventory/unequip/${this.sessionId}`), {
            method: 'POST', headers: this.getHeaders(), body: JSON.stringify({ slot: slotOrItemId, item_id: slotOrItemId })
        });
        if (!resp.ok) throw new Error('Failed to unequip');
        return await resp.json();
    }

    async useItem(itemId) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`inventory/use/${this.sessionId}`), {
            method: 'POST', headers: this.getHeaders(), body: JSON.stringify({ item_id: itemId })
        });
        if (!resp.ok) throw new Error('Failed to use item');
        return await resp.json();
    }

    async dropItem(itemId) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`inventory/drop/${this.sessionId}`), {
            method: 'POST', headers: this.getHeaders(), body: JSON.stringify({ item_id: itemId })
        });
        if (!resp.ok) throw new Error('Failed to drop item');
        return await resp.json();
    }

    // Journal endpoints
    async updateJournalCharacter(text) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`journal/character/${this.sessionId}`), { method:'POST', headers: this.getHeaders(), body: JSON.stringify({ text }) });
        if (!resp.ok) throw new Error('Failed to save character notes');
        return await resp.json();
    }
    async updateObjectiveStatus(quest_id, objective_id, payload) {
        if (!this.sessionId) throw new Error('No active game session');
        const body = { quest_id, objective_id };
        if (typeof payload.completed === 'boolean') body.completed = payload.completed;
        if (typeof payload.failed === 'boolean') body.failed = payload.failed;
        const resp = await fetch(this.buildUrl(`journal/objective_status/${this.sessionId}`), { method:'POST', headers: this.getHeaders(), body: JSON.stringify(body) });
        if (!resp.ok) throw new Error('Failed to update objective');
        return await resp.json();
    }
    async abandonQuest(quest_id) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`journal/abandon/${this.sessionId}`), { method:'POST', headers: this.getHeaders(), body: JSON.stringify({ quest_id }) });
        if (!resp.ok) throw new Error('Failed to abandon quest');
        return await resp.json();
    }

    async addJournalNote(text) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`journal/add_note/${this.sessionId}`), { method:'POST', headers: this.getHeaders(), body: JSON.stringify({ text }) });
        if (!resp.ok) throw new Error('Failed to add note');
        return await resp.json();
    }
    async deleteJournalNote(noteId) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`journal/delete_note/${this.sessionId}/${encodeURIComponent(noteId)}`), { method:'DELETE', headers: this.getHeaders() });
        if (!resp.ok) throw new Error('Failed to delete note');
        return await resp.json();
    }

    /** Get stat modifiers for a specific stat key (e.g., 'STR', 'MELEE_ATTACK') */
    async getStatModifiers(statKey) {
        if (!this.sessionId) throw new Error('No active game session');
        const resp = await fetch(this.buildUrl(`stats/modifiers/${this.sessionId}?stat=${encodeURIComponent(statKey)}`), {
            method: 'GET', headers: this.getHeaders()
        });
        if (!resp.ok) throw new Error('Failed to get stat modifiers');
        return await resp.json();
    }
}

// Create and export the singleton instance
const apiClient = new ApiClient();