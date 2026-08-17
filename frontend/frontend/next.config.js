const path = require('path');
const nextDistDir = process.env.NEXT_DIST_DIR || '.next';
const backendTarget = process.env.BACKEND_PROXY_TARGET || process.env.LOCAL_API_BASE_URL || 'http://localhost:8000';

/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['metanova1004.com', 'localhost', '127.0.0.1'],
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
      source: '/api/backend-proxy/:path*',
      destination: `${backendTarget}/api/:path*`,
    }, {
      source: '/api/:path*',
      destination: `${backendTarget}/api/:path*`,
    }, {
      source: '/docs',
      destination: `${backendTarget}/docs`,
    }, {
      source: '/openapi.json',
      destination: `${backendTarget}/openapi.json`,
    }, ];
  },
};

module.exports = nextConfig;