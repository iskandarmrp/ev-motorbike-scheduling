import { useGlobalSearchParams } from "expo-router";
import { View, Text, ScrollView, StyleSheet } from "react-native";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function JadwalMotor() {
  const { id } = useGlobalSearchParams();
  const { data, connected } = useWebSocket("ws://192.168.1.104:8001/ws/status");

  if (!connected) return <Text>Menyambung ke server...</Text>;
  if (!data) return <Text>Menunggu data...</Text>;

  const motorId = parseInt(id as string);

  const schedules = data.swap_schedules
    .filter((s) => String(s.ev_id) === String(id))
    .sort(
      (a, b) =>
        new Date(b.scheduled_time).getTime() -
        new Date(a.scheduled_time).getTime()
    );

  const formatDate = (raw: string) => {
    const date = new Date(raw);
    const pad = (n: number) => String(n).padStart(2, "0");
    return `${pad(date.getDate())}-${pad(
      date.getMonth() + 1
    )}-${date.getFullYear()} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const findStationAddress = (stationId: number) => {
    const station = data.battery_swap_station.find((st) => st.id === stationId);
    return station?.alamat || "Alamat tidak ditemukan";
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Jadwal Penukaran Motor #{motorId}</Text>
      {schedules.length === 0 ? (
        <Text style={styles.empty}>Belum ada jadwal</Text>
      ) : (
        schedules.map((s) => (
          <View key={s.id} style={styles.card}>
            <Text style={styles.label}>Stasiun Penukaran Baterai:</Text>
            <Text style={styles.value}>
              {findStationAddress(s.battery_station)}
            </Text>

            <Text style={styles.label}>Slot:</Text>
            <Text style={styles.value}>{s.slot + 1}</Text>

            <Text style={styles.label}>Status:</Text>
            <Text style={styles.value}>{s.status}</Text>

            <Text style={styles.label}>Waktu:</Text>
            <Text style={styles.value}>{formatDate(s.scheduled_time)}</Text>
          </View>
        ))
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 20,
    paddingTop: 60,
    backgroundColor: "#f0f2f5",
  },
  title: {
    fontSize: 20,
    fontWeight: "bold",
    marginBottom: 20,
    textAlign: "center",
  },
  empty: {
    textAlign: "center",
    fontStyle: "italic",
    color: "#888",
  },
  card: {
    backgroundColor: "#fff",
    padding: 16,
    borderRadius: 12,
    marginBottom: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 3,
    elevation: 3,
  },
  label: {
    fontWeight: "bold",
    fontSize: 14,
    color: "#333",
  },
  value: {
    fontSize: 14,
    marginBottom: 8,
    color: "#555",
  },
});
