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
import { Search, Download } from "lucide-react";
import type {
  SwapSchedule,
  MotorbikeState,
  BatteryStation,
} from "./dashboard-battery-swap";

interface SwapScheduleTableProps {
  swapSchedules?: SwapSchedule[];
  motorbikeStates?: Record<string, MotorbikeState>;
  batteryStations?: Record<string, BatteryStation>;
}

export function SwapScheduleTable({
  swapSchedules = [],
  motorbikeStates = {},
  batteryStations = {},
}: SwapScheduleTableProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredSchedules = swapSchedules.filter(
    (schedule) =>
      schedule.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      schedule.ev_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      schedule.battery_station.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getPriorityColor = (priority: number) => {
    if (priority >= 8) return "bg-red-500";
    if (priority >= 6) return "bg-orange-500";
    if (priority >= 4) return "bg-yellow-500";
    return "bg-green-500";
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "scheduled":
        return "bg-blue-500";
      case "in_progress":
        return "bg-orange-500";
      case "completed":
        return "bg-green-500";
      default:
        return "bg-gray-500";
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search swap schedules..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="max-w-sm"
          />
        </div>
        {/* <Button variant="outline" size="sm">
          <Download className="h-4 w-4 mr-2" />
          Export
        </Button> */}
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Swap ID</TableHead>
              <TableHead>Motorbike ID</TableHead>
              <TableHead>Station</TableHead>
              <TableHead>Slot</TableHead>
              <TableHead>Waiting Time</TableHead>
              <TableHead>Scheduled Time</TableHead>
              <TableHead>Status</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredSchedules.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={6}
                  className="text-center py-8 text-gray-500"
                >
                  No swap schedules found
                </TableCell>
              </TableRow>
            ) : (
              filteredSchedules.map((schedule, index) => {
                const motorbike = motorbikeStates[schedule.ev_id];
                const station = batteryStations[schedule.battery_station];

                return (
                  <TableRow
                    key={`${schedule.ev_id}-${schedule.battery_station}-${index}`}
                  >
                    <TableCell className="font-medium">{schedule.id}</TableCell>
                    <TableCell className="font-medium">
                      {schedule.ev_id}
                    </TableCell>
                    <TableCell>
                      {station
                        ? station.name
                        : `Station ${schedule.battery_station}`}
                    </TableCell>
                    <TableCell>{schedule.slot}</TableCell>
                    <TableCell>
                      {schedule.waiting_time.toFixed(1)} min
                    </TableCell>
                    <TableCell>
                      {(schedule.travel_time + schedule.waiting_time).toFixed(
                        1
                      )}{" "}
                      min
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor("on going")}>
                        on going
                      </Badge>
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
