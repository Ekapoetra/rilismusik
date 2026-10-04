"""Start the existing full API on an always-on container, never on a Function.

--check validates configuration only. It does not connect to MongoDB, R2,
SMTP or Xendit and cannot certify a live deployment as ready.
"""
import argparse
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

REQUIRED = (
    "MONGO_URL", "DB_NAME", "JWT_SECRET", "FRONTEND_URL",
    "SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASSWORD",
    "SENDER_EMAIL", "SENDER_NAME", "R2_ENDPOINT_URL",
    "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET",
    "XENDIT_SECRET_KEY", "XENDIT_RETURN_URL_BASE", "UPLOAD_DIR",
)


def https_origin(value):
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == "https" and bool(parsed.hostname)
                and not parsed.username and not parsed.password
                and not parsed.query and not parsed.fragment
                and parsed.path in ("", "/"))
    except ValueError:
        return False


def configuration_errors(env):
    # Report variable names and fixed messages only; never their values.
    errors = [f"{key} belum diisi" for key in REQUIRED if not env.get(key, "").strip()]
    if env.get("RILISMUSIK_DEPLOYMENT_MODE") != "production":
        errors.append("RILISMUSIK_DEPLOYMENT_MODE harus production")
    if env.get("VERCEL") == "1":
        errors.append("Launcher ini memerlukan container yang terus menyala, bukan Vercel Function")
    if env.get("MONGO_URL") and not env["MONGO_URL"].startswith(("mongodb://", "mongodb+srv://")):
        errors.append("Format MONGO_URL tidak sesuai")
    for key in ("FRONTEND_URL", "XENDIT_RETURN_URL_BASE"):
        if env.get(key) and not https_origin(env[key]):
            errors.append(f"{key} harus origin HTTPS tanpa path")
    if (env.get("FRONTEND_URL") and env.get("XENDIT_RETURN_URL_BASE")
            and env["FRONTEND_URL"].rstrip("/") != env["XENDIT_RETURN_URL_BASE"].rstrip("/")):
        errors.append("XENDIT_RETURN_URL_BASE harus mengikuti FRONTEND_URL")
    for key, default in (("PORT", "8000"), ("SMTP_PORT", "")):
        value = env.get(key, default)
        if not value.isdigit() or not 1 <= int(value) <= 65535:
            errors.append(f"{key} harus port 1–65535")
    if env.get("XENDIT_ALLOW_MOCK_PAY", "false").lower() != "false":
        errors.append("XENDIT_ALLOW_MOCK_PAY harus false pada production")
    if (env.get("XENDIT_WEBHOOK_ENABLED", "false").lower() == "true"
            and not env.get("XENDIT_WEBHOOK_VERIFICATION_TOKEN", "").strip()):
        errors.append("XENDIT_WEBHOOK_VERIFICATION_TOKEN wajib untuk webhook aktif")
    directory = env.get("UPLOAD_DIR", "")
    if directory and (not Path(directory).is_absolute() or directory.startswith("/tmp/")):
        errors.append("UPLOAD_DIR harus direktori absolut pada volume persisten, bukan /tmp")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    errors = configuration_errors(os.environ)
    if errors:
        print("Konfigurasi production belum lengkap:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 2
    if args.check:
        print("Format konfigurasi lulus. Koneksi layanan, volume persisten, dan alur aplikasi belum diuji.")
        return 0
    directory = Path(os.environ["UPLOAD_DIR"])
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError:
        print("UPLOAD_DIR tidak dapat dibuat; periksa volume dan izin tulis.", file=sys.stderr)
        return 2
    os.chdir(Path(__file__).resolve().parents[1])
    # One process and one replica: the legacy scheduler and startup recovery
    # are retained. Horizontal scaling needs their separate migration first.
    os.execvp(sys.executable, [sys.executable, "-m", "uvicorn", "server:app",
                             "--host", "0.0.0.0", "--port", os.environ.get("PORT", "8000"),
                             "--workers", "1"])


if __name__ == "__main__":
    sys.exit(main())
