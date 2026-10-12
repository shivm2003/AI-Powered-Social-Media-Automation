import crypto from "crypto";
import { getSetting, setSetting } from "./db.js";

// Algorithm: AES-256-GCM
const ALGORITHM = "aes-256-gcm";
const IV_LENGTH = 16;
const SALT_LENGTH = 32;
const KEY_LENGTH = 32;

/**
 * Get or create the master encryption key from DB or environment.
 */
function getMasterSecret() {
  if (process.env.MASTER_PASSPHRASE) {
    const pass = process.env.MASTER_PASSPHRASE.trim();
    setSetting("encryption_master_secret", pass);
    return pass;
  }
  let secret = getSetting("encryption_master_secret");
  if (!secret) {
    secret = crypto.randomBytes(32).toString("hex");
    setSetting("encryption_master_secret", secret);
  }
  return secret;
}

/**
 * Encrypt plain text using AES-256-GCM.
 * Output format: base64(salt + iv + tag + ciphertext)
 */
export function encrypt(text) {
  if (!text) return "";
  try {
    const salt = crypto.randomBytes(SALT_LENGTH);
    const iv = crypto.randomBytes(IV_LENGTH);
    const key = crypto.scryptSync(getMasterSecret(), salt, KEY_LENGTH);

    const cipher = crypto.createCipheriv(ALGORITHM, key, iv);
    const encrypted = Buffer.concat([cipher.update(text, "utf8"), cipher.final()]);
    const tag = cipher.getAuthTag();

    const combined = Buffer.concat([salt, iv, tag, encrypted]);
    return combined.toString("base64");
  } catch (err) {
    console.error("Encryption error:", err);
    throw err;
  }
}

/**
 * Decrypt ciphertext encrypted with AES-256-GCM.
 */
export function decrypt(cipherTextBase64) {
  if (!cipherTextBase64) return "";
  try {
    const combined = Buffer.from(cipherTextBase64, "base64");
    if (combined.length < SALT_LENGTH + IV_LENGTH + 16) {
      // Return as-is if not valid encrypted payload (e.g. legacy plain text)
      return cipherTextBase64;
    }

    const salt = combined.subarray(0, SALT_LENGTH);
    const iv = combined.subarray(SALT_LENGTH, SALT_LENGTH + IV_LENGTH);
    const tag = combined.subarray(SALT_LENGTH + IV_LENGTH, SALT_LENGTH + IV_LENGTH + 16);
    const ciphertext = combined.subarray(SALT_LENGTH + IV_LENGTH + 16);

    const key = crypto.scryptSync(getMasterSecret(), salt, KEY_LENGTH);
    const decipher = crypto.createDecipheriv(ALGORITHM, key, iv);
    decipher.setAuthTag(tag);

    const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
    return decrypted.toString("utf8");
  } catch (err) {
    console.error("Decryption error:", err);
    // If decryption fails (e.g. was plain text), fallback to original string
    return cipherTextBase64;
  }
}
