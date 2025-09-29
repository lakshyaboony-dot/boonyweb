// Global Theme Manager for Boony Web Application
// Centralized theme handling with random dynamic support

(function () {
    'use strict';

    const THEME_CONFIG = {
        storageKey: 'boony.theme',
        defaultTheme: 'light',
        themes: ['light', 'dark', 'golden', 'pink', 'lightblue', 'peach', 'purple', 'dynamic'],
        eventName: 'boony:theme-change'
    };

    // All themes (static + extra)
    const ALL_THEMES = {
        light: {
            '--bg-primary': '#ffffff',
            '--bg-secondary': 'rgba(248, 249, 250, 0.95)',
            '--text-primary': '#212529',
            '--text-secondary': 'rgba(33, 37, 41, 0.8)',
            '--text-muted': 'rgba(33, 37, 41, 0.6)',
            '--accent-color': '#007bff',
            '--accent-shadow': 'rgba(0, 123, 255, 0.5)',
            '--accent-glow': 'rgba(0, 123, 255, 0.8)',
            '--border-color': 'rgba(33, 37, 41, 0.1)',
            '--hover-bg': 'rgba(0, 123, 255, 0.1)',
            '--surface-secondary': 'rgba(33, 37, 41, 0.1)',
            '--surface-hover': 'rgba(33, 37, 41, 0.2)',
            '--error-color': '#dc3545',
            '--success-color': '#28a745',
            '--warning-color': '#ffc107'
        },
        dark: {
            '--bg-primary': '#1a1a1a',
            '--bg-secondary': 'rgba(42, 42, 42, 0.95)',
            '--text-primary': '#e9ecef',
            '--text-secondary': 'rgba(233, 236, 239, 0.8)',
            '--text-muted': 'rgba(233, 236, 239, 0.6)',
            '--accent-color': '#6c757d',
            '--accent-shadow': 'rgba(108, 117, 125, 0.5)',
            '--accent-glow': 'rgba(108, 117, 125, 0.8)',
            '--border-color': 'rgba(233, 236, 239, 0.1)',
            '--hover-bg': 'rgba(108, 117, 125, 0.2)',
            '--surface-secondary': 'rgba(233, 236, 239, 0.1)',
            '--surface-hover': 'rgba(233, 236, 239, 0.2)',
            '--error-color': '#dc3545',
            '--success-color': '#28a745',
            '--warning-color': '#ffc107'
        },
        golden: {
            '--bg-primary': '#fffaf0',
            '--bg-secondary': 'rgba(255, 250, 240, 0.95)',
            '--text-primary': '#5a3d00',
            '--text-secondary': 'rgba(90, 61, 0, 0.8)',
            '--text-muted': 'rgba(90, 61, 0, 0.6)',
            '--accent-color': '#daa520',
            '--accent-shadow': 'rgba(218, 165, 32, 0.5)',
            '--accent-glow': 'rgba(218, 165, 32, 0.8)',
            '--border-color': 'rgba(90, 61, 0, 0.2)',
            '--hover-bg': 'rgba(218, 165, 32, 0.1)',
            '--surface-secondary': 'rgba(90, 61, 0, 0.1)',
            '--surface-hover': 'rgba(90, 61, 0, 0.2)',
            '--error-color': '#d9534f',
            '--success-color': '#5cb85c',
            '--warning-color': '#f0ad4e'
        },
        pink: {
            '--bg-primary': '#fff0f6',
            '--bg-secondary': 'rgba(255, 240, 246, 0.95)',
            '--text-primary': '#660033',
            '--text-secondary': 'rgba(102, 0, 51, 0.8)',
            '--text-muted': 'rgba(102, 0, 51, 0.6)',
            '--accent-color': '#ff66b2',
            '--accent-shadow': 'rgba(255, 102, 178, 0.5)',
            '--accent-glow': 'rgba(255, 102, 178, 0.8)',
            '--border-color': 'rgba(102, 0, 51, 0.2)',
            '--hover-bg': 'rgba(255, 102, 178, 0.1)',
            '--surface-secondary': 'rgba(102, 0, 51, 0.1)',
            '--surface-hover': 'rgba(102, 0, 51, 0.2)',
            '--error-color': '#d9534f',
            '--success-color': '#5cb85c',
            '--warning-color': '#f0ad4e'
        },
        lightblue: {
            '--bg-primary': '#e6f7ff',
            '--bg-secondary': 'rgba(230, 247, 255, 0.95)',
            '--text-primary': '#003366',
            '--text-secondary': 'rgba(0, 51, 102, 0.8)',
            '--text-muted': 'rgba(0, 51, 102, 0.6)',
            '--accent-color': '#3399ff',
            '--accent-shadow': 'rgba(51, 153, 255, 0.5)',
            '--accent-glow': 'rgba(51, 153, 255, 0.8)',
            '--border-color': 'rgba(0, 51, 102, 0.2)',
            '--hover-bg': 'rgba(51, 153, 255, 0.1)',
            '--surface-secondary': 'rgba(0, 51, 102, 0.1)',
            '--surface-hover': 'rgba(0, 51, 102, 0.2)',
            '--error-color': '#d9534f',
            '--success-color': '#5cb85c',
            '--warning-color': '#f0ad4e'
        },
        peach: {
            '--bg-primary': '#fff5e6',
            '--bg-secondary': 'rgba(255, 245, 230, 0.95)',
            '--text-primary': '#663300',
            '--text-secondary': 'rgba(102, 51, 0, 0.8)',
            '--text-muted': 'rgba(102, 51, 0, 0.6)',
            '--accent-color': '#ff9966',
            '--accent-shadow': 'rgba(255, 153, 102, 0.5)',
            '--accent-glow': 'rgba(255, 153, 102, 0.8)',
            '--border-color': 'rgba(102, 51, 0, 0.2)',
            '--hover-bg': 'rgba(255, 153, 102, 0.1)',
            '--surface-secondary': 'rgba(102, 51, 0, 0.1)',
            '--surface-hover': 'rgba(102, 51, 0, 0.2)',
            '--error-color': '#d9534f',
            '--success-color': '#5cb85c',
            '--warning-color': '#f0ad4e'
        },
        purple: {
            '--bg-primary': '#f8f5ff',
            '--bg-secondary': 'rgba(248, 245, 255, 0.95)',
            '--text-primary': '#3d007a',
            '--text-secondary': 'rgba(61, 0, 122, 0.8)',
            '--text-muted': 'rgba(61, 0, 122, 0.6)',
            '--accent-color': '#9b59b6',
            '--accent-shadow': 'rgba(155, 89, 182, 0.5)',
            '--accent-glow': 'rgba(155, 89, 182, 0.8)',
            '--border-color': 'rgba(61, 0, 122, 0.2)',
            '--hover-bg': 'rgba(155, 89, 182, 0.1)',
            '--surface-secondary': 'rgba(61, 0, 122, 0.1)',
            '--surface-hover': 'rgba(61, 0, 122, 0.2)',
            '--error-color': '#d9534f',
            '--success-color': '#5cb85c',
            '--warning-color': '#f0ad4e'
        }
    };

    class ThemeManager {
        constructor() {
            this.currentTheme = null;
            this.init();
        }

        init() {
            const savedTheme = this.getSavedTheme();
            this.applyTheme(savedTheme);
            this.setupSystemThemeListener();
            this.setupMessageListener();
            this.setupThemeSelector();
            this.exposeGlobalFunctions();
        }

        getSavedTheme() {
            return localStorage.getItem(THEME_CONFIG.storageKey) || THEME_CONFIG.defaultTheme;
        }

        saveTheme(theme) {
            localStorage.setItem(THEME_CONFIG.storageKey, theme);
        }

        applyTheme(theme) {
            let selected = theme;

            if (theme === 'dynamic') {
                const keys = Object.keys(ALL_THEMES);
                const randomKey = keys[Math.floor(Math.random() * keys.length)];
                selected = randomKey;
                console.log(`🎲 Dynamic theme selected: ${selected}`);
            }

            // Remove old custom CSS
            const customStyles = document.getElementById('dynamic-theme-styles');
            if (customStyles) customStyles.remove();

            // Apply theme
            if (ALL_THEMES[selected]) {
                this.injectCustomCSS(ALL_THEMES[selected]);
            }

            document.documentElement.setAttribute('data-theme', selected);
            document.body.setAttribute('data-theme', selected);

            this.currentTheme = selected;
            this.broadcastThemeChange(selected, theme);
            this.saveTheme(theme);
        }

        injectCustomCSS(variables) {
            const style = document.createElement('style');
            style.id = 'dynamic-theme-styles';
            let cssText = ':root {';
            for (const [property, value] of Object.entries(variables)) {
                cssText += `${property}: ${value};`;
            }
            cssText += '}';
            style.textContent = cssText;
            document.head.appendChild(style);
        }

        broadcastThemeChange(actualTheme, originalTheme) {
            window.dispatchEvent(new CustomEvent(THEME_CONFIG.eventName, {
                detail: { theme: actualTheme, originalTheme: originalTheme || actualTheme }
            }));
        }

        setupSystemThemeListener() {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', () => {
                const currentSetting = this.getSavedTheme();
                if (currentSetting === 'auto') {
                    this.applyTheme('auto');
                }
            });
        }

        setupMessageListener() {
            window.addEventListener('message', (event) => {
                if (event.data && event.data.type === 'theme-change') {
                    const { theme, originalTheme } = event.data;
                    document.documentElement.setAttribute('data-theme', theme);
                    document.body.setAttribute('data-theme', theme);
                    this.currentTheme = theme;
                    if (originalTheme) this.saveTheme(originalTheme);
                }
            });
        }

        setupThemeSelector() {
            const themeSelect = document.getElementById('pref-theme');
            if (themeSelect) {
                themeSelect.value = this.getSavedTheme();
                themeSelect.addEventListener('change', (e) => {
                    const newTheme = e.target.value;
                    this.applyTheme(newTheme);
                });
            }
        }

        exposeGlobalFunctions() {
            window.themeManager = this;
            window.applyTheme = (theme) => this.applyTheme(theme);
            window.getCurrentTheme = () => this.currentTheme;
            window.getSavedTheme = () => this.getSavedTheme();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.themeManager = new ThemeManager();
            console.log('✅ ThemeManager initialized');
        });
    } else {
        window.themeManager = new ThemeManager();
        console.log('✅ ThemeManager initialized');
    }
})();
