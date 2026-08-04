const path = require('path');
const nextDistDir = process.env.NEXT_DIST_DIR || '.next';

/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['xn--114-2p7l635dz3bh5j.com', 'localhost', '127.0.0.1'],
  distDir: nextDistDir,
  pageExtensions: ['ts', 'tsx'],
  experimental: {
    optimizePackageImports: ['lucide-react'],
  },
  compress: true,
  images: {
    formats: ['image/avif', 'image/webp'],
    minimumCacheTTL: 300,
    dangerouslyAllowSVG: false,
  },
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    return [{
      source: '/api/:path*',
      destination: '/api/backend-proxy/:path*',
    }, ];
  },
};

module.exports = nextConfig;