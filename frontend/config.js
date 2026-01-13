// API Configuration
const CONFIG = {
    API_BASE: window.location.hostname === 'localhost'
        ? 'http://localhost:8000/api'
        : 'https://equity-research-api-xbrq.onrender.com/api'
};

// Export for use in other files
window.API_BASE = CONFIG.API_BASE;
