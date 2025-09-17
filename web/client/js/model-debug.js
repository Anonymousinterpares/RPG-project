// Debug script to identify what's replacing the SELECT element with INPUT
window.addEventListener('DOMContentLoaded', function() {
    // Direct fix for OpenRouter model field
    function fixOpenRouterModelField() {
        // Get all provider dropdowns
        const providerSelects = [
            document.getElementById('narrator-provider'),
            document.getElementById('rule-checker-provider'),
            document.getElementById('context-evaluator-provider')
        ];
        
        // Watch for changes and fix the model field
        providerSelects.forEach(providerSelect => {
            if (!providerSelect) return;
            
            providerSelect.addEventListener('change', function(e) {
                const agent = this.id.split('-')[0];
                const provider = this.value;
                
                console.log(`Provider changed for ${agent} to ${provider}`);
                
                // If OpenRouter is selected, wait for the model field to be created
                // then check if it's an INPUT and replace it with a SELECT if needed
                if (provider === 'OPENROUTER') {
                    setTimeout(() => {
                        const modelElement = document.getElementById(`${agent}-model`);
                        console.log(`Model element for ${agent}: ${modelElement ? modelElement.tagName : 'not found'}`);
                        
                        if (modelElement && modelElement.tagName === 'INPUT') {
                            console.log(`Found INPUT for ${agent} model, replacing with SELECT`);
                            
                            // Create a replacement SELECT
                            const modelFormGroup = modelElement.closest('.form-group');
                            if (modelFormGroup) {
                                // Save any entered value
                                const currentValue = modelElement.value;
                                
                                // Clear the form group
                                modelFormGroup.innerHTML = '';
                                
                                // Create label
                                const label = document.createElement('label');
                                label.setAttribute('for', `${agent}-model`);
                                label.textContent = 'Model:';
                                modelFormGroup.appendChild(label);
                                
                                // Create new SELECT
                                const select = document.createElement('select');
                                select.id = `${agent}-model`;
                                
                                // Add OpenRouter models
                                const openRouterModels = [
                                    { value: 'google/gemini-2.0-flash-lite-preview-02-05:free', label: 'Google Gemini 2.0 Flash Lite (Free)' },
                                    { value: 'nousresearch/deephermes-3-llama-3-8b-preview:free', label: 'DeepHermes 3 Llama 3 8B (Free)' },
                                    { value: 'google/gemini-2.0-pro-exp-02-05:free', label: 'Google Gemini 2.0 Pro (Free)' },
                                    { value: 'mistralai/mistral-small-3.1-24b-instruct:free', label: 'Mistral Small 3.1 24B (Free)' },
                                    { value: 'google/gemini-2.0-flash-exp:free', label: 'Google Gemini 2.0 Flash (Free)' },
                                    // Include the current value if it's not empty
                                    ...(currentValue ? [{ value: currentValue, label: currentValue }] : [])
                                ];
                                
                                openRouterModels.forEach(model => {
                                    const option = document.createElement('option');
                                    option.value = model.value;
                                    option.textContent = model.label;
                                    select.appendChild(option);
                                });
                                
                                // Set the value if it exists
                                if (currentValue) {
                                    select.value = currentValue;
                                }
                                
                                // Add the select to the form group
                                modelFormGroup.appendChild(select);
                                
                                console.log(`Successfully replaced INPUT with SELECT for ${agent}`);
                            }
                        }
                    }, 100);
                }
            });
            
            // Also run once on page load to fix existing fields
            setTimeout(() => {
                if (providerSelect.value === 'OPENROUTER') {
                    const agent = providerSelect.id.split('-')[0];
                    const modelElement = document.getElementById(`${agent}-model`);
                    
                    if (modelElement && modelElement.tagName === 'INPUT') {
                        console.log(`Found INPUT for ${agent} model on load, replacing with SELECT`);
                        
                        // Create a replacement SELECT (same code as above)
                        const modelFormGroup = modelElement.closest('.form-group');
                        if (modelFormGroup) {
                            // Save any entered value
                            const currentValue = modelElement.value;
                            
                            // Clear the form group
                            modelFormGroup.innerHTML = '';
                            
                            // Create label
                            const label = document.createElement('label');
                            label.setAttribute('for', `${agent}-model`);
                            label.textContent = 'Model:';
                            modelFormGroup.appendChild(label);
                            
                            // Create new SELECT
                            const select = document.createElement('select');
                            select.id = `${agent}-model`;
                            
                            // Add OpenRouter models
                            const openRouterModels = [
                                { value: 'google/gemini-2.0-flash-lite-preview-02-05:free', label: 'Google Gemini 2.0 Flash Lite (Free)' },
                                { value: 'nousresearch/deephermes-3-llama-3-8b-preview:free', label: 'DeepHermes 3 Llama 3 8B (Free)' },
                                { value: 'google/gemini-2.0-pro-exp-02-05:free', label: 'Google Gemini 2.0 Pro (Free)' },
                                { value: 'mistralai/mistral-small-3.1-24b-instruct:free', label: 'Mistral Small 3.1 24B (Free)' },
                                { value: 'google/gemini-2.0-flash-exp:free', label: 'Google Gemini 2.0 Flash (Free)' },
                                // Include the current value if it's not empty
                                ...(currentValue ? [{ value: currentValue, label: currentValue }] : [])
                            ];
                            
                            openRouterModels.forEach(model => {
                                const option = document.createElement('option');
                                option.value = model.value;
                                option.textContent = model.label;
                                select.appendChild(option);
                            });
                            
                            // Set the value if it exists
                            if (currentValue) {
                                select.value = currentValue;
                            }
                            
                            // Add the select to the form group
                            modelFormGroup.appendChild(select);
                            
                            console.log(`Successfully replaced INPUT with SELECT for ${agent} on load`);
                        }
                    }
                }
            }, 500);
        });
    }
    
    // Run the fix
    setTimeout(fixOpenRouterModelField, 1000);
});
