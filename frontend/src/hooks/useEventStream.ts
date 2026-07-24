"use client";

import { useEffect, useSyncExternalStore } from "react";

export interface LeaderboardEntry {
  id: string;
  name: string;
  score: number;
  avatar: string;
  trend: "up" | "down" | "flat";
  combo?: number;
}

type ConnectionState = "connecting" | "connected" | "disconnected";

interface GlobalState {
  connectionState: ConnectionState;
  leaderboardData: LeaderboardEntry[];
  lastUpdate: number;
}

let state: GlobalState = {
  connectionState: "disconnected",
  leaderboardData: [],
  lastUpdate: Date.now(),
};

const subscribers = new Set<() => void>();

const emitChange = () => {
  subscribers.forEach((callback) => callback());
};

const store = {
  subscribe(callback: () => void) {
    subscribers.add(callback);
    return () => subscribers.delete(callback);
  },
  getSnapshot() {
    return state;
  },
  getServerSnapshot() {
    return { connectionState: "disconnected" as const, leaderboardData: [], lastUpdate: 0 };
  },
};

let eventSource: EventSource | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;

const connectSSE = () => {
  if (eventSource && (eventSource.readyState === EventSource.OPEN || eventSource.readyState === EventSource.CONNECTING)) {
    return;
  }

  state = { ...state, connectionState: "connecting" };
  emitChange();

  try {
    eventSource = new EventSource("/api/v1/events/stream");

    eventSource.onopen = () => {
      state = { ...state, connectionState: "connected" };
      emitChange();
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "leaderboard_update") {
          state = { 
            ...state, 
            leaderboardData: data.payload, 
            lastUpdate: Date.now() 
          };
          emitChange();
        }
      } catch (error) {
        console.error("Failed to parse SSE data:", error);
      }
    };

    eventSource.onerror = () => {
      state = { ...state, connectionState: "disconnected" };
      emitChange();
      eventSource?.close();
      eventSource = null;

      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      reconnectTimeout = setTimeout(connectSSE, 3000);
    };
  } catch (error) {
    state = { ...state, connectionState: "disconnected" };
    emitChange();
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    reconnectTimeout = setTimeout(connectSSE, 3000);
  }
};

export function useEventStream() {
  const currentState = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getServerSnapshot);

  useEffect(() => {
    connectSSE();
  }, []);

  return currentState;
}
