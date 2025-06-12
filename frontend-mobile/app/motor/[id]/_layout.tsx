import { Tabs } from "expo-router";

export default function MotorTabsLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="index" options={{ title: "Peta" }} />
      <Tabs.Screen name="jadwal" options={{ title: "Jadwal" }} />
      <Tabs.Screen name="station" options={{ title: "Stasiun" }} />
    </Tabs>
  );
}
