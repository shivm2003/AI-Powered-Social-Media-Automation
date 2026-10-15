import { Linking, Platform } from 'react-native';
import * as Sharing from 'expo-sharing';
import * as Clipboard from 'expo-clipboard';

export type SupportedPlatform = 'facebook' | 'instagram' | 'whatsapp' | 'linkedin';

export interface PlatformConfig {
  id: SupportedPlatform;
  name: string;
  packageName: string; // Android package
  color: string;
  glowColor: string;
  scheme: string;
  iconText: string;
}

export const PLATFORMS_CONFIG: Record<SupportedPlatform, PlatformConfig> = {
  instagram: {
    id: 'instagram',
    name: 'Instagram',
    packageName: 'com.instagram.android',
    color: '#E4405F',
    glowColor: 'rgba(228, 64, 95, 0.5)',
    scheme: 'instagram://app',
    iconText: '📸',
  },
  facebook: {
    id: 'facebook',
    name: 'Facebook',
    packageName: 'com.facebook.katana',
    color: '#1877F2',
    glowColor: 'rgba(24, 119, 242, 0.5)',
    scheme: 'fb://facewebmodal/f?href=https://facebook.com',
    iconText: '👥',
  },
  whatsapp: {
    id: 'whatsapp',
    name: 'WhatsApp',
    packageName: 'com.whatsapp',
    color: '#25D366',
    glowColor: 'rgba(37, 211, 102, 0.5)',
    scheme: 'whatsapp://send',
    iconText: '💬',
  },
  linkedin: {
    id: 'linkedin',
    name: 'LinkedIn',
    packageName: 'com.linkedin.android',
    color: '#0A66C2',
    glowColor: 'rgba(10, 102, 194, 0.5)',
    scheme: 'linkedin://',
    iconText: '💼',
  },
};

/**
 * Copies the viral marketing post caption and Apply Link to device clipboard.
 */
export async function copyCaptionToClipboard(caption: string, applyUrl?: string): Promise<void> {
  const fullText = applyUrl && !caption.includes(applyUrl) 
    ? `${caption}\n\n👉 Apply Now: ${applyUrl}`
    : caption;
  await Clipboard.setStringAsync(fullText);
}

/**
 * Checks if a specific app package or scheme is installed on the mobile device.
 */
export async function isPlatformAppInstalled(platform: SupportedPlatform): Promise<boolean> {
  const config = PLATFORMS_CONFIG[platform];
  if (!config) return false;

  try {
    return await Linking.canOpenURL(config.scheme);
  } catch {
    return false;
  }
}

/**
 * Shares directly to a target platform or launches standard Android Intent sharing.
 */
export async function shareToSinglePlatform(
  platform: SupportedPlatform,
  mediaUri: string,
  caption: string,
  applyUrl?: string
): Promise<{ success: boolean; method: 'direct_app' | 'sharesheet' | 'clipboard_only'; error?: string }> {
  // Always copy caption + link to clipboard so user can immediately paste in target app composer
  await copyCaptionToClipboard(caption, applyUrl);

  const config = PLATFORMS_CONFIG[platform];

  // Specific Direct Deep-Link handling
  if (platform === 'whatsapp') {
    const encodedText = encodeURIComponent(`${caption}\n\n👉 Apply Now: ${applyUrl || ''}`);
    const waUrl = `whatsapp://send?text=${encodedText}`;
    const canOpenWA = await Linking.canOpenURL(waUrl);
    if (canOpenWA) {
      await Linking.openURL(waUrl);
      return { success: true, method: 'direct_app' };
    }
  }

  // File-based Sharing for Instagram / Facebook / LinkedIn / WhatsApp
  const isSharingAvailable = await Sharing.isAvailableAsync();
  if (isSharingAvailable && mediaUri && !mediaUri.startsWith('bundled://')) {
    try {
      await Sharing.shareAsync(mediaUri, {
        mimeType: 'image/png',
        dialogTitle: `MANVIX AI -> Share to ${config.name}`,
        UTI: 'public.png',
      });
      return { success: true, method: 'sharesheet' };
    } catch (e: any) {
      console.warn(`Sharing error for ${platform}:`, e);
    }
  }

  // Fallback to launching the app directly
  const canOpenApp = await Linking.canOpenURL(config.scheme);
  if (canOpenApp) {
    await Linking.openURL(config.scheme);
    return { success: true, method: 'direct_app' };
  }

  return { success: true, method: 'clipboard_only' };
}

/**
 * Multi-Platform Broadcast:
 * Iterates through selected platforms and prepares native intent sharing sequentially.
 */
export async function broadcastToMultiplePlatforms(
  platforms: SupportedPlatform[],
  mediaUri: string,
  caption: string,
  applyUrl?: string,
  onStepProgress?: (platform: SupportedPlatform, index: number, total: number) => void
): Promise<{ results: Record<SupportedPlatform, boolean> }> {
  await copyCaptionToClipboard(caption, applyUrl);

  const results: Record<SupportedPlatform, boolean> = {
    facebook: false,
    instagram: false,
    whatsapp: false,
    linkedin: false,
  };

  for (let i = 0; i < platforms.length; i++) {
    const plat = platforms[i];
    if (onStepProgress) {
      onStepProgress(plat, i + 1, platforms.length);
    }

    const res = await shareToSinglePlatform(plat, mediaUri, caption, applyUrl);
    results[plat] = res.success;
  }

  return { results };
}
