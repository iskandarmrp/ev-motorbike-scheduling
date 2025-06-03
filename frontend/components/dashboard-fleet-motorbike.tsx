"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { io, type Socket } from "socket.io-client";
import { MapContainer } from "@/components/map-container";
import { TaxiTable } from "@/components/taxi-table";
import { BaseTable } from "@/components/base-table";
import { AssignmentTable } from "@/components/assignment-table";
import { RequestTable } from "@/components/request-table";
import { BaseActivityLog } from "@/components/base-activity-log";
import { ViolationLog } from "@/components/violation-log";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { WEBSOCKET_URL, DEMO_MODE } from "@/lib/config";
import {
  mockTaxiStates,
  mockBaseStates,
  mockAssignments,
  mockBaseRequests,
  mockBaseActivityLogs,
  mockViolationLogs,
} from "@/lib/mock-data";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// Define types for our data
export interface MotorbikeState {
  status: string;
  online_status: string;
  max_speed: number;
  latitude: number;
  longitude: number;
  battery_id: number;
  battery: number;
}

export interface BatterySwapStationState {
  name: string;
  total_slots: number;
  latitude: number;
  longitude: number;
  slots: (number | null)[];
}

export interface Battery {
  capacity: number;
  battery: number;
  cycle: number;
}

export interface SwapSchedule {}

export interface TaxiState {
  taxi_state: string;
  latitude: number;
  longitude: number;
  battery: number;
}

export interface BaseState {
  latitude: number;
  longitude: number;
  fleet: (number | null)[];
}

export interface Assignment {
  base_id: string;
  polyline: string;
  deviate_radius?: number;
}

export interface BaseActivityLogEntry {
  timestamp: string;
  base_id: string;
  status: string;
  taxi_id: string | number;
}

export interface ViolationLogEntry {
  timestamp: string;
  taxi_id: string | number;
  base_id: string;
  reason: string;
}

// No need to import leaflet-extensions anymore as it's now included in map-content.tsx

export function DashboardFleetMotorbike() {
  const router = useRouter();
  const [socket, setSocket] = useState<Socket | null>(null);
  const [taxiStates, setTaxiStates] = useState<Record<string, TaxiState>>({});
  const [baseStates, setBaseStates] = useState<Record<string, BaseState>>({});
  const [activeAssignments, setActiveAssignments] = useState<
    Record<string, Assignment>
  >({});
  const [baseRequests, setBaseRequests] = useState<string[]>([]);
  const [baseActivityLogs, setBaseActivityLogs] = useState<
    BaseActivityLogEntry[]
  >([]);
  const [violationLogs, setViolationLogs] = useState<ViolationLogEntry[]>([]);
  const [connected, setConnected] = useState(DEMO_MODE); // In demo mode, we're always "connected"
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Check if token exists
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/");
      return;
    }

    // In demo mode, load mock data
    if (DEMO_MODE) {
      console.log("Running in demo mode with mock data");
      setTaxiStates(mockTaxiStates);
      setBaseStates(mockBaseStates);
      setActiveAssignments(mockAssignments);
      setBaseRequests(mockBaseRequests);
      setBaseActivityLogs(mockBaseActivityLogs);
      setViolationLogs(mockViolationLogs);
      return; // Skip WebSocket connection in demo mode
    }

    // Connect to WebSocket for real mode
    if (!WEBSOCKET_URL) {
      setError("WebSocket URL is not configured");
      return;
    }

    try {
      console.log(`Connecting to WebSocket at ${WEBSOCKET_URL}`);

      const socketInstance = io(WEBSOCKET_URL, {
        transports: ["websocket", "polling"], // Try both WebSocket and polling
        auth: {
          token,
        },
        withCredentials: true, // Important for CORS
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        timeout: 20000, // Increase timeout
      });

      socketInstance.on("connect", () => {
        console.log("Connected to WebSocket");
        setConnected(true);
        setError(null);
        // Register as operator
        socketInstance.emit("operator_register");
      });

      socketInstance.on("connect_error", (err) => {
        console.error("WebSocket connection error:", err);
        setError(`Could not connect to the server: ${err.message}`);
        setConnected(false);
      });

      socketInstance.on("disconnect", () => {
        console.log("Disconnected from WebSocket");
        setConnected(false);
      });

      socketInstance.on("initial_data", (data) => {
        console.log("Received initial data:", data);
        setTaxiStates(data.taxi_states || {});
        setBaseStates(data.base_states || {});
        setActiveAssignments(data.active_assignments || {});

        // Convert log data from object to array with timestamp
        if (data.log_base_activity) {
          const baseActivityLogsArray = Object.entries(
            data.log_base_activity
          ).map(([timestamp, log]: [string, any]) => ({
            timestamp,
            ...log,
          }));
          setBaseActivityLogs(baseActivityLogsArray);
        }

        if (data.log_pelanggaran_data) {
          const violationLogsArray = Object.entries(
            data.log_pelanggaran_data
          ).map(([timestamp, log]: [string, any]) => ({
            timestamp,
            ...log,
          }));
          setViolationLogs(violationLogsArray);
        }
      });

      socketInstance.on("update_data", (data) => {
        console.log("Received update data:", data);
        setTaxiStates(data.taxi_states || {});
        setBaseStates(data.base_states || {});
        setActiveAssignments(data.active_assignments || {});
        setBaseRequests(data.base_requests || []);

        // Update logs if provided
        if (data.log_base_activity) {
          const baseActivityLogsArray = Object.entries(
            data.log_base_activity
          ).map(([timestamp, log]: [string, any]) => ({
            timestamp,
            ...log,
          }));
          setBaseActivityLogs(baseActivityLogsArray);
        }

        if (data.log_pelanggaran_data) {
          const violationLogsArray = Object.entries(
            data.log_pelanggaran_data
          ).map(([timestamp, log]: [string, any]) => ({
            timestamp,
            ...log,
          }));
          setViolationLogs(violationLogsArray);
        }
      });

      setSocket(socketInstance);

      return () => {
        socketInstance.disconnect();
      };
    } catch (err) {
      console.error("Error setting up WebSocket:", err);
      setError("Failed to initialize WebSocket connection");
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("userId");
    if (socket) {
      socket.disconnect();
    }
    router.push("/");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-green-600 text-white p-4 flex justify-between items-center">
        <h1 className="text-2xl font-bold">Ojek Online Listrik</h1>
        <div className="flex items-center gap-4">
          {DEMO_MODE && (
            <span className="text-xs bg-yellow-500 text-white px-2 py-1 rounded">
              DEMO MODE
            </span>
          )}
          <span
            className={`inline-block w-3 h-3 rounded-full ${
              connected ? "bg-green-400" : "bg-red-500"
            }`}
          ></span>
          <span>{connected ? "Connected" : "Disconnected"}</span>
          <Button variant="outline" size="sm" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            Logout
          </Button>
        </div>
      </header>

      <main className="flex-1 p-4 flex flex-col gap-4">
        {!DEMO_MODE && error && (
          <Alert variant="destructive">
            <AlertTitle>Error</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {DEMO_MODE && (
          <Alert>
            <AlertTitle>Demo Mode</AlertTitle>
            <AlertDescription>
              Running with mock data. Connect to a real backend server for live
              data.
            </AlertDescription>
          </Alert>
        )}

        <div className="h-[500px] bg-white rounded-lg shadow-md overflow-hidden">
          <MapContainer
            taxiStates={taxiStates}
            baseStates={baseStates}
            activeAssignments={activeAssignments}
          />
        </div>

        <Tabs
          defaultValue="taxis"
          className="bg-white rounded-lg shadow-md p-4"
        >
          <TabsList className="grid grid-cols-6 mb-4">
            <TabsTrigger value="taxis">Taxis</TabsTrigger>
            <TabsTrigger value="bases">Bases</TabsTrigger>
            <TabsTrigger value="assignments">Active Assignments</TabsTrigger>
            <TabsTrigger value="requests">Base Requests</TabsTrigger>
            <TabsTrigger value="activity-logs">Base Activity Logs</TabsTrigger>
            <TabsTrigger value="violation-logs">Violation Logs</TabsTrigger>
          </TabsList>

          <TabsContent value="taxis">
            <TaxiTable taxiStates={taxiStates} />
          </TabsContent>

          <TabsContent value="bases">
            <BaseTable baseStates={baseStates} />
          </TabsContent>

          <TabsContent value="assignments">
            <AssignmentTable
              activeAssignments={activeAssignments}
              taxiStates={taxiStates}
              baseStates={baseStates}
            />
          </TabsContent>

          <TabsContent value="requests">
            <RequestTable baseRequests={baseRequests} baseStates={baseStates} />
          </TabsContent>

          <TabsContent value="activity-logs">
            <BaseActivityLog logs={baseActivityLogs} />
          </TabsContent>

          <TabsContent value="violation-logs">
            <ViolationLog logs={violationLogs} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
