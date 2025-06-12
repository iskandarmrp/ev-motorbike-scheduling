export interface FleetEVMotorbike {
  id: number;
  max_speed: number;
  battery_id: number;
  latitude: number;
  longitude: number;
  status: string;
  online_status: string;
}

export interface BatterySwapStation {
  id: number;
  name: string;
  total_slots: number;
  latitude: number;
  longitude: number;
  alamat: string;
  slots: number[]; // battery IDs
}

export interface Battery {
  id: number;
  capacity: number;
  battery_now: number;
  battery_total_charged: number;
  cycle: number;
}

export interface Order {
  id: number;
  status: string;
  searching_time: number;
  assigned_motorbike_id: number | null;
  order_origin_lat: number;
  order_origin_lon: number;
  order_destination_lat: number;
  order_destination_lon: number;
  created_at: string;
  completed_at: string | null;
}

export interface SwapSchedule {
  id: number;
  ev_id: number;
  battery_station: number;
  slot: number;
  energy_distance: number;
  travel_time: number;
  waiting_time: number;
  exchanged_battery: number;
  received_battery: number;
  received_battery_cycle: number;
  status: string;
  scheduled_time: string;
}

export interface StatusMessage {
  jumlah_ev_motorbike: number;
  jumlah_battery_swap_station: number;
  fleet_ev_motorbikes: FleetEVMotorbike[];
  battery_swap_station: BatterySwapStation[];
  batteries: Battery[];
  orders: Order[];
  swap_schedules: SwapSchedule[];
}
