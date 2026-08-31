"use client";

import { useEffect } from "react";

export function PwaRegister() {
  useEffect(() => {
    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch((err) => {
      // Installability/offline fallback is a progressive enhancement — never block
      // the app if registration fails (e.g. unsupported browser, blocked storage).
      console.warn("Service worker registration failed:", err);
    });
  }, []);

  return null;
}
