// The browser only ever talks to this app's own origin — every /api/* request is
// proxied server-side (by this Next.js server, not the browser) to the backend.
// This is deliberate, not just convenient: it avoids relying on a NEXT_PUBLIC_*
// build-time variable ever reaching the client bundle correctly on a given hosting
// platform's Docker build (that class of bug is exactly what broke the first Render
// deploy — a build ARG that didn't get threaded through as expected), and it avoids
// needing any CORS configuration at all, since same-origin requests aren't subject
// to CORS in the first place. INTERNAL_API_URL is read fresh at request time by the
// Next.js server process, which every hosting platform sets as a normal runtime
// environment variable — a much more certain mechanism than build-time inlining.
// Accepts either a full URL ("http://backend:8000") or a bare hostname
// ("bondaudit-backend.onrender.com") — Render's Blueprint `fromService` cross-service
// references only ever resolve to a bare host, never a scheme.
const RAW_BACKEND_URL = process.env.INTERNAL_API_URL || "http://localhost:8000";
const BACKEND_URL = /^https?:\/\//.test(RAW_BACKEND_URL) ? RAW_BACKEND_URL : `https://${RAW_BACKEND_URL}`;

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${BACKEND_URL}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
