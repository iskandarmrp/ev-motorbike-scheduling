import React, { useState } from "react";
import { View, Text, TextInput, Button, StyleSheet } from "react-native";
import { useRouter } from "expo-router";

export default function Page() {
  const [inputId, setInputId] = useState("");
  const router = useRouter();

  const goToDetail = () => {
    if (!inputId) return;
    router.push({
      pathname: "/motor/[id]",
      params: { id: inputId },
    });
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Masukkan ID Motor</Text>
      <TextInput
        style={styles.input}
        placeholder="Contoh: 5"
        keyboardType="numeric"
        value={inputId}
        onChangeText={setInputId}
      />
      <Button title="Lihat Status Motor" onPress={goToDetail} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { padding: 20, paddingTop: 60 },
  title: { fontSize: 20, fontWeight: "bold", marginBottom: 20 },
  input: {
    borderWidth: 1,
    borderColor: "#ccc",
    padding: 12,
    borderRadius: 6,
    marginBottom: 20,
  },
});
