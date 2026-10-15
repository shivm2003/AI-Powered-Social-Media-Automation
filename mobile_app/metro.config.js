const { getDefaultConfig } = require('expo/metro-config');

const config = getDefaultConfig(__dirname);

// Enable .wasm asset support for expo-sqlite web / wa-sqlite
config.resolver.assetExts.push('wasm');

module.exports = config;
