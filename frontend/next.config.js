/** @type {import('next').NextConfig} */
const nextConfig = {
  // React strict mode for better dev experience
  reactStrictMode: true,
  
  // Image domains for user avatars, generated images, etc.
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'lh3.googleusercontent.com', // Google profile photos
      },
      {
        protocol: 'https',
        hostname: '*.supabase.co', // Supabase storage
      },
      {
        protocol: 'https',
        hostname: 'res.cloudinary.com', // Cloudinary image storage
      },
      {
        protocol: 'https',
        hostname: '*.cloudinary.com', // Cloudinary subdomains
      },
      {
        protocol: 'https',
        hostname: 'replicate.delivery', // Replicate generated images
      },
      {
        protocol: 'https',
        hostname: '*.replicate.delivery', // Replicate subdomains
      },
    ],
  },
  
  // Suppress hydration warnings (useful for timestamps, etc.)
  compiler: {
    // Remove console.logs in production
    removeConsole: process.env.NODE_ENV === 'production' ? { exclude: ['error', 'warn'] } : false,
  },
  
  // Environment variables exposed to the client
  // (these are set in Vercel dashboard)
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_GOOGLE_CLIENT_ID: process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID,
  },
  
  // Output as standalone for Docker/server deployment if needed
  // output: 'standalone',
  
  // Experimental features
  experimental: {
    // Better server actions support
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
};

module.exports = nextConfig;

