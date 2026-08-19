/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  env: {
    TAFAHHUM_API: process.env.TAFAHHUM_API ?? "http://127.0.0.1:8000",
  },
};
export default nextConfig;
