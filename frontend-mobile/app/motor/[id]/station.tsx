import { View, Text, ScrollView, StyleSheet } from "react-native";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function SemuaStasiun() {
  const { data, connected } = useWebSocket("ws://192.168.1.104:8001/ws/status");

  if (!connected) return <Text>Menyambung ke server...</Text>;
  if (!data) return <Text>Menunggu data...</Text>;

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Daftar Stasiun Penukaran</Text>
      {data.battery_swap_station.map((s) => (
        <View key={s.id} style={styles.card}>
          <Text>{s.name}</Text>
          <Text>Alamat: {s.alamat}</Text>
          <Text>
            Slot tersedia: {s.slots.length} / {s.total_slots}
          </Text>
          <Text>
            Lokasi: {s.latitude.toFixed(5)}, {s.longitude.toFixed(5)}
          </Text>
        </View>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, paddingTop: 60 },
  title: { fontSize: 20, fontWeight: "bold", marginBottom: 10 },
  card: {
    backgroundColor: "#f2f2f2",
    padding: 12,
    borderRadius: 10,
    marginBottom: 10,
  },
});
