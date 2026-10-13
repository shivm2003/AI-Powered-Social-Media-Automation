"""
AES-256-GCM Encryption & Decryption module for credentials.
Full two-way compatibility with Node.js crypto (scryptSync + aes-256-gcm).
Payload format: base64(salt [32 bytes] + iv [16 bytes] + tag [16 bytes] + ciphertext)
"""
import base64
import os
import sqlite3
import logging
from pathlib import Path

# Load environment variables from .env.local and .env
try:
    from dotenv import load_dotenv
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    load_dotenv(BASE_DIR / ".env.local")
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent

DB_PATH = BASE_DIR / "data" / "database.sqlite"

logger = logging.getLogger("automation.encryption")

SALT_LENGTH = 32
IV_LENGTH = 16
TAG_LENGTH = 16
KEY_LENGTH = 32

# Try importing cryptography primitives at module level
try:
    from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    logger.warning("cryptography package not installed. Run: pip install cryptography")


def get_master_secret() -> bytes:
    """
    Retrieve master secret from environment (.env.local / env vars) or database settings.
    Guarantees synchronization with Node.js backend.
    """
    # 1. First priority: Environment variable MASTER_PASSPHRASE (from .env.local or shell)
    env_pass = os.environ.get("MASTER_PASSPHRASE")
    if env_pass:
        secret_bytes = env_pass.strip().encode("utf-8")
        if DB_PATH.exists():
            try:
                conn = sqlite3.connect(DB_PATH)
                cur = conn.cursor()
                cur.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('encryption_master_secret', ?)", (env_pass.strip(),))
                conn.commit()
                conn.close()
            except Exception:
                pass
        return secret_bytes

    # 2. Second priority: PostgreSQL settings table
    try:
        import psycopg2
        pg_user = os.environ.get("DB_USER", "postgres")
        pg_pass = os.environ.get("DB_PASSWORD", "Shivam@123")
        pg_host = os.environ.get("DB_HOST", "localhost")
        pg_port = int(os.environ.get("DB_PORT", "5432"))
        pg_db = os.environ.get("DB_NAME", "Social_Media")
        conn = psycopg2.connect(dbname=pg_db, user=pg_user, password=pg_pass, host=pg_host, port=pg_port)
        cur = conn.cursor()
        cur.execute("SELECT value FROM settings WHERE key = 'encryption_master_secret'")
        row = cur.fetchone()
        cur.close()
        conn.close()
        if row and row[0]:
            return row[0].strip().encode("utf-8")
    except Exception:
        pass

    # 3. Third priority: SQLite settings table (encryption_master_secret)
    if DB_PATH.exists():
        try:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT value FROM settings WHERE key = 'encryption_master_secret'")
            row = cur.fetchone()
            conn.close()
            if row and row[0]:
                return row[0].strip().encode("utf-8")
        except Exception as e:
            logger.debug(f"Could not read encryption_master_secret from DB: {e}")

    # 4. Fallback secret
    return b"ai-social-media-secure-local-vault-2026"


def encrypt_password(plain_text: str) -> str:
    """
    Encrypts plain text using AES-256-GCM and scrypt key derivation.
    Output: base64(salt [32] + iv [16] + tag [16] + ciphertext).
    100% binary-compatible with Node.js crypto.
    """
    if not plain_text:
        return ""

    if not HAS_CRYPTOGRAPHY:
        logger.error("Cannot encrypt password: cryptography package is not installed.")
        return plain_text

    try:
        salt = os.urandom(SALT_LENGTH)
        iv = os.urandom(IV_LENGTH)
        secret = get_master_secret()

        # Node.js scryptSync defaults: N=16384, r=8, p=1, length=32
        kdf = Scrypt(salt=salt, length=KEY_LENGTH, n=16384, r=8, p=1)
        derived_key = kdf.derive(secret)

        aesgcm = AESGCM(derived_key)
        # AESGCM.encrypt returns ciphertext + 16-byte authentication tag
        encrypted_with_tag = aesgcm.encrypt(iv, plain_text.encode("utf-8"), None)
        ciphertext = encrypted_with_tag[:-TAG_LENGTH]
        tag = encrypted_with_tag[-TAG_LENGTH:]

        # Layout matching Node.js: salt (32) + iv (16) + tag (16) + ciphertext
        combined = salt + iv + tag + ciphertext
        return base64.b64encode(combined).decode("utf-8")
    except Exception as e:
        logger.error(f"Encryption failed: {e}", exc_info=True)
        raise


def decrypt_password(cipher_base64: str) -> str:
    """
    Decrypts a base64 payload formatted as: salt (32) + iv (16) + tag (16) + ciphertext.
    Returns plain text. Falls back gracefully if input is already plain text.
    """
    if not cipher_base64:
        return ""

    # Check if this might be an unencrypted plain text password
    try:
        raw = base64.b64decode(cipher_base64, validate=True)
    except Exception:
        # Not base64, assume plain text
        return cipher_base64

    # If payload is shorter than header (salt + iv + tag = 64 bytes), it's not our encrypted format
    if len(raw) < SALT_LENGTH + IV_LENGTH + TAG_LENGTH:
        return cipher_base64

    if not HAS_CRYPTOGRAPHY:
        logger.warning("cryptography package missing, returning raw payload.")
        return cipher_base64

    try:
        salt = raw[:SALT_LENGTH]
        iv = raw[SALT_LENGTH : SALT_LENGTH + IV_LENGTH]
        tag = raw[SALT_LENGTH + IV_LENGTH : SALT_LENGTH + IV_LENGTH + TAG_LENGTH]
        ciphertext = raw[SALT_LENGTH + IV_LENGTH + TAG_LENGTH :]

        secret = get_master_secret()

        # Derive same 256-bit key using scrypt
        kdf = Scrypt(salt=salt, length=KEY_LENGTH, n=16384, r=8, p=1)
        derived_key = kdf.derive(secret)

        aesgcm = AESGCM(derived_key)
        # AESGCM.decrypt expects ciphertext + tag
        decrypted_bytes = aesgcm.decrypt(iv, ciphertext + tag, None)
        return decrypted_bytes.decode("utf-8")
    except Exception as e:
        logger.warning(f"Failed to decrypt password payload (key mismatch or unencrypted): {e}")
        # If decryption fails (e.g. was plain text that happened to be 64+ bytes), return as-is
        return cipher_base64


def test_roundtrip(sample: str = "TestSecretPassword123!") -> bool:
    """Verifies that encrypt and decrypt roundtrip matches perfectly."""
    encrypted = encrypt_password(sample)
    decrypted = decrypt_password(encrypted)
    return sample == decrypted


if __name__ == "__main__":
    import sys
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("\n--- AES-256-GCM Encryption Self-Test ---")
    secret = get_master_secret()
    print(f"Master Secret:        Loaded ({len(secret)} bytes)")
    
    sample_text = "MySecureSocialPassword2026!"
    print(f"Plain Text:           {sample_text}")
    
    encrypted_payload = encrypt_password(sample_text)
    print(f"Encrypted (Base64):   {encrypted_payload}")
    
    decrypted_text = decrypt_password(encrypted_payload)
    print(f"Decrypted:            {decrypted_text}")
    
    success = (sample_text == decrypted_text)
    print(f"Roundtrip Status:     {'[SUCCESS - Matched!]' if success else '[FAILED]'}\n")
