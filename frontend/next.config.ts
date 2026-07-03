import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_SAFEOPS_API: process.env.NEXT_PUBLIC_SAFEOPS_API ?? "http://localhost:8000",
  },
};

export default nextConfig;
