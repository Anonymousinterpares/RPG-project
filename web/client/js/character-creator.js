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
        
        // Load icons from server
        loadCharacterIcons();
    }
    
    // Load character icons from the server
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
        const sexValue = event.target.value;
        // Could filter icons by sex if we had metadata about which icons are for which sex
        console.log('Sex selection changed to:', sexValue);
    }
    
    // Get the currently selected icon
    function getSelectedIcon() {
        return selectedIcon;
    }
    
    // Validate the character creation form
    function validateForm() {
        const nameInput = document.getElementById('new-player-name');
        
        if (!nameInput || !nameInput.value.trim()) {
            alert('Please enter a character name');
            return false;
        }
        
        return true;
    }
    
    // Public API
    return {
        init,
        getSelectedIcon,
        validateForm
    };
})();

// Initialize the module when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', CharacterCreator.init);

// Export the module for use in other scripts
window.CharacterCreator = CharacterCreator;
