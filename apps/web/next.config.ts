import type { NextConfig } from "next";

const nextConfig = {
  async rewrites() {
    // Khi deploy tách (Vercel + backend riêng): NEXT_PUBLIC_AGENT_API_URL
    // được set → frontend gọi ABSOLUTE tới backend → không cần proxy.
    // Khi chạy 1 container (Render/start.sh): không set env → proxy /api/*
    // sang backend FastAPI cùng container (port 8000).
    if (process.env.NEXT_PUBLIC_AGENT_API_URL) {
      return [];
    }
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      {
        source: "/backend/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;