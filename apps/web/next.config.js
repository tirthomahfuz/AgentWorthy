/** @type {import('next').NextConfig} */
const nextConfig = {
  // Standalone is for Docker self-hosting only; Vercel/Netlify use their own output.
  ...(process.env.DOCKER_BUILD === "true" ? { output: "standalone" } : {}),
};

module.exports = nextConfig;
