// API Configuration
// Change this to your Render backend URL after deployment
const CONFIG = {
    // For local development
    // API_BASE: 'http://localhost:8000/api',

    // For production - UPDATE THIS after deploying backend to Render
    API_BASE: window.location.hostname === 'localhost'
        ? 'http://localhost:8000/api'
        : 'https://equity-research-api.onrender.com/api'  // <-- Update this URL
};

// Export for use in other files
window.API_BASE = CONFIG.API_BASE;
