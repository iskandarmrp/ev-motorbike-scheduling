"use client"

import { useState, useEffect } from "react"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { DatePicker } from "@/components/ui/date-picker"
import { Download, RefreshCw } from "lucide-react"
import { DEMO_MODE } from "@/lib/config"

interface BaseActivityLog {
  timestamp: string
  base_id: string
  status: string
  taxi_id: string | number
}

interface BaseActivityLogProps {
  logs: BaseActivityLog[]
}

export function BaseActivityLog({ logs: initialLogs }: BaseActivityLogProps) {
  const [logs, setLogs] = useState<BaseActivityLog[]>(initialLogs)
  const [filteredLogs, setFilteredLogs] = useState<BaseActivityLog[]>(initialLogs)
  const [baseIdFilter, setBaseIdFilter] = useState<string>("all")
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [isLoading, setIsLoading] = useState(false)

  // Get unique base IDs for filter dropdown
  const uniqueBaseIds = Array.from(new Set(logs.map((log) => log.base_id))).sort()

  // Fetch logs from API
  const fetchLogs = async () => {
    if (DEMO_MODE) {
      // In demo mode, use the provided logs
      setLogs(initialLogs)
      return
    }

    setIsLoading(true)
    try {
      // Build query parameters
      const params = new URLSearchParams()
      if (baseIdFilter !== "all") {
        params.append("base_id", baseIdFilter)
      }
      if (startDate) {
        params.append("start_time", startDate.toISOString())
      }
      if (endDate) {
        // Add one day to include the end date fully
        const nextDay = new Date(endDate)
        nextDay.setDate(nextDay.getDate() + 1)
        params.append("end_time", nextDay.toISOString())
      }

      const response = await fetch(`/api/getActivityBaseLogs?${params.toString()}`)
      if (!response.ok) {
        throw new Error(`Error fetching logs: ${response.statusText}`)
      }
      const data = await response.json()
      setLogs(data)
      setFilteredLogs(data)
    } catch (error) {
      console.error("Failed to fetch activity logs:", error)
    } finally {
      setIsLoading(false)
    }
  }

  // Initial fetch
  useEffect(() => {
    if (!DEMO_MODE) {
      fetchLogs()
    } else {
      setFilteredLogs(initialLogs)
    }
  }, [])

  // Apply filters when logs or filter values change
  useEffect(() => {
    if (DEMO_MODE) {
      let filtered = [...initialLogs]

      // Filter by base ID
      if (baseIdFilter !== "all") {
        filtered = filtered.filter((log) => log.base_id === baseIdFilter)
      }

      // Filter by date range
      if (startDate) {
        const startTimestamp = startDate.getTime()
        filtered = filtered.filter((log) => new Date(log.timestamp).getTime() >= startTimestamp)
      }

      if (endDate) {
        const endTimestamp = endDate.getTime() + 86400000 // Add one day to include the end date
        filtered = filtered.filter((log) => new Date(log.timestamp).getTime() <= endTimestamp)
      }

      setFilteredLogs(filtered)
    } else {
      setFilteredLogs(logs)
    }
  }, [logs, baseIdFilter, startDate, endDate, DEMO_MODE, initialLogs])

  // Function to download logs as CSV
  const downloadCSV = () => {
    // Create CSV header
    const csvHeader = ["Timestamp", "Base ID", "Status", "Taxi ID"]

    // Create CSV rows
    const csvRows = filteredLogs.map((log) => [log.timestamp, log.base_id, log.status, log.taxi_id])

    // Combine header and rows
    const csvContent = [csvHeader.join(","), ...csvRows.map((row) => row.join(","))].join("\n")

    // Create a Blob and download link
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" })
    const url = URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.setAttribute("href", url)
    link.setAttribute("download", `base_activity_log_${new Date().toISOString().split("T")[0]}.csv`)
    link.style.visibility = "hidden"
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  // Reset all filters
  const resetFilters = () => {
    setBaseIdFilter("all")
    setStartDate(undefined)
    setEndDate(undefined)

    if (!DEMO_MODE) {
      fetchLogs()
    }
  }

  // Apply filters
  const applyFilters = () => {
    if (!DEMO_MODE) {
      fetchLogs()
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>Base Activity Log</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={fetchLogs} disabled={isLoading}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={downloadCSV}>
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-4 mb-4">
          <div className="flex flex-col space-y-1.5">
            <Label htmlFor="baseIdFilter">Base ID</Label>
            <Select value={baseIdFilter} onValueChange={setBaseIdFilter}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="All Bases" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Bases</SelectItem>
                {uniqueBaseIds.map((baseId) => (
                  <SelectItem key={baseId} value={baseId}>
                    {baseId}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col space-y-1.5">
            <Label htmlFor="startDate">Start Date</Label>
            <DatePicker date={startDate} setDate={setStartDate} />
          </div>

          <div className="flex flex-col space-y-1.5">
            <Label htmlFor="endDate">End Date</Label>
            <DatePicker date={endDate} setDate={setEndDate} />
          </div>

          <div className="flex flex-col space-y-1.5 justify-end">
            <div className="flex gap-2">
              <Button variant="secondary" onClick={applyFilters} disabled={isLoading}>
                Apply Filters
              </Button>
              <Button variant="ghost" onClick={resetFilters} disabled={isLoading}>
                Reset
              </Button>
            </div>
          </div>
        </div>

        <div className="rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Base ID</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Taxi ID</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={4} className="text-center py-8">
                    <div className="flex justify-center items-center">
                      <RefreshCw className="h-6 w-6 animate-spin mr-2" />
                      Loading activity logs...
                    </div>
                  </TableCell>
                </TableRow>
              ) : filteredLogs.length > 0 ? (
                filteredLogs.map((log, index) => (
                  <TableRow key={index}>
                    <TableCell>{new Date(log.timestamp).toLocaleString()}</TableCell>
                    <TableCell>{log.base_id}</TableCell>
                    <TableCell>{log.status}</TableCell>
                    <TableCell>{log.taxi_id}</TableCell>
                  </TableRow>
                ))
              ) : (
                <TableRow>
                  <TableCell colSpan={4} className="text-center">
                    No activity logs found
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  )
}
