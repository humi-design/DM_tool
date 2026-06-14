// Viraly Custom JavaScript

document.addEventListener('alpine:init', () => {
    // Global Alpine.js data and methods
    Alpine.data('app', () => ({
        sidebarOpen: false,
        notificationsOpen: false,
        
        init() {
            // Initialize app
            this.setupInterceptors();
            this.setupEventListeners();
        },
        
        setupInterceptors() {
            // HTMX request interceptor
            document.body.addEventListener('htmx:beforeRequest', (event) => {
                this.showLoading(event.detail.target);
            });
            
            document.body.addEventListener('htmx:afterRequest', (event) => {
                this.hideLoading(event.detail.target);
            });
            
            document.body.addEventListener('htmx:responseError', (event) => {
                this.showError('An error occurred. Please try again.');
            });
        },
        
        setupEventListeners() {
            // Close dropdowns on outside click
            document.addEventListener('click', (event) => {
                if (!event.target.closest('[x-data]')) {
                    this.notificationsOpen = false;
                }
            });
            
            // Keyboard shortcuts
            document.addEventListener('keydown', (event) => {
                // Cmd/Ctrl + K for search
                if ((event.metaKey || event.ctrlKey) && event.key === 'k') {
                    event.preventDefault();
                    document.querySelector('input[type="text"]')?.focus();
                }
            });
        },
        
        showLoading(target) {
            target.classList.add('htmx-loading');
        },
        
        hideLoading(target) {
            target.classList.remove('htmx-loading');
        },
        
        showError(message) {
            // Create toast notification
            const toast = document.createElement('div');
            toast.className = 'fixed bottom-4 right-4 bg-red-500 text-white px-6 py-3 rounded-lg shadow-lg animate-fadeIn z-50';
            toast.textContent = message;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.remove();
            }, 5000);
        },
        
        showSuccess(message) {
            const toast = document.createElement('div');
            toast.className = 'fixed bottom-4 right-4 bg-green-500 text-white px-6 py-3 rounded-lg shadow-lg animate-fadeIn z-50';
            toast.textContent = message;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.remove();
            }, 5000);
        }
    }));
});

// Utility functions
const Viraly = {
    // Format numbers
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        }
        if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    },
    
    // Format date
    formatDate(date) {
        return new Intl.DateTimeFormat('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        }).format(new Date(date));
    },
    
    // Format relative time
    formatRelativeTime(date) {
        const now = new Date();
        const then = new Date(date);
        const diff = now - then;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);
        
        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        return this.formatDate(date);
    },
    
    // Debounce function
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    // Copy to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch (err) {
            return false;
        }
    },
    
    // API helper
    async api(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content
            }
        };
        
        const response = await fetch(endpoint, { ...defaultOptions, ...options });
        
        if (!response.ok) {
            const error = await response.json().catch(() => ({ message: 'An error occurred' }));
            throw new Error(error.message || 'An error occurred');
        }
        
        return response.json();
    }
};

// Export for use
window.Viraly = Viraly;