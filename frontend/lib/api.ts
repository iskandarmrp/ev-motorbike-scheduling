import { API_BASE_URL, DEMO_MODE } from "./config"
import { mockLogin, mockRegister } from "./mock-data"

/**
 * Makes an API request and handles common error cases
 */
export async function apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // In demo mode (preview), use mock data
  if (DEMO_MODE) {
    console.log("Running in demo mode, using mock data")

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
  console.log(`Making API request to: ${url}`)

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
