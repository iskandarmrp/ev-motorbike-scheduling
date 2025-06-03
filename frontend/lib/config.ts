// Check if we're in a browser environment
const isBrowser = typeof window !== "undefined"

// Check if we're in a preview environment (v0.dev)
const isPreview =
  isBrowser && (window.location.hostname.includes("v0.dev") || window.location.hostname.includes("vercel.app"))

// Get the current hostname (for development and production)
const hostname = isBrowser ? window.location.hostname : "localhost"

// Backend API and WebSocket configuration for taxi system
export const API_BASE_URL = isPreview
  ? "/api" // Use relative path in preview (will be mocked)
  : `http://${hostname}:5000`

export const WEBSOCKET_URL = isPreview
  ? null // Disable WebSocket in preview
  : `http://${hostname}:5000`

// Backend API and WebSocket configuration for battery swap system
export const BATTERY_API_BASE_URL = isPreview
  ? "/api/battery" // Use relative path in preview (will be mocked)
  : "http://localhost:8000"

export const BATTERY_WEBSOCKET_URL = isPreview
  ? null
  : "ws://localhost:8000/ws/status";

// Map configuration
export const DEFAULT_MAP_CENTER = [-6.2088, 106.8456] // Jakarta area
export const DEFAULT_MAP_ZOOM = 13
export const BASE_RADIUS = 500 // meters

// Demo mode - only enable in preview environments, not for localhost development
export const DEMO_MODE = isPreview

// Debug logging
export const DEBUG_MODE = process.env.NODE_ENV === "development"

if (DEBUG_MODE && isBrowser) {
  console.log("Config Debug Info:", {
    hostname,
    isPreview,
    DEMO_MODE,
    API_BASE_URL,
    BATTERY_API_BASE_URL,
    currentURL: window.location.href,
  })
}
