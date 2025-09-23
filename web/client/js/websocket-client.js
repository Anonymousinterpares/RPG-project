/**
 * WebSocket Client for RPG Game
 * Handles real-time updates from the server
 */

class WebSocketClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl || window.location.origin;
        this.socket = null;
        this.isConnected = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000; // Start with 3 seconds
        this.sessionId = null;
        this.eventHandlers = {
            'connect': [],
            'disconnect': [],
            'game_state': [],
            'command_result': [],
            'game_loaded': [],
            'time_update': [],
            'stats_changed': [],
            'turn_order_update': [],
            'ui_bar_update_phase1': [],
            'ui_bar_update_phase2': [],
            'combat_log_set_html': [],
            'narrative': [],
            'journal_updated': [],
            'error': []
        };
        
        // Flag to prevent multiple connection attempts
        this.connecting = false;
    }

    /**
     * Connect to the WebSocket server
     * @param {string} sessionId - The game session ID
     */
    connect(sessionId) {
        if (!sessionId) {
            console.error('Cannot connect WebSocket: No session ID provided');
            return false;
        }

        // If already connected to the same session, don't reconnect
        if (this.socket && this.isConnected && this.sessionId === sessionId) {
            console.log('Already connected to this session, skipping reconnect');
            return true;
        }
        
        // If already in the process of connecting, don't start another connection
        if (this.connecting) {
            console.log('Connection already in progress, skipping');
            return false;
        }
        
        this.connecting = true;

        // If connected to a different session, disconnect first
        if (this.socket) {
            this.disconnect();
        }

        this.sessionId = sessionId;

        // Normalize the WebSocket URL (handle ws/wss protocol)
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsBaseUrl = this.baseUrl.replace(/^http(s?):\/\//, '');
        const wsUrl = `${protocol}//${wsBaseUrl}/ws/${sessionId}`;

        console.log(`Connecting to WebSocket: ${wsUrl}`);

        try {
            this.socket = new WebSocket(wsUrl);
            
            // Connection opened
            this.socket.addEventListener('open', (event) => {
                this.isConnected = true;
                this.connecting = false;
                this.reconnectAttempts = 0;
                console.log('WebSocket connection established');
                this._notifyEventHandlers('connect', { event });
            });
            
            // Listen for messages
            this.socket.addEventListener('message', (event) => {
                try {
                    const data = JSON.parse(event.data);
                    const eventType = data.type || 'unknown';
                    
                    console.log(`WebSocket received ${eventType} event:`, data);
                    
                    // Notify appropriate event handlers
                    this._notifyEventHandlers(eventType, data.data || data);
                    
                } catch (error) {
                    console.error('Error processing WebSocket message:', error);
                    this._notifyEventHandlers('error', { error, message: 'Error processing message' });
                }
            });
            
            // Connection closed
            this.socket.addEventListener('close', (event) => {
                this.isConnected = false;
                this.connecting = false;
                console.log('WebSocket connection closed', event.code, event.reason);
                this._notifyEventHandlers('disconnect', { code: event.code, reason: event.reason });
                
                // Attempt to reconnect if it wasn't a normal closure
                if (event.code !== 1000 && event.code !== 1001) {
                    this._attemptReconnect();
                }
            });
            
            // Connection error
            this.socket.addEventListener('error', (error) => {
                this.connecting = false;
                console.error('WebSocket error:', error);
                this._notifyEventHandlers('error', { error, message: 'Connection error' });
            });
            
            return true;
        } catch (error) {
            this.connecting = false;
            console.error('Failed to create WebSocket:', error);
            this._notifyEventHandlers('error', { error, message: 'Failed to create connection' });
            return false;
        }
    }

    /**
     * Disconnect from the WebSocket server
     */
    disconnect() {
        if (this.socket) {
            try {
                this.socket.close(1000, 'Client disconnected');
            } catch (error) {
                console.error('Error closing WebSocket:', error);
            } finally {
                this.socket = null;
                this.isConnected = false;
                this.connecting = false;
            }
        }
    }

    /**
     * Register an event handler
     * @param {string} eventType - The type of event to handle
     * @param {function} handler - The handler function
     */
    on(eventType, handler) {
        if (typeof handler !== 'function') {
            console.error('Event handler must be a function');
            return;
        }

        if (!this.eventHandlers[eventType]) {
            this.eventHandlers[eventType] = [];
        }
        
        // Check if handler is already registered
        if (this.eventHandlers[eventType].indexOf(handler) === -1) {
            this.eventHandlers[eventType].push(handler);
        }
    }

    /**
     * Remove an event handler
     * @param {string} eventType - The type of event
     * @param {function} handler - The handler function to remove
     */
    off(eventType, handler) {
        if (!this.eventHandlers[eventType]) return;

        const index = this.eventHandlers[eventType].indexOf(handler);
        if (index !== -1) {
            this.eventHandlers[eventType].splice(index, 1);
        }
    }
    
    /**
     * Remove all event handlers for a specific event type
     * @param {string} eventType - The type of event
     */
    offAll(eventType) {
        if (eventType && this.eventHandlers[eventType]) {
            this.eventHandlers[eventType] = [];
        }
    }

    /**
     * Send data to the server (if needed)
     * @param {object} data - The data to send
     */
    send(data) {
        if (!this.isConnected || !this.socket) {
            console.error('Cannot send: WebSocket not connected');
            return false;
        }

        try {
            this.socket.send(JSON.stringify(data));
            return true;
        } catch (error) {
            console.error('Error sending WebSocket message:', error);
            return false;
        }
    }

    /**
     * Check if the WebSocket is currently connected
     */
    checkConnected() {
        return this.isConnected && this.socket && this.socket.readyState === WebSocket.OPEN;
    }

    /**
     * Attempt to reconnect to the WebSocket server
     * @private
     */
    _attemptReconnect() {
        if (this.connecting) {
            return; // Already trying to connect
        }
        
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error(`Maximum reconnect attempts (${this.maxReconnectAttempts}) reached`);
            this._notifyEventHandlers('error', { message: 'Failed to reconnect after maximum attempts' });
            return;
        }

        // Exponential backoff
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts);
        
        console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts + 1}/${this.maxReconnectAttempts})`);
        
        setTimeout(() => {
            this.reconnectAttempts++;
            this.connect(this.sessionId);
        }, delay);
    }

    /**
     * Notify all registered handlers for an event type
     * @private
     */
    _notifyEventHandlers(eventType, data) {
        if (!this.eventHandlers[eventType]) return;

        for (const handler of this.eventHandlers[eventType]) {
            try {
                handler(data);
            } catch (error) {
                console.error(`Error in ${eventType} handler:`, error);
            }
        }
    }
}

// Create and export the singleton instance
const webSocketClient = new WebSocketClient();