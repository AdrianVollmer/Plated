// Theme Switcher for Plated Recipe App

(function() {
    'use strict';

    const THEME_KEY = 'plated-theme';
    const DEFAULT_THEME = 'auto';
    const THEMES = ['light', 'dark', 'auto'];

    // Detect system theme preference
    function getSystemTheme() {
        if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            return 'dark';
        }
        return 'light';
    }

    // Get current theme from localStorage or use default
    function getCurrentTheme() {
        return localStorage.getItem(THEME_KEY) || DEFAULT_THEME;
    }

    // Resolve the actual theme to apply (handles 'auto' option)
    function resolveTheme(theme) {
        if (theme === 'auto') {
            return getSystemTheme();
        }
        return theme;
    }

    // Set theme on document
    function setTheme(theme) {
        if (!THEMES.includes(theme)) {
            theme = DEFAULT_THEME;
        }

        // Store the user's preference (which might be 'auto')
        localStorage.setItem(THEME_KEY, theme);

        // Apply the resolved theme to the document
        const resolvedTheme = resolveTheme(theme);
        document.documentElement.setAttribute('data-theme', resolvedTheme);

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

    // Listen for system theme changes when in auto mode
    function setupSystemThemeListener() {
        if (window.matchMedia) {
            const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)');
            darkModeQuery.addEventListener('change', function() {
                const currentTheme = getCurrentTheme();
                if (currentTheme === 'auto') {
                    // Re-apply theme to pick up system change
                    setTheme('auto');
                }
            });
        }
    }

    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            initTheme();
            setupThemeSwitcher();
            setupSystemThemeListener();
        });
    } else {
        initTheme();
        setupThemeSwitcher();
        setupSystemThemeListener();
    }
})();
