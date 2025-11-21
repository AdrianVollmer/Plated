/**
 * Recipe Scaler - Handles dynamic scaling of recipe ingredients
 * Modal-based UI version
 */

class RecipeScaler {
    constructor(originalServings) {
        this.originalServings = originalServings;
        this.currentServings = originalServings;
        this.ingredients = [];
        this.scalingMode = 'servings'; // 'servings' or 'ingredient'
        this.targetIngredientIndex = null;
        this.targetIngredientAmount = null;
        this.isScaled = false;
    }

    /**
     * Parse ingredient amount string to a numeric value
     * Handles: whole numbers, decimals, fractions, mixed numbers, ranges
     */
    parseAmount(amountStr) {
        if (!amountStr || amountStr.trim() === '') {
            return null;
        }

        amountStr = amountStr.trim();

        // Handle ranges (e.g., "1-2", "2-3") - take the first value
        if (amountStr.includes('-')) {
            const parts = amountStr.split('-');
            amountStr = parts[0].trim();
        }

        // Handle fractions (e.g., "1/2", "3/4")
        if (amountStr.includes('/')) {
            const parts = amountStr.split(/\s+/);
            let total = 0;

            for (const part of parts) {
                if (part.includes('/')) {
                    const [num, denom] = part.split('/').map(Number);
                    if (!isNaN(num) && !isNaN(denom) && denom !== 0) {
                        total += num / denom;
                    }
                } else {
                    const num = parseFloat(part);
                    if (!isNaN(num)) {
                        total += num;
                    }
                }
            }

            return total > 0 ? total : null;
        }

        // Handle simple numbers
        const num = parseFloat(amountStr);
        return !isNaN(num) ? num : null;
    }

    /**
     * Format a numeric amount back to a display string
     */
    formatAmount(amount) {
        if (amount === null || amount === undefined) {
            return '';
        }

        // Round to 2 decimal places
        amount = Math.round(amount * 100) / 100;

        // Try to convert to fraction for common values
        const fractions = {
            0.125: '⅛',
            0.25: '¼',
            0.333: '⅓',
            0.375: '⅜',
            0.5: '½',
            0.625: '⅝',
            0.666: '⅔',
            0.75: '¾',
            0.875: '⅞'
        };

        const whole = Math.floor(amount);
        const decimal = amount - whole;

        // Check if decimal part matches a common fraction
        for (const [dec, frac] of Object.entries(fractions)) {
            if (Math.abs(decimal - parseFloat(dec)) < 0.01) {
                return whole > 0 ? `${whole} ${frac}` : frac;
            }
        }

        // Return as decimal if no fraction match
        return amount.toString();
    }

    /**
     * Register an ingredient for scaling
     */
    addIngredient(index, originalAmount, unit, name) {
        const parsedAmount = this.parseAmount(originalAmount);
        this.ingredients.push({
            index,
            originalAmount,
            originalAmountParsed: parsedAmount,
            unit,
            name
        });
    }

    /**
     * Scale recipe by servings count
     */
    scaleByServings(newServings) {
        this.scalingMode = 'servings';
        this.currentServings = newServings;
        this.targetIngredientIndex = null;
        this.targetIngredientAmount = null;

        const scaleFactor = newServings / this.originalServings;
        this.isScaled = Math.abs(scaleFactor - 1) > 0.001; // Consider scaled if factor differs by more than 0.1%
        return this.applyScaleFactor(scaleFactor);
    }

    /**
     * Scale recipe by a specific ingredient amount
     */
    scaleByIngredient(ingredientIndex, newAmount) {
        const ingredient = this.ingredients[ingredientIndex];
        if (!ingredient || !ingredient.originalAmountParsed) {
            return null;
        }

        const parsedNewAmount = this.parseAmount(newAmount);
        if (!parsedNewAmount) {
            return null;
        }

        this.scalingMode = 'ingredient';
        this.targetIngredientIndex = ingredientIndex;
        this.targetIngredientAmount = parsedNewAmount;

        const scaleFactor = parsedNewAmount / ingredient.originalAmountParsed;
        this.currentServings = Math.round(this.originalServings * scaleFactor * 100) / 100;
        this.isScaled = Math.abs(scaleFactor - 1) > 0.001;

        return this.applyScaleFactor(scaleFactor);
    }

    /**
     * Apply a scale factor to all ingredients
     */
    applyScaleFactor(scaleFactor) {
        const scaledIngredients = [];

        for (const ingredient of this.ingredients) {
            let scaledAmount = ingredient.originalAmount;

            if (ingredient.originalAmountParsed !== null) {
                const newAmount = ingredient.originalAmountParsed * scaleFactor;
                scaledAmount = this.formatAmount(newAmount);
            }

            scaledIngredients.push({
                index: ingredient.index,
                amount: scaledAmount,
                unit: ingredient.unit,
                name: ingredient.name
            });
        }

        return {
            servings: this.currentServings,
            ingredients: scaledIngredients,
            scaleFactor,
            isScaled: this.isScaled
        };
    }

    /**
     * Reset to original values
     */
    reset() {
        this.currentServings = this.originalServings;
        this.scalingMode = 'servings';
        this.targetIngredientIndex = null;
        this.targetIngredientAmount = null;
        this.isScaled = false;
        return this.scaleByServings(this.originalServings);
    }

    /**
     * Get preview text for current scaling
     */
    getPreviewText(newServings) {
        if (!newServings || newServings === this.originalServings) {
            return null;
        }
        const plural = newServings === 1 ? '' : 's';
        return `This will make ${newServings} serving${plural}`;
    }
}

// Initialize recipe scaler when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    const recipePage = document.getElementById('recipe-scaler-container');
    if (!recipePage) {
        return;
    }

    const originalServings = parseInt(recipePage.dataset.originalServings);
    const scaler = new RecipeScaler(originalServings);

    // Register all ingredients
    const ingredientElements = document.querySelectorAll('.ingredient-item');
    ingredientElements.forEach((element, index) => {
        const amount = element.dataset.amount || '';
        const unit = element.dataset.unit || '';
        const name = element.dataset.name || '';
        scaler.addIngredient(index, amount, unit, name);
    });

    // Modal elements
    const modal = document.getElementById('scaleRecipeModal');
    const modalServingsInput = document.getElementById('modal-servings-input');
    const modalIngredientSelect = document.getElementById('modal-ingredient-select');
    const modalIngredientAmount = document.getElementById('modal-ingredient-amount');
    const modalApplyButton = document.getElementById('modal-apply-button');
    const modalResetButton = document.getElementById('modal-reset-button');
    const scalePreview = document.getElementById('scale-preview');
    const scalePreviewText = document.getElementById('scale-preview-text');
    const servingsDisplay = document.getElementById('servings-display');

    let previewResult = null;

    // Reset modal when opened
    if (modal) {
        modal.addEventListener('show.bs.modal', function() {
            // Reset to current values
            if (modalServingsInput) {
                modalServingsInput.value = scaler.currentServings;
            }
            if (modalIngredientSelect) {
                modalIngredientSelect.selectedIndex = 0;
            }
            if (modalIngredientAmount) {
                modalIngredientAmount.value = '';
            }
            hidePreview();
        });
    }

    // Servings input preview
    if (modalServingsInput) {
        modalServingsInput.addEventListener('input', function() {
            const newServings = parseFloat(this.value);
            if (newServings && newServings > 0) {
                previewResult = scaler.scaleByServings(newServings);
                const previewText = scaler.getPreviewText(newServings);
                if (previewText) {
                    showPreview(previewText);
                } else {
                    hidePreview();
                }
            } else {
                hidePreview();
                previewResult = null;
            }
        });
    }

    // Ingredient scaling preview
    if (modalIngredientSelect && modalIngredientAmount) {
        const updateIngredientPreview = () => {
            const selectedIndex = parseInt(modalIngredientSelect.value);
            const newAmount = modalIngredientAmount.value;

            if (selectedIndex >= 0 && newAmount) {
                const result = scaler.scaleByIngredient(selectedIndex, newAmount);
                if (result) {
                    previewResult = result;
                    const previewText = scaler.getPreviewText(result.servings);
                    if (previewText) {
                        showPreview(previewText);
                    } else {
                        hidePreview();
                    }
                } else {
                    hidePreview();
                    previewResult = null;
                }
            } else {
                hidePreview();
                previewResult = null;
            }
        };

        modalIngredientAmount.addEventListener('input', updateIngredientPreview);
        modalIngredientSelect.addEventListener('change', function() {
            modalIngredientAmount.value = '';
            hidePreview();
            previewResult = null;
        });
    }

    // Apply button
    if (modalApplyButton) {
        modalApplyButton.addEventListener('click', function() {
            if (previewResult) {
                applyScaling(previewResult);
                // Close modal
                const bsModal = bootstrap.Modal.getInstance(modal);
                if (bsModal) {
                    bsModal.hide();
                }
            }
        });
    }

    // Reset button
    if (modalResetButton) {
        modalResetButton.addEventListener('click', function() {
            const result = scaler.reset();
            applyScaling(result);
            if (modalServingsInput) {
                modalServingsInput.value = originalServings;
            }
            if (modalIngredientSelect) {
                modalIngredientSelect.selectedIndex = 0;
            }
            if (modalIngredientAmount) {
                modalIngredientAmount.value = '';
            }
            hidePreview();
            previewResult = null;

            // Close modal
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
                bsModal.hide();
            }
        });
    }

    /**
     * Apply scaling to the page
     */
    function applyScaling(result) {
        if (!result) {
            return;
        }

        // Update servings display
        if (servingsDisplay) {
            servingsDisplay.textContent = result.servings;
        }

        // Update ingredient amounts
        result.ingredients.forEach(ingredient => {
            const element = ingredientElements[ingredient.index];
            if (element) {
                const amountSpan = element.querySelector('.ingredient-amount');
                if (amountSpan) {
                    let displayText = '';
                    if (ingredient.amount) {
                        displayText += ingredient.amount;
                    }
                    if (ingredient.unit) {
                        displayText += (displayText ? ' ' : '') + ingredient.unit;
                    }
                    amountSpan.textContent = displayText;

                    // Add visual indicator if scaled
                    if (result.isScaled && result.scaleFactor !== 1) {
                        amountSpan.classList.add('scaled');
                    } else {
                        amountSpan.classList.remove('scaled');
                    }
                }
            }
        });
    }

    /**
     * Show preview
     */
    function showPreview(text) {
        if (scalePreviewText && scalePreview) {
            scalePreviewText.textContent = text;
            scalePreview.style.display = 'block';
        }
    }

    /**
     * Hide preview
     */
    function hidePreview() {
        if (scalePreview) {
            scalePreview.style.display = 'none';
        }
    }
});
