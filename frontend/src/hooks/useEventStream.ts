"use client";

import { useEffect, useSyncExternalStore } from "react";

export interface LeaderboardEntry {
  token: string;
  pseudonym: string;
  total_amount: number;
  badge: string;
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

const SERVER_SNAPSHOT: GlobalState = { connectionState: "disconnected", leaderboardData: [], lastUpdate: 0 };

const store = {
  subscribe(callback: () => void) {
    subscribers.add(callback);
    return () => subscribers.delete(callback);
  },
  getSnapshot() {
    return state;
  },
  getServerSnapshot() {
    return SERVER_SNAPSHOT;
  },
};

let eventSource: EventSource | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout> | null = null;
let heartbeatTimeout: ReturnType<typeof setTimeout> | null = null;

const resetHeartbeat = () => {
  if (heartbeatTimeout) clearTimeout(heartbeatTimeout);
  heartbeatTimeout = setTimeout(() => {
    // If we haven't received a ping or message in 20 seconds, consider the connection dead
    console.warn("SSE heartbeat timeout, forcing reconnect...");
    state = { ...state, connectionState: "disconnected" };
    emitChange();
    eventSource?.close();
    eventSource = null;
    if (reconnectTimeout) clearTimeout(reconnectTimeout);
    reconnectTimeout = setTimeout(connectSSE, 3000);
  }, 35000); // 35 seconds
};

const connectSSE = () => {
  if (eventSource && (eventSource.readyState === EventSource.OPEN || eventSource.readyState === EventSource.CONNECTING)) {
    return;
  }

  state = { ...state, connectionState: "connecting" };
  emitChange();

  try {
    // Bypass Next.js Turbopack proxy in development for SSE because it buffers streaming responses
    const isDev = process.env.NODE_ENV === "development";
    const sseUrl = isDev ? "http://localhost:8000/api/v1/events/stream" : "/api/v1/events/stream";
    eventSource = new EventSource(sseUrl);

    eventSource.onopen = () => {
      state = { ...state, connectionState: "connected" };
      emitChange();
      resetHeartbeat();
    };

    const fetchLeaderboard = async () => {
      try {
        const res = await fetch("/api/v1/financial/leaderboard");
        if (res.ok) {
          const data = await res.json();
          state = { ...state, leaderboardData: data, lastUpdate: Date.now() };
          emitChange();
        }
      } catch (err) {
        console.error("Failed to fetch leaderboard", err);
      }
    };

    // Fetch initial data
    fetchLeaderboard();

    eventSource.addEventListener("new_donation", (event) => {
      resetHeartbeat();
      // Whenever a new donation occurs, refetch the leaderboard
      fetchLeaderboard();
    });

    eventSource.addEventListener("ping", (event) => {
      // console.log("Received ping");
      resetHeartbeat();
    });

    eventSource.onmessage = (event) => {
      // Catch-all for unnamed events
      resetHeartbeat();
    };

    eventSource.onerror = () => {
      state = { ...state, connectionState: "disconnected" };
      emitChange();
      eventSource?.close();
      eventSource = null;

      if (heartbeatTimeout) clearTimeout(heartbeatTimeout);
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
