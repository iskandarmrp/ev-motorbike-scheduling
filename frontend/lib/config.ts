// Check if we're in a browser environment
const isBrowser = typeof window !== "undefined"

// Check if we're in a preview environment
const isPreview = isBrowser && window.location.hostname.includes("v0.dev")

// Get the current hostname (for development and production)
const hostname = isBrowser ? window.location.hostname : "localhost"

// Backend API and WebSocket configuration
export const API_BASE_URL = isPreview
  ? "/api" // Use relative path in preview (will be mocked)
  : `http://${hostname}:5000`

export const WEBSOCKET_URL = isPreview
  ? null // Disable WebSocket in preview
  : `http://${hostname}:5000`

// Map configuration
export const DEFAULT_MAP_CENTER = [-6.9, 107.6] // Bandung area
export const DEFAULT_MAP_ZOOM = 13
export const BASE_RADIUS = 500 // meters

// Demo mode for preview environments
export const DEMO_MODE = isPreview
