/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Standalone output ships only the files the server actually needs, which
  // keeps the runtime image small and free of the build toolchain.
  output: "standalone",

  // The browser always calls /api on the origin it loaded the page from, so no
  // cross-origin request is ever made and no CORS policy has to be relaxed.
  //
  // In production Caddy intercepts /api before Next.js sees it, so this rewrite
  // never fires there. Running locally there is no proxy, and without this the
  // browser asks Next.js for /api and gets a 404 while the API sits healthy on
  // another port — which surfaces as "the search could not be completed" and
  // looks like the backend is down when it is not.
  async rewrites() {
    const target = process.env.TAFAHHUM_API_ORIGIN ?? "http://127.0.0.1:8000";
    return [{ source: "/api/:path*", destination: `${target}/api/:path*` }];
  },
};

export default nextConfig;
