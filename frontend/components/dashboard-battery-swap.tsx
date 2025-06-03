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
import { OrderTable } from "./order-table";
import { SwapScheduleTable } from "./swap-schedule-table";
import { FleetActivityLog } from "./fleet-activity-log";
import { ConnectionStatus } from "./connection-status";
import { DEMO_MODE, DEBUG_MODE } from "@/lib/config";
import { fetchBatteryStatus, type BatterySwapStatus } from "@/lib/battery-api";
import { Battery, Zap, Truck, CheckCircle, AlertTriangle } from "lucide-react";

export interface MotorbikeState {
  id: string;
  current_lat: number;
  current_lon: number;
  status: "idle" | "on_order" | "heading_to_station" | "charging" | "offline";
  battery_now: number;
  battery_max: number;
  online_status: "online" | "offline";
  assigned_order_id?: string;
  assigned_station_id?: string;
}

export interface BatteryStation {
  id: string;
  name: string;
  lat: number;
  lon: number;
  available_batteries: number;
  charging_batteries: number;
  total_capacity: number;
}

export interface OrderSchedule {
  id: string;
  status: "pending" | "active" | "completed" | "failed";
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
  motorbike_id: string;
  station_id: string;
  priority: number;
  scheduled_time: number;
  status: "scheduled" | "in_progress" | "completed";
}

// Mock data for fallback
const mockMotorbikeStates: Record<string, MotorbikeState> = {
  MB001: {
    id: "MB001",
    current_lat: -6.2088,
    current_lon: 106.8456,
    status: "idle",
    battery_now: 80,
    battery_max: 100,
    online_status: "online",
  },
};

const mockBatteryStations: Record<string, BatteryStation> = {
  BS001: {
    id: "BS001",
    name: "Station Central Jakarta",
    lat: -6.2088,
    lon: 106.8456,
    available_batteries: 8,
    charging_batteries: 2,
    total_capacity: 10,
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
    id: "SWAP001",
    motorbike_id: "MB003",
    station_id: "BS001",
    priority: 8,
    scheduled_time: 15,
    status: "scheduled",
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
    if (!data) return;

    try {
      let hasRealData = false;

      if (DEBUG_MODE) {
        console.log("Starting data transformation with:", data);
      }

      // Transform motorbike data
      const transformedMotorbikes: Record<string, MotorbikeState> = {};
      const motorbikeArray = safeArray(data.fleet_ev_motorbikes);

      if (motorbikeArray.length > 0) {
        motorbikeArray.forEach((motorbike, index) => {
          if (motorbike && typeof motorbike === "object") {
            console.log("Ini motorbike id", motorbike.id);
            console.log("Ini motorbike latitude", motorbike.latitude);
            const id = safeString(
              motorbike.id,
              `MB${String(index + 1).padStart(3, "0")}`
            );

            // Use actual API values, not defaults
            const transformedMotorbike: MotorbikeState = {
              id,
              current_lat: safeNumber(
                motorbike.latitude,
                -6.2088 + (Math.random() - 0.5) * 0.02
              ),
              current_lon: safeNumber(
                motorbike.longitude,
                106.8456 + (Math.random() - 0.5) * 0.02
              ),
              status: safeString(motorbike.status, "idle") as any,
              battery_now: safeNumber(
                motorbike.battery_now,
                Math.floor(Math.random() * 100)
              ),
              battery_max: safeNumber(motorbike.battery_max, 100),
              online_status: safeString(
                motorbike.online_status,
                "online"
              ) as any,
              assigned_order_id: motorbike.assigned_order_id
                ? safeString(motorbike.assigned_order_id)
                : undefined,
              assigned_station_id: motorbike.assigned_station_id
                ? safeString(motorbike.assigned_station_id)
                : undefined,
            };

            transformedMotorbikes[id] = transformedMotorbike;
            hasRealData = true;

            if (DEBUG_MODE) {
              console.log(`Transformed motorbike ${id}:`, {
                original: motorbike,
                transformed: transformedMotorbike,
              });
            }
          }
        });
      }

      // Transform battery station data
      const transformedStations: Record<string, BatteryStation> = {};
      const stationArray = safeArray(data.battery_swap_station);

      if (stationArray.length > 0) {
        stationArray.forEach((station, index) => {
          if (station && typeof station === "object") {
            const id = safeString(
              station.id,
              `BS${String(index + 1).padStart(3, "0")}`
            );
            console.log("Ini id:", station.id);
            console.log("Ini latitude:", station.lat);

            const transformedStation: BatteryStation = {
              id,
              name: safeString(station.name, `Battery Station ${id}`),
              lat: safeNumber(
                station.latitude,
                -6.2088 + (Math.random() - 0.5) * 0.02
              ),
              lon: safeNumber(
                station.longitude,
                106.8456 + (Math.random() - 0.5) * 0.02
              ),
              available_batteries: safeNumber(
                station.available_batteries,
                Math.floor(Math.random() * 10)
              ),
              charging_batteries: safeNumber(
                station.charging_batteries,
                Math.floor(Math.random() * 5)
              ),
              total_capacity: safeNumber(station.total_capacity, 15),
            };

            transformedStations[id] = transformedStation;
            hasRealData = true;

            if (DEBUG_MODE) {
              console.log(`Transformed station ${id}:`, {
                original: station,
                transformed: transformedStation,
              });
            }
          }
        });
      }

      // Transform order data
      const transformedOrders: OrderSchedule[] = [];
      const allOrders = [
        ...safeArray(data.order_search_driver),
        ...safeArray(data.order_active),
        ...safeArray(data.order_done),
        ...safeArray(data.order_failed),
      ];

      if (allOrders.length > 0) {
        allOrders.forEach((order, index) => {
          if (order && typeof order === "object") {
            const transformedOrder: OrderSchedule = {
              id: safeString(
                order.id,
                `ORD${String(index + 1).padStart(3, "0")}`
              ),
              status: safeString(order.status, "pending") as any,
              assigned_motorbike_id: order.assigned_motorbike_id
                ? safeString(order.assigned_motorbike_id)
                : undefined,
              order_origin_lat: safeNumber(
                order.order_origin_lat,
                -6.2088 + (Math.random() - 0.5) * 0.02
              ),
              order_origin_lon: safeNumber(
                order.order_origin_lon,
                106.8456 + (Math.random() - 0.5) * 0.02
              ),
              order_destination_lat: safeNumber(
                order.order_destination_lat,
                -6.22 + (Math.random() - 0.5) * 0.02
              ),
              order_destination_lon: safeNumber(
                order.order_destination_lon,
                106.83 + (Math.random() - 0.5) * 0.02
              ),
              created_at: safeString(
                order.created_at,
                new Date().toISOString()
              ),
              completed_at: order.completed_at
                ? safeString(order.completed_at)
                : undefined,
            };

            transformedOrders.push(transformedOrder);
            hasRealData = true;

            if (DEBUG_MODE) {
              console.log(`Transformed order ${transformedOrder.id}:`, {
                original: order,
                transformed: transformedOrder,
              });
            }
          }
        });
      }

      // Transform swap schedule data
      const transformedSwaps: SwapSchedule[] = [];
      const batteryArray = safeArray(data.batteries);

      if (batteryArray.length > 0) {
        batteryArray.forEach((battery, index) => {
          if (battery && typeof battery === "object") {
            const transformedSwap: SwapSchedule = {
              id: safeString(
                battery.id,
                `SWAP${String(index + 1).padStart(3, "0")}`
              ),
              motorbike_id: safeString(
                battery.motorbike_id,
                `MB${String(index + 1).padStart(3, "0")}`
              ),
              station_id: safeString(
                battery.station_id,
                `BS${String((index % 8) + 1).padStart(3, "0")}`
              ),
              priority: safeNumber(
                battery.priority,
                Math.floor(Math.random() * 10) + 1
              ),
              scheduled_time: safeNumber(
                battery.scheduled_time,
                Math.floor(Math.random() * 30) + 5
              ),
              status: safeString(battery.status, "scheduled") as any,
            };

            transformedSwaps.push(transformedSwap);
            hasRealData = true;

            if (DEBUG_MODE) {
              console.log(`Transformed swap ${transformedSwap.id}:`, {
                original: battery,
                transformed: transformedSwap,
              });
            }
          }
        });
      }

      // Update state with real data or keep mock data
      if (hasRealData) {
        setDataSource("api");

        // Always use transformed data if we have any
        if (Object.keys(transformedMotorbikes).length > 0) {
          setMotorbikeStates(transformedMotorbikes);
          if (DEBUG_MODE) {
            console.log(
              "Updated motorbike states with API data:",
              transformedMotorbikes
            );
          }
        }

        if (Object.keys(transformedStations).length > 0) {
          setBatteryStations(transformedStations);
          if (DEBUG_MODE) {
            console.log(
              "Updated battery stations with API data:",
              transformedStations
            );
          }
        }

        if (transformedOrders.length > 0) {
          setOrderSchedules(transformedOrders);
          if (DEBUG_MODE) {
            console.log(
              "Updated order schedules with API data:",
              transformedOrders
            );
          }
        }

        if (transformedSwaps.length > 0) {
          setSwapSchedules(transformedSwaps);
          if (DEBUG_MODE) {
            console.log(
              "Updated swap schedules with API data:",
              transformedSwaps
            );
          }
        }

        // Generate activity logs
        const newLogs = [
          `[${new Date().toLocaleTimeString()}] API data received: ${
            Object.keys(transformedMotorbikes).length
          } motorbikes, ${Object.keys(transformedStations).length} stations, ${
            transformedOrders.length
          } orders`,
        ];
        setActivityLogs((prev) => [...newLogs, ...prev].slice(0, 50));
      } else {
        setDataSource("mock");
        const newLogs = [
          `[${new Date().toLocaleTimeString()}] API returned empty data, using mock data`,
        ];
        setActivityLogs((prev) => [...newLogs, ...prev].slice(0, 50));
      }

      if (DEBUG_MODE) {
        console.log("Data transformation completed:", {
          hasRealData,
          dataSource: hasRealData ? "api" : "mock",
          motorbikeCount: Object.keys(transformedMotorbikes).length,
          stationCount: Object.keys(transformedStations).length,
          orderCount: transformedOrders.length,
          swapCount: transformedSwaps.length,
        });
      }
    } catch (err) {
      console.error("Error transforming API data:", err);
      setDataSource("mock");
    }
  };

  const fetchStatusData = async () => {
    try {
      setError(null);

      if (DEMO_MODE) {
        // Mock data for demo mode
        const mockStatus: BatterySwapStatus = {
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
        };
        setStatus(mockStatus);
        setLastUpdated(new Date());
        setLoading(false);
        return;
      }

      // Fetch real data from API
      const data = await fetchBatteryStatus();
      setStatus(data);
      setLastUpdated(new Date());

      // Transform API data to component format
      transformApiData(data);

      if (DEBUG_MODE) {
        console.log("Received battery status:", data);
      }
    } catch (err) {
      console.error("Failed to fetch status:", err);
      setError(err instanceof Error ? err.message : "Unknown error");
      setDataSource("mock");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatusData();

    // Poll for updates every 5 seconds when not in demo mode
    const interval = setInterval(fetchStatusData, DEMO_MODE ? 10000 : 5000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-lg">Loading Battery Swap Dashboard...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <ConnectionStatus />
        <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <h2 className="text-lg font-semibold text-red-800">
            API Connection Error
          </h2>
          <p className="text-red-600">
            Failed to fetch data from battery swap backend: {error}
          </p>
          <div className="mt-2 space-x-2">
            <button
              onClick={fetchStatusData}
              className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
            >
              Retry Connection
            </button>
            <button
              onClick={() =>
                window.open("http://localhost:8000/docs", "_blank")
              }
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              View API Docs
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Electric Fleet Management</h1>
          <p className="text-muted-foreground">Battery Swap System Dashboard</p>
          {lastUpdated && (
            <p className="text-xs text-muted-foreground">
              Last updated: {lastUpdated.toLocaleTimeString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-sm">
            {DEMO_MODE ? "Demo Mode" : "Live Data"}
          </Badge>
          <Badge
            variant={dataSource === "api" ? "default" : "secondary"}
            className="text-sm"
          >
            {dataSource === "api" ? "API Data" : "Mock Data"}
          </Badge>
        </div>
      </div>

      <ConnectionStatus />

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
      {DEBUG_MODE && status && (
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
      )}

      {/* Main Content Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="motorbikes">Motorbikes</TabsTrigger>
          <TabsTrigger value="stations">Battery Stations</TabsTrigger>
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
                  Real-time location of motorbikes and battery stations
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

        <TabsContent value="orders">
          <Card>
            <CardHeader>
              <CardTitle>Order Management</CardTitle>
              <CardDescription>
                Track and manage delivery orders
              </CardDescription>
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
              <CardDescription>
                Scheduled battery swaps and priorities
              </CardDescription>
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
