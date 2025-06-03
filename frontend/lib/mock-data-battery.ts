import type {
  MotorbikeState,
  BatteryStation,
  OrderSchedule,
  SwapSchedule,
  FleetActivityLogEntry,
} from "@/components/dashboard-battery-swap"

export const mockMotorbikeStates: Record<string, MotorbikeState> = {
  "0": {
    id: 0,
    status: "idle",
    online_status: "online",
    current_lat: -6.2088,
    current_lon: 106.8456,
    battery_now: 85,
    battery_max: 100,
  },
  "1": {
    id: 1,
    status: "on_order",
    online_status: "online",
    current_lat: -6.1944,
    current_lon: 106.8229,
    battery_now: 65,
    battery_max: 100,
    assigned_order_id: 101,
  },
  "2": {
    id: 2,
    status: "heading_to_station",
    online_status: "online",
    current_lat: -6.2297,
    current_lon: 106.8175,
    battery_now: 15,
    battery_max: 100,
    assigned_station_id: 1,
  },
  "3": {
    id: 3,
    status: "charging",
    online_status: "online",
    current_lat: -6.2615,
    current_lon: 106.7812,
    battery_now: 45,
    battery_max: 100,
    assigned_station_id: 2,
  },
  "4": {
    id: 4,
    status: "offline",
    online_status: "offline",
    current_lat: -6.1751,
    current_lon: 106.865,
    battery_now: 30,
    battery_max: 100,
  },
}

export const mockBatteryStations: Record<string, BatteryStation> = {
  "0": {
    id: 0,
    name: "Station_Central",
    lat: -6.2088,
    lon: 106.8456,
    available_batteries: 8,
    charging_batteries: 2,
    total_capacity: 10,
  },
  "1": {
    id: 1,
    name: "Station_North",
    lat: -6.1944,
    lon: 106.8229,
    available_batteries: 5,
    charging_batteries: 3,
    total_capacity: 8,
  },
  "2": {
    id: 2,
    name: "Station_South",
    lat: -6.2615,
    lon: 106.7812,
    available_batteries: 3,
    charging_batteries: 5,
    total_capacity: 8,
  },
}

export const mockOrderSchedules: OrderSchedule[] = [
  {
    id: 101,
    status: "active",
    order_origin_lat: -6.1944,
    order_origin_lon: 106.8229,
    order_destination_lat: -6.2297,
    order_destination_lon: 106.8175,
    assigned_motorbike_id: 1,
    created_at: new Date(Date.now() - 300000).toISOString(), // 5 minutes ago
  },
  {
    id: 102,
    status: "searching",
    order_origin_lat: -6.2088,
    order_origin_lon: 106.8456,
    order_destination_lat: -6.1751,
    order_destination_lon: 106.865,
    created_at: new Date(Date.now() - 60000).toISOString(), // 1 minute ago
  },
  {
    id: 100,
    status: "done",
    order_origin_lat: -6.2615,
    order_origin_lon: 106.7812,
    order_destination_lat: -6.2088,
    order_destination_lon: 106.8456,
    assigned_motorbike_id: 0,
    created_at: new Date(Date.now() - 900000).toISOString(), // 15 minutes ago
    completed_at: new Date(Date.now() - 600000).toISOString(), // 10 minutes ago
  },
]

export const mockSwapSchedules: SwapSchedule[] = [
  {
    motorbike_id: 2,
    station_id: 1,
    scheduled_time: 125.5,
    priority: 9,
    status: "scheduled",
  },
  {
    motorbike_id: 3,
    station_id: 2,
    scheduled_time: 120.0,
    priority: 7,
    status: "in_progress",
  },
  {
    motorbike_id: 4,
    station_id: 0,
    scheduled_time: 140.0,
    priority: 6,
    status: "scheduled",
  },
]

export const mockFleetActivityLogs: FleetActivityLogEntry[] = [
  {
    timestamp: new Date(Date.now() - 30000).toISOString(),
    motorbike_id: 1,
    action: "order_assigned",
    details: "Assigned to order #101",
    location: { lat: -6.1944, lon: 106.8229 },
  },
  {
    timestamp: new Date(Date.now() - 120000).toISOString(),
    motorbike_id: 2,
    action: "battery_swap_started",
    details: "Started battery swap at Station_North",
    location: { lat: -6.1944, lon: 106.8229 },
  },
  {
    timestamp: new Date(Date.now() - 180000).toISOString(),
    motorbike_id: 0,
    action: "order_completed",
    details: "Completed order #100",
    location: { lat: -6.2088, lon: 106.8456 },
  },
  {
    timestamp: new Date(Date.now() - 240000).toISOString(),
    motorbike_id: 4,
    action: "went_offline",
    details: "Motorbike went offline due to maintenance",
    location: { lat: -6.1751, lon: 106.865 },
  },
  {
    timestamp: new Date(Date.now() - 300000).toISOString(),
    motorbike_id: 3,
    action: "status_changed",
    details: "Status changed from idle to heading_to_station",
    location: { lat: -6.2297, lon: 106.8175 },
  },
]
