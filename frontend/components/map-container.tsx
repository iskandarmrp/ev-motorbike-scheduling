import dynamic from "next/dynamic";
import type {
  Assignment,
  BaseState,
  TaxiState,
} from "./dashboard-fleet-motorbike";

// Create a dynamic import for the MapContent component
// This ensures Leaflet is only loaded on the client side
const MapContent = dynamic(() => import("./map-content"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center bg-gray-100">
      <p>Loading map...</p>
    </div>
  ),
});

interface MapContainerProps {
  taxiStates: Record<string, TaxiState>;
  baseStates: Record<string, BaseState>;
  activeAssignments: Record<string, Assignment>;
}

export function MapContainer({
  taxiStates,
  baseStates,
  activeAssignments,
}: MapContainerProps) {
  return (
    <MapContent
      taxiStates={taxiStates}
      baseStates={baseStates}
      activeAssignments={activeAssignments}
    />
  );
}
