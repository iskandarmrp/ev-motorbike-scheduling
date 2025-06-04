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
import { Search, Download } from "lucide-react";
import type { Battery } from "./dashboard-battery-swap";

interface BatteryTableProps {
  batteries: Battery[];
}

export function BatteryTable({ batteries }: BatteryTableProps) {
  const [searchTerm, setSearchTerm] = useState("");

  const filteredBatteries = batteries.filter(
    (battery) =>
      battery.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      battery.location_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getBatteryColor = (battery_now: number) => {
    if (battery_now >= 80) return "text-green-600";
    if (battery_now >= 30) return "text-orange-600";
    return "text-red-600";
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Search className="h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search batteries..."
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
              <TableHead>Battery ID</TableHead>
              <TableHead>Capacity</TableHead>
              <TableHead>Battery Now</TableHead>
              <TableHead>Total Charged</TableHead>
              <TableHead>Cycles</TableHead>
              <TableHead>Location</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredBatteries.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="text-center py-8 text-gray-500"
                >
                  No batteries found
                </TableCell>
              </TableRow>
            ) : (
              filteredBatteries.map((battery) => (
                <TableRow key={battery.id}>
                  <TableCell className="font-medium">{battery.id}</TableCell>
                  <TableCell>{battery.capacity}</TableCell>
                  <TableCell className={getBatteryColor(battery.battery_now)}>
                    {battery.battery_now}%
                  </TableCell>
                  <TableCell>{battery.battery_total_charged}</TableCell>
                  <TableCell>{battery.cycle}</TableCell>
                  <TableCell className="capitalize">
                    {battery.location} {battery.location_id}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
