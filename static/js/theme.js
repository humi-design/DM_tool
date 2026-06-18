/**
 * Viraly Theme Manager
 * Handles dark/light mode toggle with localStorage persistence
 */

class ThemeManager {
  constructor() {
    this.storageKey = 'viraly-theme';
    this.theme = this.getStoredTheme() || this.getSystemPreference();
    this.init();
  }

  getSystemPreference() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }

  getStoredTheme() {
    const stored = localStorage.getItem(this.storageKey);
    if (stored === 'dark' || stored === 'light') {
      return stored;
    }
    return null;
  }

  setStoredTheme(theme) {
    localStorage.setItem(this.storageKey, theme);
  }

  init() {
    this.applyTheme(this.theme);
    this.bindEvents();
    this.watchSystemPreference();
  }

  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    this.theme = theme;
    this.updateToggleButton(theme);
  }

  toggle() {
    const newTheme = this.theme === 'dark' ? 'light' : 'dark';
    this.setStoredTheme(newTheme);
    this.applyTheme(newTheme);
  }

  updateToggleButton(theme) {
    const toggle = document.querySelector('.theme-toggle');
    if (toggle) {
      const sun = toggle.querySelector('.sun');
      const moon = toggle.querySelector('.moon');
      if (sun && moon) {
        if (theme === 'dark') {
          sun.style.display = 'block';
          moon.style.display = 'none';
        } else {
          sun.style.display = 'none';
          moon.style.display = 'block';
        }
      }
    }
  }

  bindEvents() {
    document.addEventListener('click', (e) => {
      const toggle = e.target.closest('.theme-toggle');
      if (toggle) {
        e.preventDefault();
        this.toggle();
      }
    });
  }

  watchSystemPreference() {
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        if (!this.getStoredTheme()) {
          this.applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  }
}

// Initialize theme manager
document.addEventListener('DOMContentLoaded', () => {
  window.themeManager = new ThemeManager();
});