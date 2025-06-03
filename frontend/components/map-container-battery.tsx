"use client"

import dynamic from "next/dynamic"
import { Skeleton } from "@/components/ui/skeleton"
import type { MotorbikeState, BatteryStation, OrderSchedule } from "./dashboard-battery-swap"

// Create a dynamic import for the MapContent component to avoid SSR issues
const MapContentBattery = dynamic(() => import("./map-content-battery"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[400px] flex items-center justify-center bg-gray-100 rounded-lg">
      <Skeleton className="w-full h-full" />
    </div>
  ),
})

interface MapContainerBatteryProps {
  motorbikeStates?: Record<string, MotorbikeState>
  batteryStations?: Record<string, BatteryStation>
  orderSchedules?: OrderSchedule[]
}

export function MapContainerBattery({
  motorbikeStates = {},
  batteryStations = {},
  orderSchedules = [],
}: MapContainerBatteryProps) {
  return (
    <div className="w-full h-[400px] rounded-lg overflow-hidden border">
      <MapContentBattery
        motorbikeStates={motorbikeStates}
        batteryStations={batteryStations}
        orderSchedules={orderSchedules}
      />
    </div>
  )
}
