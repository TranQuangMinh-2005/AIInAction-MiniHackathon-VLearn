import type { NextConfig } from "next";

const nextConfig = {
  async rewrites() {
    return [
      // Backend chạy CÙNG container (start.sh: uvicorn port 8000) —
      // proxy mọi /api/* về 8000 để web + api chung 1 origin.
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
      // Legacy: rewrite cũ giữ lại cho tương thích
      {
        source: "/backend/:path*",
        destination: "http://localhost:8000/:path*",
      },
    ];
  },
};

export default nextConfig;