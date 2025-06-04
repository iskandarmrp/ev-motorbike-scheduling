"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MapContainerBattery } from "./map-container-battery";
import { MotorbikeTable } from "./motorbike-table";
import { BatteryStationTable } from "./battery-station-table";
import { BatteryTable } from "./battery-table";
import { OrderTable } from "./order-table";
import { SwapScheduleTable } from "./swap-schedule-table";
import { FleetActivityLog } from "./fleet-activity-log";
import { ConnectionStatus } from "./connection-status";
import { DEMO_MODE, DEBUG_MODE, BATTERY_WEBSOCKET_URL } from "@/lib/config";
import { type BatterySwapStatus } from "@/lib/battery-api";
import { Battery, Zap, Truck, CheckCircle, AlertTriangle } from "lucide-react";

export interface Battery {
  id: string;
  capacity: number;
  battery_now: number;
  battery_total_charged: number;
  cycle: number;
  location: string;
  location_id: string;
}

export interface MotorbikeState {
  id: string;
  current_lat: number;
  current_lon: number;
  status: string;
  battery_id: number;
  battery_now: number;
  battery_max: number;
  battery_cycle: number;
  online_status: string;
  assigned_order_id?: string;
  assigned_swap_schedule?: SwapSchedule;
}

export interface BatteryStation {
  id: string;
  name: string;
  total_slots: number;
  lat: number;
  lon: number;
  slots: Battery[];
  available_batteries: number;
  charging_batteries: number;
}

export interface OrderSchedule {
  id: string;
  status: string;
  assigned_motorbike_id?: string;
  order_origin_lat: number;
  order_origin_lon: number;
  order_destination_lat: number;
  order_destination_lon: number;
  created_at: string;
  completed_at?: string;
}

export interface SwapSchedule {
  id: string;
  ev_id: string;
  battery_now: number;
  battery_cycle: number;
  battery_station: string;
  slot: string;
  energy_distance: number;
  travel_time: number;
  waiting_time: number;
  exchanged_battery: number;
  received_battery: number;
  received_battery_cycle: number;
  status: string;
  scheduled_time: string;
}

// Mock data for fallback
const mockMotorbikeStates: Record<string, MotorbikeState> = {
  MB001: {
    id: "MB001",
    current_lat: -6.2088,
    current_lon: 106.8456,
    status: "idle",
    battery_id: 999,
    battery_now: 80,
    battery_max: 100,
    battery_cycle: 20,
    online_status: "online",
  },
};

const mockBatteryStations: Record<string, BatteryStation> = {
  BS001: {
    id: "BS001",
    name: "Station Central Jakarta",
    total_slots: 3,
    lat: -6.2088,
    lon: 106.8456,
    slots: [
      {
        id: "1",
        capacity: 100,
        battery_now: 30,
        battery_total_charged: 240,
        cycle: 2,
        location: "station",
        location_id: "BS001",
      },
    ],
    available_batteries: 8,
    charging_batteries: 2,
  },
};

const mockOrderSchedules: OrderSchedule[] = [
  {
    id: "ORD001",
    status: "active",
    assigned_motorbike_id: "MB002",
    order_origin_lat: -6.21,
    order_origin_lon: 106.847,
    order_destination_lat: -6.22,
    order_destination_lon: 106.83,
    created_at: new Date().toISOString(),
  },
];

const mockSwapSchedules: SwapSchedule[] = [
  {
    id: "1",
    ev_id: "1",
    battery_now: 15,
    battery_cycle: 23,
    battery_station: "1",
    slot: "1",
    energy_distance: 123,
    travel_time: 126,
    waiting_time: 12,
    exchanged_battery: 10,
    received_battery: 100,
    received_battery_cycle: 22,
    status: "on going",
    scheduled_time: "1-2-3",
  },
];

const mockBatteries: Battery[] = [
  {
    id: "BAT001",
    capacity: 100,
    battery_now: 90,
    battery_total_charged: 300,
    cycle: 10,
    location: "station",
    location_id: "BS001",
  },
  {
    id: "BAT002",
    capacity: 100,
    battery_now: 45,
    battery_total_charged: 150,
    cycle: 5,
    location: "motorbike",
    location_id: "MB001",
  },
];

export function DashboardBatterySwap() {
  const [status, setStatus] = useState<BatterySwapStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [dataSource, setDataSource] = useState<"api" | "mock">("mock");

  // State for map data
  const [motorbikeStates, setMotorbikeStates] =
    useState<Record<string, MotorbikeState>>(mockMotorbikeStates);
  const [batteryStations, setBatteryStations] =
    useState<Record<string, BatteryStation>>(mockBatteryStations);
  const [orderSchedules, setOrderSchedules] =
    useState<OrderSchedule[]>(mockOrderSchedules);
  const [swapSchedules, setSwapSchedules] =
    useState<SwapSchedule[]>(mockSwapSchedules);
  const [activityLogs, setActivityLogs] = useState<string[]>([]);
  const [batteries, setBatteries] = useState<Battery[]>(mockBatteries);

  // Helper functions for safe data conversion - FIXED VERSION
  const safeString = (value: any, defaultValue = ""): string => {
    if (value === null || value === undefined || value === "")
      return defaultValue;
    return String(value);
  };

  const safeNumber = (value: any, defaultValue = 0): number => {
    // Handle the case where value is 0 (which is valid)
    if (value === null || value === undefined) return defaultValue;
    const num = Number(value);
    return isNaN(num) ? defaultValue : num;
  };

  const safeArray = (value: any): any[] => {
    return Array.isArray(value) ? value : [];
  };

  // Transform API data to component format - FIXED VERSION
  const transformApiData = (data: BatterySwapStatus) => {
    const batteryMap = new Map(safeArray(data.batteries).map((b) => [b.id, b]));
    const motorbikeMap: Record<string, MotorbikeState> = {};
    const stationMap: Record<string, BatteryStation> = {};
    const orders: OrderSchedule[] = [];
    const swaps: SwapSchedule[] = [];

    console.log("swap schedules", data.swap_schedules);

    const allBatteries: Battery[] = safeArray(data.batteries).map((b) => ({
      id: safeString(b.id),
      capacity: safeNumber(b.capacity),
      battery_now: safeNumber(b.battery_now),
      battery_total_charged: safeNumber(b.battery_total_charged),
      cycle: safeNumber(b.cycle),
      location: safeString(b.location),
      location_id: safeString(b.location_id),
    }));

    const allSwapSchedules: SwapSchedule[] = safeArray(data.swap_schedules).map(
      (s) => ({
        id: safeString(s.id),
        ev_id: safeString(s.ev_id),
        battery_now: safeNumber(s.battery_now),
        battery_cycle: safeNumber(s.battery_cycle),
        battery_station: safeString(s.battery_station),
        slot: safeString(s.slot),
        energy_distance: safeNumber(s.energy_distance),
        travel_time: safeNumber(s.travel_time),
        waiting_time: safeNumber(s.waiting_time),
        exchanged_battery: safeNumber(s.exchanged_battery),
        received_battery: safeNumber(s.received_battery),
        received_battery_cycle: safeNumber(s.received_battery_cycle),
        status: safeString(s.status),
        scheduled_time: safeString(s.scheduled_time),
      })
    );

    safeArray(data.fleet_ev_motorbikes).forEach((m, i) => {
      const battery = batteryMap.get(m.battery_id);
      const id = safeString(m.id, `MB${i}`);
      motorbikeMap[id] = {
        id,
        current_lat: safeNumber(m.latitude),
        current_lon: safeNumber(m.longitude),
        status: safeString(m.status),
        battery_id: safeNumber(m.battery_id),
        battery_now: safeNumber(battery?.battery_now),
        battery_max: safeNumber(battery?.capacity),
        battery_cycle: safeNumber(battery?.cycle),
        online_status: safeString(m.online_status),
        assigned_order_id: m.order_id ?? undefined,
        assigned_swap_schedule:
          m.swap_schedule && Object.keys(m.swap_schedule).length > 0
            ? m.swap_schedule
            : undefined,
      };
    });

    safeArray(data.battery_swap_station).forEach((s, i) => {
      const id = safeString(s.id, `BS${i}`);

      const battery_list = safeArray(s.slots).map((batteryId) => {
        const battery = batteryMap.get(batteryId); // Ambil detail dari batteryMap
        return {
          id: safeString(batteryId),
          capacity: safeNumber(battery?.capacity),
          battery_now: safeNumber(battery?.battery_now),
          battery_total_charged: safeNumber(battery?.battery_total_charged),
          cycle: safeNumber(battery?.cycle),
          location: safeString(battery?.location),
          location_id: safeString(battery?.location_id),
        };
      });

      const available_batteries = battery_list.filter(
        (b) => safeNumber(b.battery_now) >= 80
      ).length;
      const charging_batteries = battery_list.length - available_batteries;

      stationMap[id] = {
        id,
        name: safeString(s.name),
        total_slots: safeNumber(s.total_slots),
        lat: safeNumber(s.latitude),
        lon: safeNumber(s.longitude),
        slots: battery_list,
        available_batteries: safeNumber(available_batteries),
        charging_batteries: safeNumber(charging_batteries),
      };
    });

    [
      ...safeArray(data.order_search_driver),
      ...safeArray(data.order_active),
      ...safeArray(data.order_done),
      ...safeArray(data.order_failed),
    ].forEach((o, i) => {
      orders.push({
        id: safeString(o.id, `ORD${i}`),
        status: safeString(o.status),
        assigned_motorbike_id: o.assigned_motorbike_id ?? undefined,
        order_origin_lat: safeNumber(o.order_origin_lat),
        order_origin_lon: safeNumber(o.order_origin_lon),
        order_destination_lat: safeNumber(o.order_destination_lat),
        order_destination_lon: safeNumber(o.order_destination_lon),
        created_at: safeString(o.created_at, new Date().toISOString()),
        completed_at: o.completed_at ?? undefined,
      });
    });

    // safeArray(data.batteries).forEach((b, i) => {
    //   if (b.motorbike_id && b.station_id) {
    //     swaps.push({
    //       id: safeString(b.id, `SWAP${i}`),
    //       motorbike_id: safeString(b.motorbike_id),
    //       station_id: safeString(b.station_id),
    //       priority: safeNumber(b.priority, 1),
    //       scheduled_time: safeNumber(b.scheduled_time, 0),
    //       status: safeString(b.status, "scheduled"),
    //     });
    //   }
    // });

    setMotorbikeStates(motorbikeMap);
    setBatteryStations(stationMap);
    setOrderSchedules(orders);
    setSwapSchedules(allSwapSchedules);
    setBatteries(allBatteries);
    setActivityLogs((prev) =>
      [
        `[${new Date().toLocaleTimeString()}] WebSocket update received: ${
          Object.keys(motorbikeMap).length
        } motorbikes`,
        ...prev,
      ].slice(0, 50)
    );
  };

  function formatTime(isoString: string) {
    const date = new Date(isoString);

    return (
      date.toLocaleString("id-ID", {
        timeZone: "Asia/Jakarta",
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }) + " WIB"
    );
  }

  // console.log("Ini batere", batteries);

  useEffect(() => {
    if (DEMO_MODE || !BATTERY_WEBSOCKET_URL) return;

    const socket = new WebSocket(BATTERY_WEBSOCKET_URL);

    socket.onopen = () => {
      setError(null);
      console.log("✅ WebSocket connected");
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus(data);
        transformApiData(data);
        setLastUpdated(new Date());
        setDataSource("api");
        setLoading(false);
      } catch (err) {
        console.error("WebSocket data error:", err);
      }
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
      setError("WebSocket error");
      setDataSource("mock");
    };

    socket.onclose = () => {
      setError("Disconnected");
      console.warn("WebSocket closed");
    };

    return () => socket.close();
  }, []);

  if (loading)
    return <div className="text-center p-12">Loading dashboard...</div>;

  // if (error) {
  //   return (
  //     <div className="container mx-auto p-6">
  //       <ConnectionStatus />
  //       <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
  //         <h2 className="text-lg font-semibold text-red-800">
  //           API Connection Error
  //         </h2>
  //         <p className="text-red-600">
  //           Failed to fetch data from battery swap backend: {error}
  //         </p>
  //         <div className="mt-2 space-x-2">
  //           <button
  //             onClick={fetchStatusData}
  //             className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
  //           >
  //             Retry Connection
  //           </button>
  //           <button
  //             onClick={() =>
  //               window.open("http://localhost:8000/docs", "_blank")
  //             }
  //             className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
  //           >
  //             View API Docs
  //           </button>
  //         </div>
  //       </div>
  //     </div>
  //   );
  // }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">
            Electric Motorbikes Fleet Management
          </h1>
          <p className="text-muted-foreground">Battery Swap System Dashboard</p>
          <span className="text-xs text-muted-foreground">
            Last updated:{" "}
            {status?.time_now && formatTime(status.time_now.toString())}
          </span>
        </div>
        {/* <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-sm">
            {DEMO_MODE ? "Demo Mode" : "Live Data"}
          </Badge>
          <Badge
            variant={dataSource === "api" ? "default" : "secondary"}
            className="text-sm"
          >
            {dataSource === "api" ? "API Data" : "Mock Data"}
          </Badge>
        </div> */}
      </div>

      {/* <ConnectionStatus /> */}

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Motorbikes
            </CardTitle>
            <Truck className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {safeNumber(status?.jumlah_ev_motorbike, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Electric motorbikes in fleet
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Battery Stations
            </CardTitle>
            <Battery className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {safeNumber(status?.jumlah_battery_swap_station, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Swap stations available
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Orders</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {safeArray(status?.order_active).length}
            </div>
            <p className="text-xs text-muted-foreground">Orders in progress</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Orders</CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {safeNumber(status?.total_order, 0)}
            </div>
            <p className="text-xs text-muted-foreground">Orders today</p>
          </CardContent>
        </Card>
      </div>

      {/* API Data Debug Info (only in development) */}
      {/* {DEBUG_MODE && status && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              API Response Debug (Development Only)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-2">
              <strong>Data Source:</strong>{" "}
              {dataSource === "api"
                ? "Real API Data"
                : "Mock Data (API returned empty)"}
            </div>
            <div className="mb-2">
              <strong>Current State:</strong>
              <ul className="text-sm ml-4">
                <li>Motorbikes: {Object.keys(motorbikeStates).length}</li>
                <li>Stations: {Object.keys(batteryStations).length}</li>
                <li>Orders: {orderSchedules.length}</li>
                <li>Swaps: {swapSchedules.length}</li>
              </ul>
            </div>
            <pre className="text-xs bg-gray-100 p-4 rounded overflow-auto max-h-40">
              {JSON.stringify(status, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )} */}

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="motorbikes">Motorbikes</TabsTrigger>
          <TabsTrigger value="stations">Battery Swap Stations</TabsTrigger>
          <TabsTrigger value="batteries">Batteries</TabsTrigger>
          <TabsTrigger value="orders">Orders</TabsTrigger>
          <TabsTrigger value="schedule">Swap Schedule</TabsTrigger>
          <TabsTrigger value="logs">Activity Logs</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>Fleet Map</CardTitle>
                <CardDescription>
                  Real-time location of electric motorbikes and battery stations
                </CardDescription>
              </CardHeader>
              <CardContent>
                <MapContainerBattery
                  motorbikeStates={motorbikeStates}
                  batteryStations={batteryStations}
                  orderSchedules={orderSchedules}
                />
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="motorbikes">
          <Card>
            <CardHeader>
              <CardTitle>Motorbike Fleet</CardTitle>
              <CardDescription>
                Status and location of all electric motorbikes
              </CardDescription>
            </CardHeader>
            <CardContent>
              <MotorbikeTable motorbikeStates={motorbikeStates} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="stations">
          <Card>
            <CardHeader>
              <CardTitle>Battery Swap Stations</CardTitle>
              <CardDescription>
                Battery availability and station status
              </CardDescription>
            </CardHeader>
            <CardContent>
              <BatteryStationTable batteryStations={batteryStations} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="batteries">
          <Card>
            <CardHeader>
              <CardTitle>Batteries</CardTitle>
              <CardDescription>Batteries status</CardDescription>
            </CardHeader>
            <CardContent>
              <BatteryTable batteries={batteries} />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="orders">
          <Card>
            <CardHeader>
              <CardTitle>Orders</CardTitle>
              <CardDescription>Track orders</CardDescription>
            </CardHeader>
            <CardContent>
              <OrderTable
                orderSchedules={orderSchedules}
                motorbikeStates={motorbikeStates}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="schedule">
          <Card>
            <CardHeader>
              <CardTitle>Battery Swap Schedule</CardTitle>
              <CardDescription>Schedules</CardDescription>
            </CardHeader>
            <CardContent>
              <SwapScheduleTable
                swapSchedules={swapSchedules}
                motorbikeStates={motorbikeStates}
                batteryStations={batteryStations}
              />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="logs">
          <Card>
            <CardHeader>
              <CardTitle>Fleet Activity Logs</CardTitle>
              <CardDescription>
                System events and fleet activities
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FleetActivityLog logs={activityLogs} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
