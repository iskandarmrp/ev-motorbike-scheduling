import { useLocalSearchParams, useRouter } from "expo-router";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { useWebSocket } from "@/hooks/useWebSocket";
import MapView, { Marker, Callout } from "react-native-maps";
import { Feather } from "@expo/vector-icons";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useEffect, useRef } from "react";

export default function MotorDetail() {
  const { id } = useLocalSearchParams();
  const router = useRouter();
  const { top } = useSafeAreaInsets();
  const { data, connected } = useWebSocket("ws://192.168.1.104:8001/ws/status");

  const mapRef = useRef<MapView | null>(null);

  const motor = data?.fleet_ev_motorbikes.find(
    (m) => m.id === parseInt(id as string)
  );

  useEffect(() => {
    if (motor && mapRef.current) {
      mapRef.current.animateToRegion(
        {
          latitude: motor.latitude,
          longitude: motor.longitude,
          latitudeDelta: 0.01,
          longitudeDelta: 0.01,
        },
        1000
      );
    }
  }, [motor?.latitude, motor?.longitude]);

  if (!connected) return <Text>🔌 Menyambung ke server...</Text>;
  if (!data) return <Text>📭 Menunggu data...</Text>;
  if (!motor) return <Text>🚫 Motor ID {id} tidak ditemukan.</Text>;

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        style={StyleSheet.absoluteFillObject}
        initialRegion={{
          latitude: motor.latitude,
          longitude: motor.longitude,
          latitudeDelta: 0.01,
          longitudeDelta: 0.01,
        }}
      >
        {/* Marker untuk motor */}
        <Marker
          coordinate={{
            latitude: motor.latitude,
            longitude: motor.longitude,
          }}
          pinColor="red"
        >
          <Callout>
            <Text>Motor #{motor.id}</Text>
          </Callout>
        </Marker>

        {/* Marker untuk semua stasiun baterai */}
        {data.battery_swap_station.map((station) => (
          <Marker
            key={station.id}
            coordinate={{
              latitude: station.latitude,
              longitude: station.longitude,
            }}
            pinColor="blue"
          >
            <Callout>
              <View style={{ maxWidth: 200 }}>
                <Text style={{ fontWeight: "bold" }}>{station.name}</Text>
                <Text>Alamat: {station.alamat}</Text>
                <Text>Slot: {station.total_slots}</Text>
                <Text>
                  Lokasi: {station.latitude.toFixed(5)},{" "}
                  {station.longitude.toFixed(5)}
                </Text>
              </View>
            </Callout>
          </Marker>
        ))}
      </MapView>

      <TouchableOpacity
        style={[styles.backButton, { top: top + 10 }]}
        onPress={() => router.back()}
      >
        <Feather name="arrow-left" size={20} color="white" />
      </TouchableOpacity>

      <View style={styles.infoCard}>
        <Text style={styles.title}>Motor #{motor.id}</Text>
        <Text>Status: {motor.status}</Text>
        <Text>Online: {motor.online_status}</Text>
        <Text>Battery ID: {motor.battery_id}</Text>
        <Text>
          Posisi: {motor.latitude.toFixed(5)}, {motor.longitude.toFixed(5)}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },

  backButton: {
    position: "absolute",
    left: 20,
    top: 0,
    backgroundColor: "rgba(0,0,0,0.6)",
    padding: 10,
    borderRadius: 30,
    zIndex: 10,
  },

  infoCard: {
    position: "absolute",
    bottom: 0,
    width: "100%",
    backgroundColor: "rgba(255,255,255,0.9)",
    padding: 20,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
  },

  title: {
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 10,
  },
});
