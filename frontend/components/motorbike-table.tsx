"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Search, Download } from "lucide-react";
import type { MotorbikeState } from "./dashboard-battery-swap";

interface MotorbikeTableProps {
  motorbikeStates?: Record<string, MotorbikeState>;
}

export function MotorbikeTable({ motorbikeStates = {} }: MotorbikeTableProps) {
  const [searchTerm, setSearchTerm] = useState("");

  // Filter out invalid motorbikes and ensure proper data types
  const motorbikes = Object.values(motorbikeStates).filter((motorbike) => {
    return (
      motorbike &&
      typeof motorbike === "object" &&
      motorbike.id &&
      typeof motorbike.id === "string" &&
      typeof motorbike.current_lat === "number" &&
      typeof motorbike.current_lon === "number"
    );
  });

  const filteredMotorbikes = motorbikes.filter((motorbike) => {
    const id = String(motorbike.id || "").toLowerCase();
    const search = String(searchTerm || "").toLowerCase();
    return id.includes(search);
  });

  const getStatusColor = (status: string) => {
    switch (status) {
      case "idle":
        return "bg-blue-500 text-white";
      case "heading to order":
        return "bg-green-500 text-white";
      case "on order":
        return "bg-green-500 text-white";
      case "heading to bss":
        return "bg-orange-500 text-white";
      case "battery swap":
        return "bg-yellow-500 text-white";
      case "offline":
        return "bg-gray-500 text-white";
      default:
        return "bg-gray-500 text-white";
    }
  };

  const getBatteryColor = (percentage: number) => {
    if (percentage > 50) return "text-green-600";
    if (percentage > 20) return "text-orange-600";
    return "text-red-600";
  };

  const safeNumber = (value: any, defaultValue = 0): number => {
    const num = Number(value);
    return isNaN(num) ? defaultValue : num;
  };

  const safeString = (value: any, defaultValue = ""): string => {
    return value && typeof value === "string"
      ? value
      : String(value || defaultValue);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search motorbikes..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-sm"
          />
        </div>
        <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Motorbike ID</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Battery ID</TableHead>
              <TableHead>Battery</TableHead>
              <TableHead>Battery Cycle</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Online Status</TableHead>
              <TableHead>Assignment</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredMotorbikes.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center py-8 text-gray-500"
                >
                  {Object.keys(motorbikeStates).length === 0
                    ? "No motorbike data available from API"
                    : "No motorbikes match your search"}
                </TableCell>
              </TableRow>
            ) : (
              filteredMotorbikes.map((motorbike, index) => {
                const batteryId = safeNumber(motorbike.battery_id, 0);
                const batteryNow = safeNumber(motorbike.battery_now, 0);
                const batteryMax = safeNumber(motorbike.battery_max, 100);
                const batteryCycle = safeNumber(motorbike.battery_cycle, 0);
                const batteryPercentage =
                  batteryMax > 0
                    ? Math.round((batteryNow / batteryMax) * 100)
                    : 0;
                const motorbikeId = safeString(motorbike.id, `MB${index + 1}`);
                const status = safeString(motorbike.status, "unknown");
                const onlineStatus = safeString(
                  motorbike.online_status,
                  "unknown"
                );
                const lat = safeNumber(motorbike.current_lat, 0);
                const lon = safeNumber(motorbike.current_lon, 0);

                return (
                  <TableRow key={motorbikeId}>
                    <TableCell className="font-medium">{motorbikeId}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(status)}>{status}</Badge>
                    </TableCell>
                    <TableCell className="font-medium">{batteryId}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress
                          value={batteryPercentage}
                          className="h-2 w-20"
                        />
                        <span className={getBatteryColor(batteryPercentage)}>
                          {batteryPercentage}% ({batteryNow}/{batteryMax})
                        </span>
                      </div>
                    </TableCell>
                    <TableCell className="font-medium">
                      {batteryCycle}
                    </TableCell>
                    <TableCell>
                      {lat.toFixed(4)}, {lon.toFixed(4)}
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          onlineStatus === "online" ? "green" : "destructive"
                        }
                      >
                        {onlineStatus}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {motorbike.assigned_order_id ? (
                        <span className="text-sm">
                          Order: {safeString(motorbike.assigned_order_id)}
                        </span>
                      ) : motorbike.assigned_swap_schedule ? (
                        <span className="text-sm">
                          Station:{" "}
                          {safeString(
                            motorbike.assigned_swap_schedule.battery_station
                          )}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-500">None</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>

      {/* Debug info for development */}
      {process.env.NODE_ENV === "development" && (
        <div className="mt-4 p-2 bg-gray-100 rounded text-xs">
          <strong>Debug:</strong> Found {Object.keys(motorbikeStates).length}{" "}
          motorbike entries, {motorbikes.length} valid motorbikes,{" "}
          {filteredMotorbikes.length} after filtering
        </div>
      )}
    </div>
  );
}
