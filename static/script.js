
// Handle base URL for AJAX requests when in a subdirectory
if (typeof window.appBaseUrl === 'undefined') {
    // Default to empty string if not set in base.html
    window.appBaseUrl = '';
}
