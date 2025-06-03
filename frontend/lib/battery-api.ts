import { BATTERY_API_BASE_URL, DEBUG_MODE } from "./config"

export interface BatterySwapStatus {
  jumlah_ev_motorbike: number
  jumlah_battery_swap_station: number
  fleet_ev_motorbikes: any[]
  battery_swap_station: any[]
  batteries: any[]
  total_order: number
  order_search_driver: any[]
  order_active: any[]
  order_done: any[]
  order_failed: any[]
  time_now: string | number
}

export async function fetchBatteryStatus(): Promise<BatterySwapStatus> {
  try {
    if (DEBUG_MODE) {
      console.log(`Fetching battery status from: ${BATTERY_API_BASE_URL}/status`)
    }

    const response = await fetch(`${BATTERY_API_BASE_URL}/status`, {
      method: "GET",
      mode: "cors",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const data = await response.json()

    if (DEBUG_MODE) {
      console.log("Raw API response:", data)
      console.log("API response type check:", {
        jumlah_ev_motorbike: typeof data.jumlah_ev_motorbike,
        fleet_ev_motorbikes: Array.isArray(data.fleet_ev_motorbikes),
        battery_swap_station: Array.isArray(data.battery_swap_station),
      })
    }

    // Transform the data to ensure proper types
    return {
      jumlah_ev_motorbike: Number(data.jumlah_ev_motorbike) || 0,
      jumlah_battery_swap_station: Number(data.jumlah_battery_swap_station) || 0,
      fleet_ev_motorbikes: Array.isArray(data.fleet_ev_motorbikes) ? data.fleet_ev_motorbikes : [],
      battery_swap_station: Array.isArray(data.battery_swap_station) ? data.battery_swap_station : [],
      batteries: Array.isArray(data.batteries) ? data.batteries : [],
      total_order: Number(data.total_order) || 0,
      order_search_driver: Array.isArray(data.order_search_driver) ? data.order_search_driver : [],
      order_active: Array.isArray(data.order_active) ? data.order_active : [],
      order_done: Array.isArray(data.order_done) ? data.order_done : [],
      order_failed: Array.isArray(data.order_failed) ? data.order_failed : [],
      time_now: data.time_now || new Date().toISOString(),
    }
  } catch (error) {
    console.error("Failed to fetch battery status:", error)
    throw error
  }
}

export async function fetchBatteryRoot(): Promise<any> {
  try {
    const response = await fetch(`${BATTERY_API_BASE_URL}/`, {
      method: "GET",
      mode: "cors",
      headers: {
        "Content-Type": "application/json",
      },
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    return await response.json()
  } catch (error) {
    console.error("Failed to fetch battery root:", error)
    throw error
  }
}
