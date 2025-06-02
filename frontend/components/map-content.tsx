"use client"

import { useEffect, useRef, useState } from "react"
import L from "leaflet"
import "leaflet/dist/leaflet.css"
import type { Assignment, BaseState, TaxiState } from "./dashboard"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

// Add Leaflet polyline decoding extension
// This is moved from the separate file to avoid SSR issues
if (typeof window !== "undefined") {
  L.Polyline.fromEncoded = (encoded: string, options?: L.PolylineOptions) => {
    // Array that holds the points
    const points: [number, number][] = []
    let index = 0
    const len = encoded.length
    let lat = 0
    let lng = 0

    while (index < len) {
      let b
      let shift = 0
      let result = 0
      do {
        b = encoded.charCodeAt(index++) - 63
        result |= (b & 0x1f) << shift
        shift += 5
      } while (b >= 0x20)
      const dlat = (result & 1) !== 0 ? ~(result >> 1) : result >> 1
      lat += dlat

      shift = 0
      result = 0
      do {
        b = encoded.charCodeAt(index++) - 63
        result |= (b & 0x1f) << shift
        shift += 5
      } while (b >= 0x20)
      const dlng = (result & 1) !== 0 ? ~(result >> 1) : result >> 1
      lng += dlng

      points.push([lat * 1e-5, lng * 1e-5])
    }

    return new L.Polyline(points, options || {})
  }
}

interface MapContentProps {
  taxiStates: Record<string, TaxiState>
  baseStates: Record<string, BaseState>
  activeAssignments: Record<string, Assignment>
}

export default function MapContent({ taxiStates, baseStates, activeAssignments }: MapContentProps) {
  const mapRef = useRef<HTMLDivElement>(null)
  const leafletMapRef = useRef<L.Map | null>(null)
  const markersRef = useRef<Record<string, L.Marker>>({})
  const baseMarkersRef = useRef<Record<string, L.Circle>>({})
  const baseIconMarkersRef = useRef<Record<string, L.Marker>>({})
  const polylineRef = useRef<Record<string, L.Polyline>>({})
  const deviationBufferRef = useRef<Record<string, L.Polygon>>({})

  const [mapInitialized, setMapInitialized] = useState(false)
  const [selectedTaxi, setSelectedTaxi] = useState<string | null>(null)

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || leafletMapRef.current) return

    const map = L.map(mapRef.current).setView([-6.9, 107.6], 13)

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map)

    leafletMapRef.current = map
    setMapInitialized(true)

    return () => {
      map.remove()
      leafletMapRef.current = null
    }
  }, [])

  // Update taxi markers
  useEffect(() => {
    if (!mapInitialized || !leafletMapRef.current) return

    const map = leafletMapRef.current

    // Update existing markers and add new ones
    Object.entries(taxiStates).forEach(([taxiId, state]) => {
      const { latitude, longitude, taxi_state } = state

      // Skip if no valid coordinates
      if (!latitude || !longitude) return

      // Determine marker color based on taxi_state
      let markerColor = "green" // Default for "kosong"
      if (taxi_state === "menuju penumpang") {
        markerColor = "yellow"
      } else if (taxi_state === "bersama penumpang") {
        markerColor = "red"
      }

      // Create custom icon
      const taxiIcon = L.divIcon({
        className: "custom-taxi-marker",
        html: `<div style="background-color: ${markerColor}; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white;"></div>`,
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      })

      if (markersRef.current[taxiId]) {
        // Update existing marker
        markersRef.current[taxiId].setLatLng([latitude, longitude])
        markersRef.current[taxiId].setIcon(taxiIcon)
      } else {
        // Create new marker
        const marker = L.marker([latitude, longitude], { icon: taxiIcon })
          .addTo(map)
          .on("click", () => {
            setSelectedTaxi(selectedTaxi === taxiId ? null : taxiId)
          })

        markersRef.current[taxiId] = marker
      }

      // Update popup content with real-time data
      const popupContent = `
        <div class="taxi-popup">
          <h3 class="font-bold">Taxi ID: ${taxiId}</h3>
          <p>Status: ${taxi_state}</p>
          <p>Battery: ${state.battery}%</p>
          <p>Location: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}</p>
        </div>
      `

      markersRef.current[taxiId].bindPopup(popupContent)
    })

    // Remove markers for taxis that no longer exist
    Object.keys(markersRef.current).forEach((taxiId) => {
      if (!taxiStates[taxiId]) {
        map.removeLayer(markersRef.current[taxiId])
        delete markersRef.current[taxiId]
      }
    })
  }, [taxiStates, mapInitialized, selectedTaxi])

  // Update base markers
  useEffect(() => {
    if (!mapInitialized || !leafletMapRef.current) return

    const map = leafletMapRef.current

    // Update existing base markers and add new ones
    Object.entries(baseStates).forEach(([baseId, state]) => {
      const { latitude, longitude, fleet } = state

      // Skip if no valid coordinates
      if (!latitude || !longitude) return

      // Count occupied slots
      const occupiedSlots = fleet.filter((slot) => slot !== null).length
      const totalSlots = fleet.length

      // Create base icon
      const baseIcon = L.divIcon({
        className: "custom-base-marker",
        html: `<div style="background-color: #3b82f6; color: white; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white;">${occupiedSlots}/${totalSlots}</div>`,
        iconSize: [24, 24],
        iconAnchor: [12, 12],
      })

      // Update or create base area circle
      if (baseMarkersRef.current[baseId]) {
        // Update existing marker
        baseMarkersRef.current[baseId].setLatLng([latitude, longitude])
      } else {
        // Create new marker (circle)
        const circle = L.circle([latitude, longitude], {
          color: "blue",
          fillColor: "#3b82f6",
          fillOpacity: 0.2,
          radius: 500, // 500m radius as defined in backend
        }).addTo(map)

        baseMarkersRef.current[baseId] = circle
      }

      // Update or create base icon marker
      if (baseIconMarkersRef.current[baseId]) {
        // Update existing marker
        baseIconMarkersRef.current[baseId].setLatLng([latitude, longitude])
        baseIconMarkersRef.current[baseId].setIcon(baseIcon)
      } else {
        // Create new marker
        const marker = L.marker([latitude, longitude], { icon: baseIcon }).addTo(map)

        baseIconMarkersRef.current[baseId] = marker
      }

      // Create popup content with fleet information
      const fleetInfo = fleet
        .map((taxiId, index) => {
          if (taxiId === null) {
            return `<li>Slot ${index + 1}: Empty</li>`
          } else {
            const taxi = taxiStates[taxiId]
            const status = taxi ? taxi.taxi_state : "Unknown"
            const battery = taxi ? `${taxi.battery}%` : "Unknown"
            return `<li>Slot ${index + 1}: Taxi ${taxiId} (${status}, Battery: ${battery})</li>`
          }
        })
        .join("")

      const popupContent = `
        <div class="base-popup">
          <h3 class="font-bold">Base ID: ${baseId}</h3>
          <p>Location: ${latitude.toFixed(6)}, ${longitude.toFixed(6)}</p>
          <p>Capacity: ${occupiedSlots}/${totalSlots}</p>
          <h4 class="font-semibold mt-2">Fleet:</h4>
          <ul class="list-disc pl-5">
            ${fleetInfo}
          </ul>
        </div>
      `

      baseIconMarkersRef.current[baseId].bindPopup(popupContent)
    })

    // Remove markers for bases that no longer exist
    Object.keys(baseMarkersRef.current).forEach((baseId) => {
      if (!baseStates[baseId]) {
        map.removeLayer(baseMarkersRef.current[baseId])
        delete baseMarkersRef.current[baseId]
      }
    })

    Object.keys(baseIconMarkersRef.current).forEach((baseId) => {
      if (!baseStates[baseId]) {
        map.removeLayer(baseIconMarkersRef.current[baseId])
        delete baseIconMarkersRef.current[baseId]
      }
    })
  }, [baseStates, taxiStates, mapInitialized])

  // Update polylines and deviation buffers for active assignments
  useEffect(() => {
    if (!mapInitialized || !leafletMapRef.current) return

    const map = leafletMapRef.current

    // Remove all existing polylines and deviation buffers
    Object.values(polylineRef.current).forEach((polyline) => {
      map.removeLayer(polyline)
    })
    polylineRef.current = {}

    Object.values(deviationBufferRef.current).forEach((buffer) => {
      map.removeLayer(buffer)
    })
    deviationBufferRef.current = {}

    // Add new polylines for active assignments
    Object.entries(activeAssignments).forEach(([taxiId, assignment]) => {
      if (!assignment.polyline) return

      try {
        // Decode polyline
        const decodedPath = L.Polyline.fromEncoded(assignment.polyline).getLatLngs()

        // Create polyline
        const polyline = L.polyline(decodedPath, {
          color: "blue",
          weight: 3,
          opacity: 0.7,
        }).addTo(map)

        polylineRef.current[taxiId] = polyline

        // Only show deviation buffer for selected taxi
        if (selectedTaxi === taxiId) {
          // Create buffer polygon for deviation radius (2000m)
          const deviateRadius = 2000 // MELENCENG_RADIUS from backend

          // Create buffer points around each segment of the route
          const bufferPoints: L.LatLng[][] = []

          // For each segment of the route, create buffer points
          for (let i = 0; i < decodedPath.length - 1; i++) {
            const p1 = decodedPath[i] as L.LatLng
            const p2 = decodedPath[i + 1] as L.LatLng

            // Calculate perpendicular vector
            const dx = p2.lng - p1.lng
            const dy = p2.lat - p1.lat
            const length = Math.sqrt(dx * dx + dy * dy)

            if (length === 0) continue

            // Normalize and scale to buffer distance
            // Convert meters to approximate degrees (very rough approximation)
            const bufferDegrees = deviateRadius / 111000 // 1 degree is roughly 111km

            const nx = (-dy / length) * bufferDegrees
            const ny = (dx / length) * bufferDegrees

            // Create buffer points on both sides of the segment
            bufferPoints.push([
              new L.LatLng(p1.lat + ny, p1.lng + nx),
              new L.LatLng(p2.lat + ny, p2.lng + nx),
              new L.LatLng(p2.lat - ny, p2.lng - nx),
              new L.LatLng(p1.lat - ny, p1.lng - nx),
              new L.LatLng(p1.lat + ny, p1.lng + nx), // Close the polygon
            ])
          }

          // Create a polygon for each segment buffer
          bufferPoints.forEach((points, i) => {
            const buffer = L.polygon(points, {
              color: "red",
              weight: 1,
              opacity: 0.5,
              fillColor: "red",
              fillOpacity: 0.1,
            }).addTo(map)

            deviationBufferRef.current[`${taxiId}-${i}`] = buffer
          })
        }
      } catch (error) {
        console.error("Error decoding polyline:", error)
      }
    })
  }, [activeAssignments, mapInitialized, selectedTaxi])

  return (
    <div className="relative h-full">
      <div ref={mapRef} className="w-full h-full" />

      {selectedTaxi && (
        <div className="absolute top-4 right-4 z-[1000]">
          <Card className="w-64 shadow-lg">
            <CardHeader className="py-3">
              <CardTitle className="text-lg flex justify-between items-center">
                <span>Taxi {selectedTaxi}</span>
                <Badge
                  className={
                    taxiStates[selectedTaxi]?.taxi_state === "kosong"
                      ? "bg-green-500"
                      : taxiStates[selectedTaxi]?.taxi_state === "menuju penumpang"
                        ? "bg-yellow-500"
                        : "bg-red-500"
                  }
                >
                  {taxiStates[selectedTaxi]?.taxi_state}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="py-3">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="font-medium">Battery:</span>
                  <span>{taxiStates[selectedTaxi]?.battery}%</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Latitude:</span>
                  <span>{taxiStates[selectedTaxi]?.latitude.toFixed(6)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Longitude:</span>
                  <span>{taxiStates[selectedTaxi]?.longitude.toFixed(6)}</span>
                </div>
                {activeAssignments[selectedTaxi] && (
                  <div className="flex justify-between">
                    <span className="font-medium">Assigned to Base:</span>
                    <span>{activeAssignments[selectedTaxi].base_id}</span>
                  </div>
                )}
              </div>
              <Button variant="outline" size="sm" className="w-full mt-3" onClick={() => setSelectedTaxi(null)}>
                Close
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
