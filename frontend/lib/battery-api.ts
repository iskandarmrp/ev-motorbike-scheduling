import { BATTERY_API_BASE_URL } from "./config";

export interface BatterySwapStatus {
  jumlah_ev_motorbike: number;
  jumlah_battery_swap_station: number;
  fleet_ev_motorbikes: any[];
  battery_swap_station: any[];
  batteries: any[];
  total_order: number;
  order_search_driver: any[];
  order_active: any[];
  order_done: any[];
  order_failed: any[];
  total_waiting: number;
  average_waiting_time: number;
  total_low_battery_idle: number;
  time_now: string | number;
  swap_schedules: any[];
  avg_daily_incomes: number;
}

export async function fetchBatteryRoot(): Promise<any> {
  try {
    const response = await fetch(`${BATTERY_API_BASE_URL}/`, {
      method: "GET",
      mode: "cors",
      headers: {
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Failed to fetch battery root:", error);
    throw error;
  }
}
