import os
import sqlite3
import smtplib
from email.message import EmailMessage
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "quotes.db"


def load_env_file() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ[key.strip()] = value.strip().strip('"').strip("'")


def get_smtp_config() -> dict:
    load_env_file()
    return {
        "recipient_email": os.environ.get("QUOTE_EMAIL", "alex@goodmanwash.com"),
        "smtp_host": os.environ.get("SMTP_HOST", ""),
        "smtp_port": int(os.environ.get("SMTP_PORT", "587")),
        "smtp_username": os.environ.get("SMTP_USERNAME", ""),
        "smtp_password": os.environ.get("SMTP_PASSWORD", ""),
        "smtp_use_tls": os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
    }


def init_db() -> None:
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            email TEXT NOT NULL,
            services TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def save_quote(data: dict) -> int:
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """
        INSERT INTO quotes (name, phone, address, email, services)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            data.get("name", "").strip(),
            data.get("phone", "").strip(),
            data.get("address", "").strip(),
            data.get("email", "").strip(),
            data.get("services", "").strip(),
        ),
    )
    conn.commit()
    quote_id = cursor.lastrowid
    conn.close()
    return quote_id


def send_email(data: dict, config: dict) -> tuple[bool, str]:
    if not config["smtp_host"] or not config["smtp_username"] or not config["smtp_password"]:
        return False, "SMTP not configured; lead was saved locally only."

    msg = EmailMessage()
    msg["Subject"] = "New Quote Request From Goodman Pressure Washing"
    msg["From"] = config["smtp_username"]
    msg["To"] = config["recipient_email"]
    msg.set_content(
        "\n".join(
            [
                "New quote request received:",
                f"Name: {data.get('name', '').strip()}",
                f"Phone: {data.get('phone', '').strip()}",
                f"Address: {data.get('address', '').strip()}",
                f"Email: {data.get('email', '').strip()}",
                "Services:",
                data.get("services", "").strip(),
            ]
        )
    )

    try:
        with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
            if config["smtp_use_tls"]:
                server.starttls()
            server.login(config["smtp_username"], config["smtp_password"])
            server.send_message(msg)
        return True, "Thanks, we’ll be in touch soon."
    except Exception as exc:
        return False, f"Email send failed: {exc}"


class QuoteHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self.path = "/index.html"
        elif path == "/quote":
            self.path = "/quote.html"
        super().do_GET()

    def do_POST(self):
        path = urlparse(self.path).path
        if path != "/submit-quote":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        data = {key: values[0] if values else "" for key, values in parse_qs(body, keep_blank_values=True).items()}

        missing = [field for field in ("name", "phone", "address", "email", "services") if not data.get(field, "").strip()]
        if missing:
            self.send_response(400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                """
                <html><body><h2>Missing required information.</h2>
                <p>Please complete all fields and try again.</p>
                <p><a href="/quote.html">Back to form</a></p></body></html>
                """.encode("utf-8")
            )
            return

        quote_id = save_quote(data)
        print(f"Lead saved with ID {quote_id}")
        config = get_smtp_config()
        email_sent, email_message = send_email(data, config)

        success_html = f"""
        <!DOCTYPE html>
        <html lang=\"en\">
        <head>
            <meta charset=\"UTF-8\">
            <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
            <title>Quote Request Received</title>
            <style>
                body {{ font-family: Segoe UI, sans-serif; background: #f8fafc; color: #1e293b; padding: 40px; }}
                .card {{ max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; padding: 32px; box-shadow: 0 10px 30px rgba(15, 23, 42, 0.08); }}
                h1 {{ color: #0f172a; margin-bottom: 12px; }}
                p {{ margin-bottom: 12px; }}
                a {{ color: #0284c7; font-weight: 700; }}
            </style>
        </head>
        <body>
            <div class=\"card\">
                <h1>Thank you for your quote request.</h1>
                <p>Your information has been received.</p>
                <p>{email_message}</p>
                <p><a href=\"/\">Return to the homepage</a></p>
            </div>
        </body>
        </html>
        """

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(success_html.encode("utf-8"))


if __name__ == "__main__":
    init_db()
    config = get_smtp_config()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), QuoteHandler)
    print(f"Quote form server running at http://{host}:{port}")
    print(f"Leads will be stored in {DB_PATH}")
    print(f"Email recipient: {config['recipient_email']}")
    server.serve_forever()
