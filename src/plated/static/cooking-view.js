/**
 * Cooking View - Wake lock and checkbox management
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

    // Load saved checkbox states on page load
    loadCheckboxStates();

    // ── Step Timers ──────────────────────────────────────────────────────────

    /**
     * Play a beeping alarm using Web Audio API for up to `duration` seconds.
     * Returns a cancel function that silences it immediately.
     */
    function createAlarm(duration) {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (!AudioCtx) { return function () {}; }
        const ctx = new AudioCtx();
        const beepOn = 0.2;
        const beepOff = 0.1;
        const period = beepOn + beepOff;
        const numBeeps = Math.floor(duration / period);
        const oscs = [];

        for (let i = 0; i < numBeeps; i++) {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = 'square';
            osc.frequency.value = 880;
            gain.gain.value = 0.3;
            const start = ctx.currentTime + i * period;
            osc.start(start);
            osc.stop(start + beepOn);
            oscs.push(osc);
        }

        return function cancel() {
            oscs.forEach(function (osc) {
                try { osc.stop(ctx.currentTime); } catch (_) {}
            });
            ctx.close();
        };
    }

    /**
     * Format seconds as MM:SS.
     */
    function formatCountdown(totalSeconds) {
        const m = Math.floor(totalSeconds / 60);
        const s = totalSeconds % 60;
        return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
    }

    /**
     * Build and return the timer widget element for a given step.
     * The widget manages its own state machine: idle → running → alarming → done.
     */
    function buildTimerWidget(minutes, labels) {
        const totalSeconds = minutes * 60;
        let remaining = totalSeconds;
        let intervalId = null;
        let cancelAlarm = null;
        let alarmTimeout = null;

        // Elements
        const widget = document.createElement('div');
        widget.className = 'step-timer-widget';

        const display = document.createElement('span');
        display.className = 'timer-display';
        display.setAttribute('aria-live', 'polite');

        const startBtn = document.createElement('button');
        startBtn.type = 'button';
        startBtn.className = 'btn btn-sm btn-outline-secondary';
        startBtn.innerHTML = '<i class="bi bi-stopwatch"></i> ' + minutes + ' min';

        const cancelBtn = document.createElement('button');
        cancelBtn.type = 'button';
        cancelBtn.className = 'btn btn-sm btn-outline-danger d-none';
        cancelBtn.textContent = labels.cancel;

        const dismissBtn = document.createElement('button');
        dismissBtn.type = 'button';
        dismissBtn.className = 'btn btn-sm btn-danger d-none';
        dismissBtn.textContent = labels.dismiss;

        const restartBtn = document.createElement('button');
        restartBtn.type = 'button';
        restartBtn.className = 'btn btn-sm btn-outline-secondary d-none';
        restartBtn.innerHTML = '<i class="bi bi-arrow-counterclockwise"></i> ' + labels.restart;

        widget.append(startBtn, display, cancelBtn, dismissBtn, restartBtn);

        function showIdle() {
            widget.classList.remove('timer-alarm');
            display.textContent = '';
            startBtn.classList.remove('d-none');
            cancelBtn.classList.add('d-none');
            dismissBtn.classList.add('d-none');
            restartBtn.classList.add('d-none');
        }

        function showRunning() {
            widget.classList.remove('timer-alarm');
            display.textContent = formatCountdown(remaining);
            startBtn.classList.add('d-none');
            cancelBtn.classList.remove('d-none');
            dismissBtn.classList.add('d-none');
            restartBtn.classList.add('d-none');
        }

        function showAlarming() {
            widget.classList.add('timer-alarm');
            display.textContent = '00:00';
            startBtn.classList.add('d-none');
            cancelBtn.classList.add('d-none');
            dismissBtn.classList.remove('d-none');
            restartBtn.classList.add('d-none');
        }

        function showDone() {
            widget.classList.remove('timer-alarm');
            display.textContent = '';
            startBtn.classList.add('d-none');
            cancelBtn.classList.add('d-none');
            dismissBtn.classList.add('d-none');
            restartBtn.classList.remove('d-none');
        }

        function stopCountdown() {
            if (intervalId !== null) {
                clearInterval(intervalId);
                intervalId = null;
            }
        }

        function stopAlarm() {
            if (cancelAlarm !== null) {
                cancelAlarm();
                cancelAlarm = null;
            }
            if (alarmTimeout !== null) {
                clearTimeout(alarmTimeout);
                alarmTimeout = null;
            }
        }

        startBtn.addEventListener('click', function () {
            stopCountdown();
            remaining = totalSeconds;
            showRunning();
            intervalId = setInterval(function () {
                remaining -= 1;
                if (remaining <= 0) {
                    stopCountdown();
                    showAlarming();
                    cancelAlarm = createAlarm(10);
                    alarmTimeout = setTimeout(function () {
                        stopAlarm();
                        showDone();
                    }, 10000);
                } else {
                    display.textContent = formatCountdown(remaining);
                }
            }, 1000);
        });

        cancelBtn.addEventListener('click', function () {
            stopCountdown();
            remaining = totalSeconds;
            showIdle();
        });

        dismissBtn.addEventListener('click', function () {
            stopAlarm();
            showDone();
        });

        restartBtn.addEventListener('click', function () {
            remaining = totalSeconds;
            showIdle();
        });

        showIdle();
        return widget;
    }

    // Initialise all step timers on page load
    document.querySelectorAll('[data-timer-minutes]').forEach(function (stepEl) {
        const minutes = parseInt(stepEl.getAttribute('data-timer-minutes'), 10);
        if (!minutes || minutes <= 0) { return; }
        const placeholder = stepEl.querySelector('.step-timer-widget');
        if (!placeholder) { return; }
        const labels = {
            cancel: placeholder.dataset.labelCancel || 'Cancel',
            dismiss: placeholder.dataset.labelDismiss || 'Dismiss',
            restart: placeholder.dataset.labelRestart || 'Restart',
        };
        placeholder.replaceWith(buildTimerWidget(minutes, labels));
    });
})();
