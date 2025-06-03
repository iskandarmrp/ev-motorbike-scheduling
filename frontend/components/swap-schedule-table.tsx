"use client"

import { useState } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, Download } from "lucide-react"
import type { SwapSchedule, MotorbikeState, BatteryStation } from "./dashboard-battery-swap"

interface SwapScheduleTableProps {
  swapSchedules?: SwapSchedule[]
  motorbikeStates?: Record<string, MotorbikeState>
  batteryStations?: Record<string, BatteryStation>
}

export function SwapScheduleTable({
  swapSchedules = [],
  motorbikeStates = {},
  batteryStations = {},
}: SwapScheduleTableProps) {
  const [searchTerm, setSearchTerm] = useState("")

  const filteredSchedules = swapSchedules.filter(
    (schedule) =>
      schedule.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      schedule.motorbike_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      schedule.station_id.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const getPriorityColor = (priority: number) => {
    if (priority >= 8) return "bg-red-500"
    if (priority >= 6) return "bg-orange-500"
    if (priority >= 4) return "bg-yellow-500"
    return "bg-green-500"
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "scheduled":
        return "bg-blue-500"
      case "in_progress":
        return "bg-orange-500"
      case "completed":
        return "bg-green-500"
      default:
        return "bg-gray-500"
    }
  }

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
              <TableHead>Station</TableHead>
              <TableHead>Scheduled Time</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Current Battery</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filteredSchedules.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                  No swap schedules found
                </TableCell>
              </TableRow>
            ) : (
              filteredSchedules.map((schedule, index) => {
                const motorbike = motorbikeStates[schedule.motorbike_id]
                const station = batteryStations[schedule.station_id]
                const batteryPercentage = motorbike
                  ? Math.round((motorbike.battery_now / motorbike.battery_max) * 100)
                  : 0

                return (
                  <TableRow key={`${schedule.motorbike_id}-${schedule.station_id}-${index}`}>
                    <TableCell className="font-medium">{schedule.motorbike_id}</TableCell>
                    <TableCell>{station ? station.name : `Station ${schedule.station_id}`}</TableCell>
                    <TableCell>{schedule.scheduled_time.toFixed(1)} min</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          schedule.priority >= 8 ? "destructive" : schedule.priority >= 6 ? "default" : "secondary"
                        }
                      >
                        {schedule.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(schedule.status)}>{schedule.status}</Badge>
                    </TableCell>
                    <TableCell>
                      {motorbike ? (
                        <span className={batteryPercentage <= 20 ? "text-red-600 font-medium" : ""}>
                          {batteryPercentage}%
                        </span>
                      ) : (
                        <span className="text-gray-500">-</span>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
