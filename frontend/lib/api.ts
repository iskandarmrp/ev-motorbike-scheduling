import { API_BASE_URL, BATTERY_API_BASE_URL, DEMO_MODE, DEBUG_MODE } from "./config"
import { mockLogin, mockRegister } from "./mock-data"

/**
 * Makes an API request and handles common error cases
 */
export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // In demo mode (preview), use mock data
  if (DEMO_MODE) {
    if (DEBUG_MODE) console.log("Running in demo mode, using mock data")

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 500))

    // Return mock data based on endpoint
    if (endpoint === "/api/loginOperator" && options.method === "POST") {
      return mockLogin(options) as unknown as T
    }

    if (endpoint === "/api/registerOperator" && options.method === "POST") {
      return mockRegister(options) as unknown as T
    }

    throw new Error("Endpoint not supported in demo mode")
  }

  // Real API request
  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE_URL}${endpoint}`
  if (DEBUG_MODE) console.log(`Making API request to: ${url}`)

  // Set default headers if not provided
  if (!options.headers) {
    options.headers = {
      "Content-Type": "application/json",
    }
  }

  // Add auth token if available
  const token = localStorage.getItem("token")
  if (token && options.headers) {
    ;(options.headers as Record<string, string>)["Authorization"] = `Bearer ${token}`
  }

  // Include credentials for CORS
  options.credentials = "include"

  try {
    const response = await fetch(url, options)

    if (!response.ok) {
      const errorText = await response.text()
      try {
        // Try to parse as JSON
        const errorData = JSON.parse(errorText)
        throw new Error(errorData.error || `Request failed with status ${response.status}`)
      } catch (parseError) {
        // If not JSON, use text
        throw new Error(`Request failed: ${response.status} ${response.statusText}`)
      }
    }

    return await response.json()
  } catch (error) {
    console.error("API request failed:", error)
    if (error instanceof TypeError && error.message.includes("Failed to fetch")) {
      throw new Error(`Could not connect to the server at ${url}. Please check if the backend is running.`)
    }
    throw error
  }
}

/**
 * Makes an API request to the battery swap backend with better error handling
 */
export async function batteryApiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // In demo mode (preview), use mock data
  if (DEMO_MODE) {
    if (DEBUG_MODE) console.log("Running in demo mode for battery API, using mock data")

    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 500))

    // Return mock data based on endpoint
    if (endpoint === "/status" || endpoint === "/api/battery/status") {
      return {
        jumlah_ev_motorbike: 100,
        jumlah_battery_swap_station: 10,
        fleet_ev_motorbikes: [],
        battery_swap_station: [],
        batteries: [],
        total_order: 45,
        order_search_driver: [],
        order_active: [],
        order_done: [],
        order_failed: [],
        time_now: new Date().toISOString(),
      } as unknown as T
    }

    throw new Error("Battery API endpoint not supported in demo mode")
  }

  // Real API request to battery swap backend
  const url = endpoint.startsWith("http") ? endpoint : `${BATTERY_API_BASE_URL}${endpoint}`
  if (DEBUG_MODE) console.log(`Making Battery API request to: ${url}`)

  // Set default headers if not provided
  if (!options.headers) {
    options.headers = {
      "Content-Type": "application/json",
    }
  }

  // Don't include credentials for external API to avoid CORS issues
  // options.credentials = "include"

  try {
    const response = await fetch(url, {
      ...options,
      mode: "cors", // Explicitly set CORS mode
    })

    if (!response.ok) {
      const errorText = await response.text()
      try {
        // Try to parse as JSON
        const errorData = JSON.parse(errorText)
        throw new Error(errorData.error || `Request failed with status ${response.status}`)
      } catch (parseError) {
        // If not JSON, use text
        throw new Error(`Request failed: ${response.status} ${response.statusText}`)
      }
    }

    return await response.json()
  } catch (error) {
    console.error("Battery API request failed:", error)
    if (error instanceof TypeError && error.message.includes("Failed to fetch")) {
      throw new Error(
        `Could not connect to the battery swap server at ${url}. Please ensure:\n1. FastAPI backend is running on port 8000\n2. CORS is properly configured\n3. No firewall blocking the connection`,
      )
    }
    throw error
  }
}

/**
 * Check if the battery API is available
 */
export async function checkBatteryApiHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${BATTERY_API_BASE_URL}/`, {
      method: "GET",
      mode: "cors",
      headers: {
        "Content-Type": "application/json",
      },
    })
    return response.ok
  } catch (error) {
    if (DEBUG_MODE) console.log("Battery API health check failed:", error)
    return false
  }
}
