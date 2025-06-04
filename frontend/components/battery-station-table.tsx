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
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Search, Download } from "lucide-react";
import type { BatteryStation } from "./dashboard-battery-swap";

interface BatteryStationTableProps {
  batteryStations?: Record<string, BatteryStation>;
}

export function BatteryStationTable({
  batteryStations = {},
}: BatteryStationTableProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const stations = Object.values(batteryStations);
  const filteredStations = stations.filter(
    (station) =>
      station.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      station.id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getCapacityColor = (percentage: number) => {
    if (percentage > 70) return "text-green-600";
    if (percentage > 30) return "text-orange-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search stations..."
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
              <TableHead>Station ID</TableHead>
              <TableHead>Name</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Total Slots</TableHead>
              <TableHead>Batteries</TableHead>
              <TableHead>Available Batteries</TableHead>
              <TableHead>Charging Batteries</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredStations.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center py-8 text-gray-500"
                >
                  No battery stations found
                </TableCell>
              </TableRow>
            ) : (
              filteredStations.map((station) => {
                const usagePercentage = Math.round(
                  ((station.total_slots - station.available_batteries) /
                    station.total_slots) *
                    100
                );

                return (
                  <TableRow key={station.id}>
                    <TableCell className="font-medium">{station.id}</TableCell>
                    <TableCell>{station.name}</TableCell>
                    <TableCell>
                      {station.lat.toFixed(6)}, {station.lon.toFixed(6)}
                    </TableCell>
                    <TableCell>{station.total_slots}</TableCell>
                    <TableCell>
                      <div className="space-y-1 text-sm max-h-40 overflow-y-auto">
                        {station.slots.map((battery, index) => (
                          <div key={battery.id} className="border rounded p-1">
                            <div className="font-medium text-gray-800">
                              Slot: {index + 1}
                            </div>
                            <div className="font-medium text-gray-800">
                              Battery ID: {battery.id}
                            </div>
                            <div className="text-xs text-gray-500">
                              Battery Now:{" "}
                              <span
                                className={
                                  battery.battery_now >= 80
                                    ? "text-green-600"
                                    : battery.battery_now >= 30
                                    ? "text-orange-600"
                                    : "text-red-600"
                                }
                              >
                                {battery.battery_now}%
                              </span>
                              , Cycles: {battery.cycle}
                            </div>
                          </div>
                        ))}
                      </div>
                    </TableCell>

                    <TableCell className="text-green-600 font-medium">
                      {station.available_batteries}/{station.total_slots}
                    </TableCell>
                    <TableCell className="text-orange-600 font-medium">
                      {station.charging_batteries}/{station.total_slots}
                    </TableCell>
                  </TableRow>
                );
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
