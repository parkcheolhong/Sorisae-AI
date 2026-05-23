const path = require('path');
const nextDistDir = process.env.NEXT_DIST_DIR || '.next';

/** @type {import('next').NextConfig} */
const nextConfig = {
  allowedDevOrigins: ['metanova1004.com', 'localhost', '127.0.0.1'],
  distDir: nextDistDir,
  pageExtensions: ['ts', 'tsx'],
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