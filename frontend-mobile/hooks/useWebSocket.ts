import { useEffect, useRef, useState } from "react";
import { StatusMessage } from "@/hooks/types";

export const useWebSocket = (url: string) => {
  const ws = useRef<WebSocket | null>(null);
  const [data, setData] = useState<StatusMessage | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      console.log("✅ WebSocket connected");
      setConnected(true);
    };

    ws.current.onmessage = (event) => {
      try {
        const msg: StatusMessage = JSON.parse(event.data);
        setData(msg);
      } catch (err) {
        console.error("❌ Error parsing WebSocket message:", err);
      }
    };

    ws.current.onerror = (e) => {
      console.error("❌ WebSocket error:", e);
    };

    ws.current.onclose = () => {
      console.log("🔌 WebSocket disconnected");
      setConnected(false);
    };

    return () => {
      ws.current?.close();
    };
  }, [url]);

  return { data, connected };
};
