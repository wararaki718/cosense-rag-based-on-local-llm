/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // Local LLM access might need to bypass some checks if using HTTP
  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
