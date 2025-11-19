// Theme Switcher for Plated Recipe App

(function() {
    'use strict';

    const THEME_KEY = 'plated-theme';
    const DEFAULT_THEME = 'light';
    const THEMES = ['light', 'dark', 'warm', 'cool', 'forest'];

    // Get current theme from localStorage or use default
    function getCurrentTheme() {
        return localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
    }

    // Set theme on document
    function setTheme(theme) {
        if (!THEMES.includes(theme)) {
            theme = DEFAULT_THEME;
        }

        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem(THEME_KEY, theme);

        // Update active state on theme buttons
        updateThemeButtons(theme);
    }

    // Update active state on theme buttons
    function updateThemeButtons(activeTheme) {
        const buttons = document.querySelectorAll('.theme-btn');
        buttons.forEach(btn => {
            if (btn.getAttribute('data-theme') === activeTheme) {
                btn.classList.add('active');
            } else {
                btn.classList.remove('active');
            }
        });
    }

    // Initialize theme on page load
    function initTheme() {
        const currentTheme = getCurrentTheme();
        setTheme(currentTheme);
    }

    // Setup theme switcher event listeners
    function setupThemeSwitcher() {
        const buttons = document.querySelectorAll('.theme-btn');
        buttons.forEach(btn => {
            btn.addEventListener('click', function() {
                const theme = this.getAttribute('data-theme');
                setTheme(theme);
            });
        });
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initTheme();
            setupThemeSwitcher();
        });
    } else {
        initTheme();
        setupThemeSwitcher();
    }
})();
