import * as FileSystem from 'expo-file-system/legacy';
import * as Sharing from 'expo-sharing';

function getMediaDir(): string {
  try {
    const base = FileSystem?.documentDirectory || FileSystem?.cacheDirectory || '';
    return `${base}manvix_media/`;
  } catch {
    return 'manvix_media/';
  }
}

/**
 * Ensures the internal on-device storage directory exists.
 */
export async function ensureMediaDirectory(): Promise<string> {
  const mediaDir = getMediaDir();
  try {
    if (FileSystem?.getInfoAsync) {
      const dirInfo = await FileSystem.getInfoAsync(mediaDir);
      if (!dirInfo.exists && FileSystem.makeDirectoryAsync) {
        await FileSystem.makeDirectoryAsync(mediaDir, { intermediates: true });
      }
    }
  } catch (err) {
    console.warn('ensureMediaDirectory error:', err);
  }
  return mediaDir;
}

/**
 * Saves an image to internal app memory (100% on-device sandboxed filesystem).
 */
export async function saveMediaToInternalStorage(filename: string, fileDataOrUri: string): Promise<string> {
  const mediaDir = await ensureMediaDirectory();
  const targetPath = `${mediaDir}${Date.now()}_${filename}`;

  try {
    if (fileDataOrUri.startsWith('file://') || fileDataOrUri.startsWith('content://')) {
      if (FileSystem?.copyAsync) {
        await FileSystem.copyAsync({
          from: fileDataOrUri,
          to: targetPath,
        });
      }
    } else if (fileDataOrUri.startsWith('data:image/')) {
      const base64Data = fileDataOrUri.split(',')[1] || fileDataOrUri;
      if (FileSystem?.writeAsStringAsync) {
        await FileSystem.writeAsStringAsync(targetPath, base64Data, {
          encoding: FileSystem.EncodingType.Base64,
        });
      }
    } else {
      if (FileSystem?.writeAsStringAsync) {
        await FileSystem.writeAsStringAsync(targetPath, fileDataOrUri, {
          encoding: FileSystem.EncodingType.Base64,
        });
      }
    }
  } catch (e) {
    console.warn('saveMediaToInternalStorage error:', e);
  }

  return targetPath;
}

/**
 * Saves/exports a media file to device storage or photo gallery via native Android intent.
 */
export async function exportToDeviceGallery(localUri: string): Promise<boolean> {
  try {
    const isAvailable = await Sharing.isAvailableAsync();
    if (isAvailable && localUri && !localUri.startsWith('bundled://')) {
      await Sharing.shareAsync(localUri, {
        mimeType: 'image/png',
        dialogTitle: 'Save / Export MANVIX AI Creative',
        UTI: 'public.png',
      });
      return true;
    }
    return true;
  } catch (err) {
    console.warn('exportToDeviceGallery error:', err);
    return false;
  }
}

/**
 * Calculates total internal storage used by MANVIX AI media in bytes.
 */
export async function getInternalStorageUsage(): Promise<{ fileCount: number; totalSizeBytes: number; readableSize: string }> {
  try {
    const mediaDir = await ensureMediaDirectory();
    if (!FileSystem?.readDirectoryAsync) {
      return { fileCount: 0, totalSizeBytes: 0, readableSize: '0 KB' };
    }

    const files = await FileSystem.readDirectoryAsync(mediaDir);
    let totalSize = 0;

    for (const file of files) {
      const info = await FileSystem.getInfoAsync(`${mediaDir}${file}`);
      if (info.exists && !info.isDirectory) {
        totalSize += info.size || 0;
      }
    }

    const readableSize =
      totalSize < 1024
        ? `${totalSize} B`
        : totalSize < 1024 * 1024
        ? `${(totalSize / 1024).toFixed(1)} KB`
        : `${(totalSize / (1024 * 1024)).toFixed(2)} MB`;

    return {
      fileCount: files.length,
      totalSizeBytes: totalSize,
      readableSize,
    };
  } catch (e) {
    return { fileCount: 0, totalSizeBytes: 0, readableSize: '0 KB' };
  }
}
