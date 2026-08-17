const path = require('path');

const nextDistDir = process.env.NEXT_DIST_DIR || '.next';

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  distDir: nextDistDir,
  turbopack: {
    root: path.resolve(__dirname),
  },
};

module.exports = nextConfig;
