/** @type {import('next').NextConfig} */
const nextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  outputFileTracingExcludes: {
    '*': [
      'chrome_profiles/**/*',
      'data/**/*',
      'logs/**/*',
      'automation/**/*',
      'graphify-out/**/*',
    ],
  },
};

export default nextConfig;
