/**
 * Cooking View - Wake lock, fullscreen, and checkbox management
 */

(function () {
    'use strict';

    // Wake Lock
    let wakeLock = null;

    /**
     * Request a wake lock to prevent screen from sleeping
     */
    async function requestWakeLock() {
        if ('wakeLock' in navigator) {
            try {
                wakeLock = await navigator.wakeLock.request('screen');
                console.log('Wake Lock activated');

                wakeLock.addEventListener('release', () => {
                    console.log('Wake Lock released');
                });
            } catch (err) {
                console.error(`Wake Lock error: ${err.name}, ${err.message}`);
            }
        } else {
            console.log('Wake Lock API not supported');
        }
    }

    /**
     * Release the wake lock
     */
    async function releaseWakeLock() {
        if (wakeLock !== null) {
            try {
                await wakeLock.release();
                wakeLock = null;
                console.log('Wake Lock manually released');
            } catch (err) {
                console.error(`Wake Lock release error: ${err.name}, ${err.message}`);
            }
        }
    }

    // Request wake lock when page loads
    requestWakeLock();

    // Re-request wake lock when page becomes visible (user returns to tab)
    document.addEventListener('visibilitychange', () => {
        if (wakeLock !== null && document.visibilityState === 'visible') {
            requestWakeLock();
        }
    });

    // Release wake lock when leaving the page
    window.addEventListener('beforeunload', () => {
        releaseWakeLock();
    });

    // Fullscreen functionality
    const fullscreenBtn = document.getElementById('fullscreenBtn');
    const fullscreenText = document.getElementById('fullscreenText');
    const cookingView = document.getElementById('cookingView');

    if (fullscreenBtn && cookingView) {
        fullscreenBtn.addEventListener('click', () => {
            if (!document.fullscreenElement &&
                !document.webkitFullscreenElement &&
                !document.mozFullScreenElement) {
                // Enter fullscreen
                if (cookingView.requestFullscreen) {
                    cookingView.requestFullscreen();
                } else if (cookingView.webkitRequestFullscreen) {
                    cookingView.webkitRequestFullscreen();
                } else if (cookingView.mozRequestFullScreen) {
                    cookingView.mozRequestFullScreen();
                }
            } else {
                // Exit fullscreen
                if (document.exitFullscreen) {
                    document.exitFullscreen();
                } else if (document.webkitExitFullscreen) {
                    document.webkitExitFullscreen();
                } else if (document.mozCancelFullScreen) {
                    document.mozCancelFullScreen();
                }
            }
        });

        // Update button text based on fullscreen state
        document.addEventListener('fullscreenchange', updateFullscreenButton);
        document.addEventListener('webkitfullscreenchange', updateFullscreenButton);
        document.addEventListener('mozfullscreenchange', updateFullscreenButton);

        function updateFullscreenButton() {
            if (document.fullscreenElement ||
                document.webkitFullscreenElement ||
                document.mozFullScreenElement) {
                fullscreenText.textContent = 'Exit Fullscreen';
                fullscreenBtn.querySelector('i').className = 'bi bi-fullscreen-exit';
            } else {
                fullscreenText.textContent = 'Fullscreen';
                fullscreenBtn.querySelector('i').className = 'bi bi-arrows-fullscreen';
            }
        }
    }

    // Checkbox state management
    const recipeId = window.location.pathname.split('/')[2]; // Extract recipe ID from URL
    const storageKey = `cooking-view-${recipeId}`;

    /**
     * Load checkbox states from localStorage
     */
    function loadCheckboxStates() {
        const saved = localStorage.getItem(storageKey);
        if (saved) {
            try {
                const states = JSON.parse(saved);

                // Restore ingredient checkboxes
                if (states.ingredients) {
                    states.ingredients.forEach(id => {
                        const checkbox = document.querySelector(`.ingredient-checkbox[data-id="${id}"]`);
                        if (checkbox) {
                            checkbox.checked = true;
                            const item = checkbox.closest('.cooking-ingredient-item');
                            if (item) {
                                item.classList.add('item-checked');
                            }
                        }
                    });
                }

                // Restore step checkboxes
                if (states.steps) {
                    states.steps.forEach(id => {
                        const checkbox = document.querySelector(`.step-checkbox[data-id="${id}"]`);
                        if (checkbox) {
                            checkbox.checked = true;
                            const item = checkbox.closest('.cooking-step-item');
                            if (item) {
                                item.classList.add('item-checked');
                            }
                        }
                    });
                }
            } catch (err) {
                console.error('Error loading checkbox states:', err);
            }
        }
    }

    /**
     * Save checkbox states to localStorage
     */
    function saveCheckboxStates() {
        const states = {
            ingredients: [],
            steps: [],
        };

        // Save checked ingredients
        document.querySelectorAll('.ingredient-checkbox:checked').forEach(checkbox => {
            const id = checkbox.getAttribute('data-id');
            if (id) {
                states.ingredients.push(id);
            }
        });

        // Save checked steps
        document.querySelectorAll('.step-checkbox:checked').forEach(checkbox => {
            const id = checkbox.getAttribute('data-id');
            if (id) {
                states.steps.push(id);
            }
        });

        localStorage.setItem(storageKey, JSON.stringify(states));
    }

    /**
     * Clear all checkbox states
     */
    function clearCheckboxStates() {
        // Uncheck all checkboxes
        document.querySelectorAll('.cooking-checkbox').forEach(checkbox => {
            checkbox.checked = false;
        });

        // Remove checked styling
        document.querySelectorAll('.item-checked').forEach(item => {
            item.classList.remove('item-checked');
        });

        // Clear from localStorage
        localStorage.removeItem(storageKey);
    }

    // Handle checkbox changes
    document.querySelectorAll('.cooking-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function () {
            const item = this.closest('.cooking-ingredient-item, .cooking-step-item');
            if (item) {
                if (this.checked) {
                    item.classList.add('item-checked');
                } else {
                    item.classList.remove('item-checked');
                }
            }
            saveCheckboxStates();
        });
    });

    // Clear checkboxes button
    const clearBtn = document.getElementById('clearCheckboxesBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            if (confirm('Clear all checkboxes?')) {
                clearCheckboxStates();
            }
        });
    }

    // Load saved checkbox states on page load
    loadCheckboxStates();
})();
