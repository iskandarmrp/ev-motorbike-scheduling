"use client";

import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type {
  MotorbikeState,
  BatteryStation,
  OrderSchedule,
} from "./dashboard-battery-swap";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface MapContentBatteryProps {
  motorbikeStates?: Record<string, MotorbikeState>;
  batteryStations?: Record<string, BatteryStation>;
  orderSchedules?: OrderSchedule[];
}

export default function MapContentBattery({
  motorbikeStates = {},
  batteryStations = {},
  orderSchedules = [],
}: MapContentBatteryProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const leafletMapRef = useRef<L.Map | null>(null);
  const motorbikeMarkersRef = useRef<Record<string, L.Marker>>({});
  const stationMarkersRef = useRef<Record<string, L.Marker>>({});
  const orderLinesRef = useRef<Record<string, L.Polyline>>({});

  const [mapInitialized, setMapInitialized] = useState(false);
  const [selectedMotorbike, setSelectedMotorbike] = useState<string | null>(
    null
  );

  // Fix for default markers in Leaflet with Next.js
  useEffect(() => {
    delete (L.Icon.Default.prototype as any)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl:
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png",
      iconUrl:
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png",
      shadowUrl:
        "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png",
    });
  }, []);

  // Initialize map
  useEffect(() => {
    if (!mapRef.current || leafletMapRef.current) return;

    const map = L.map(mapRef.current).setView([-6.2088, 106.8456], 11);

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    }).addTo(map);

    leafletMapRef.current = map;
    setMapInitialized(true);

    return () => {
      map.remove();
      leafletMapRef.current = null;
    };
  }, []);

  // Update motorbike markers
  useEffect(() => {
    if (!mapInitialized || !leafletMapRef.current || !motorbikeStates) return;

    const map = leafletMapRef.current;

    // Update existing markers and add new ones
    Object.entries(motorbikeStates).forEach(([motorbikeId, state]) => {
      if (!state) return;

      const { current_lat, current_lon, status, battery_now, battery_max } =
        state;

      // Skip if no valid coordinates
      if (!current_lat || !current_lon) return;

      // Determine marker color based on status
      let markerColor = "blue"; // Default for idle
      if (status === "on_order") {
        markerColor = "green";
      } else if (status === "heading_to_station") {
        markerColor = "orange";
      } else if (status === "charging") {
        markerColor = "red";
      } else if (status === "offline") {
        markerColor = "gray";
      }

      // Create custom icon
      const motorbikeIcon = L.divIcon({
        className: "custom-motorbike-marker",
        html: `<div style="background-color: ${markerColor}; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; display: flex; align-items: center; justify-content: center; color: white; font-size: 10px; font-weight: bold;">M</div>`,
        iconSize: [20, 20],
        iconAnchor: [10, 10],
      });

      if (motorbikeMarkersRef.current[motorbikeId]) {
        // Update existing marker
        motorbikeMarkersRef.current[motorbikeId].setLatLng([
          current_lat,
          current_lon,
        ]);
        motorbikeMarkersRef.current[motorbikeId].setIcon(motorbikeIcon);
      } else {
        // Create new marker
        const marker = L.marker([current_lat, current_lon], {
          icon: motorbikeIcon,
        })
          .addTo(map)
          .on("click", () => {
            setSelectedMotorbike(
              selectedMotorbike === motorbikeId ? null : motorbikeId
            );
          });

        motorbikeMarkersRef.current[motorbikeId] = marker;
      }

      // Update popup content
      const batteryPercentage = Math.round((battery_now / battery_max) * 100);
      const popupContent = `
        <div class="motorbike-popup">
          <h3 class="font-bold">Motorbike ${motorbikeId}</h3>
          <p>Status: ${status}</p>
          <p>Battery: ${batteryPercentage}% (${battery_now}/${battery_max})</p>
          <p>Location: ${current_lat.toFixed(6)}, ${current_lon.toFixed(6)}</p>
        </div>
      `;

      motorbikeMarkersRef.current[motorbikeId].bindPopup(popupContent);
    });

    // Remove markers for motorbikes that no longer exist
    Object.keys(motorbikeMarkersRef.current).forEach((motorbikeId) => {
      if (!motorbikeStates[motorbikeId]) {
        map.removeLayer(motorbikeMarkersRef.current[motorbikeId]);
        delete motorbikeMarkersRef.current[motorbikeId];
      }
    });
  }, [motorbikeStates, mapInitialized, selectedMotorbike]);

  // Update battery station markers
  useEffect(() => {
    if (!mapInitialized || !leafletMapRef.current || !batteryStations) return;

    const map = leafletMapRef.current;

    // Update existing station markers and add new ones
    Object.entries(batteryStations).forEach(([stationId, station]) => {
      if (!station) return;

      const { lat, lon, name, available_batteries, total_slots } = station;

      // Skip if no valid coordinates
      if (!lat || !lon) return;

      // Create station icon
      const stationIcon = L.divIcon({
        className: "custom-station-marker",
        html: `<div style="background-color: #3b82f6; color: white; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: bold; border: 2px solid white; font-size: 10px;">${available_batteries}/${total_slots}</div>`,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      if (stationMarkersRef.current[stationId]) {
        // Update existing marker
        stationMarkersRef.current[stationId].setLatLng([lat, lon]);
        stationMarkersRef.current[stationId].setIcon(stationIcon);
      } else {
        // Create new marker
        const marker = L.marker([lat, lon], { icon: stationIcon }).addTo(map);
        stationMarkersRef.current[stationId] = marker;
      }

      // Create popup content
      const popupContent = `
        <div class="station-popup">
          <h3 class="font-bold">${name}</h3>
          <p>Available Batteries: ${available_batteries}</p>
          <p>Charging: ${station.charging_batteries || 0}</p>
          <p>Total Slots: ${total_slots}</p>
          <p>Alamat: ${station.alamat}</p>
          <p>Location: ${lat.toFixed(6)}, ${lon.toFixed(6)}</p>
        </div>
      `;

      stationMarkersRef.current[stationId].bindPopup(popupContent);
    });

    // Remove markers for stations that no longer exist
    Object.keys(stationMarkersRef.current).forEach((stationId) => {
      if (!batteryStations[stationId]) {
        map.removeLayer(stationMarkersRef.current[stationId]);
        delete stationMarkersRef.current[stationId];
      }
    });
  }, [batteryStations, mapInitialized]);

  // Update order lines
  useEffect(() => {
    if (!mapInitialized || !leafletMapRef.current || !orderSchedules) return;

    const map = leafletMapRef.current;

    // Remove all existing order lines
    Object.values(orderLinesRef.current).forEach((line) => {
      map.removeLayer(line);
    });
    orderLinesRef.current = {};

    // Add new order lines for active orders
    orderSchedules.forEach((order) => {
      if (order && order.status === "active" && order.assigned_motorbike_id) {
        const orderLine = L.polyline(
          [
            [order.order_origin_lat, order.order_origin_lon],
            [order.order_destination_lat, order.order_destination_lon],
          ],
          {
            color: "green",
            weight: 3,
            opacity: 0.7,
          }
        ).addTo(map);

        orderLinesRef.current[order.id] = orderLine;

        // Add popup to order line
        const popupContent = `
          <div class="order-popup">
            <h3 class="font-bold">Order ${order.id}</h3>
            <p>Status: ${order.status}</p>
            <p>Assigned Motorbike: ${order.assigned_motorbike_id}</p>
            <p>Created: ${new Date(order.created_at).toLocaleString()}</p>
          </div>
        `;
        orderLine.bindPopup(popupContent);
      }
    });
  }, [orderSchedules, mapInitialized]);

  return (
    <div className="relative h-full">
      <div ref={mapRef} className="w-full h-full" />

      {selectedMotorbike && motorbikeStates[selectedMotorbike] && (
        <div className="absolute top-4 right-4 z-[1000]">
          <Card className="w-64 shadow-lg">
            <CardHeader className="py-3">
              <CardTitle className="text-lg flex justify-between items-center">
                <span>Motorbike {selectedMotorbike}</span>
                <Badge
                  className={
                    motorbikeStates[selectedMotorbike]?.status === "idle"
                      ? "bg-blue-500"
                      : motorbikeStates[selectedMotorbike]?.status ===
                        "on_order"
                      ? "bg-green-500"
                      : motorbikeStates[selectedMotorbike]?.status ===
                        "heading_to_station"
                      ? "bg-orange-500"
                      : motorbikeStates[selectedMotorbike]?.status ===
                        "charging"
                      ? "bg-red-500"
                      : "bg-gray-500"
                  }
                >
                  {motorbikeStates[selectedMotorbike]?.status}
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="py-3">
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="font-medium">Battery:</span>
                  <span>
                    {Math.round(
                      (motorbikeStates[selectedMotorbike]?.battery_now /
                        motorbikeStates[selectedMotorbike]?.battery_max) *
                        100
                    )}
                    %
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Online:</span>
                  <span>
                    {motorbikeStates[selectedMotorbike]?.online_status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Latitude:</span>
                  <span>
                    {motorbikeStates[selectedMotorbike]?.current_lat.toFixed(6)}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="font-medium">Longitude:</span>
                  <span>
                    {motorbikeStates[selectedMotorbike]?.current_lon.toFixed(6)}
                  </span>
                </div>
                {motorbikeStates[selectedMotorbike]?.assigned_order_id && (
                  <div className="flex justify-between">
                    <span className="font-medium">Order ID:</span>
                    <span>
                      {motorbikeStates[selectedMotorbike]?.assigned_order_id}
                    </span>
                  </div>
                )}
                {motorbikeStates[selectedMotorbike]?.assigned_swap_schedule
                  ?.battery_station && (
                  <div className="flex justify-between">
                    <span className="font-medium">Station ID:</span>
                    <span>
                      {
                        motorbikeStates[selectedMotorbike]
                          ?.assigned_swap_schedule?.battery_station
                      }
                    </span>
                  </div>
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                className="w-full mt-3"
                onClick={() => setSelectedMotorbike(null)}
              >
                Close
              </Button>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
