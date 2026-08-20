/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Standalone output ships only the files the server actually needs, which
  // keeps the runtime image small and free of the build toolchain.
  output: "standalone",
};
export default nextConfig;
