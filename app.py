import os
import smtplib
import socket
import threading
from datetime import datetime
from email.message import EmailMessage

import pymysql
import pymysql.cursors
from flask import Flask, jsonify, render_template, request
from zoneinfo import ZoneInfo

app = Flask(__name__)

ist_tz = ZoneInfo("Asia/Kolkata")


DB_PORT = int(os.environ.get("DB_PORT", 3306))

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "root"),
    "database": os.environ.get("DB_NAME", "date_proposal"),
    "port": DB_PORT,
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

MAIL_CONFIG = {
    "server": os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
    "port": int(os.environ.get("MAIL_PORT", "465")),
    "username": os.environ.get("MAIL_USERNAME", ""),
    "password": os.environ.get("MAIL_PASSWORD", ""),
}
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "abhiabhi4a@gmail.com")


class SMTP_SSL_IPv4(smtplib.SMTP_SSL):
    """Some hosts (e.g. Render) can't route outbound IPv6, but smtplib's
    default connection logic may try an IPv6 address for smtp.gmail.com
    and fail with 'Network is unreachable'. This forces IPv4 while still
    validating the TLS certificate against the real hostname."""

    def _get_socket(self, host, port, timeout):
        addr_info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        family, socktype, proto, _, sockaddr = addr_info[0]
        sock = socket.socket(family, socktype, proto)
        if timeout is not None:
            sock.settimeout(timeout)
        sock.connect(sockaddr)
        return self.context.wrap_socket(sock, server_hostname=self._host)


def get_connection():
    """Open a fresh MySQL connection."""
    return pymysql.connect(**DB_CONFIG)


def init_db():
    """Create the responses table if it doesn't already exist."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS responses (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    response VARCHAR(10) NOT NULL,
                    day VARCHAR(20),
                    time_slot VARCHAR(50),
                    food VARCHAR(50),
                    saved_at DATETIME NOT NULL
                )
                """
            )
    finally:
        conn.close()

try:
    init_db()
    print("Database successfully initialized or already exists.")
except Exception as e:
    print(f"Database initialization warning (App will try running anyway): {e}")


def send_notification_email(record):
    """Email NOTIFY_EMAIL whenever a new response comes in.
    Failures here are logged but never break the save/response flow."""
    if not MAIL_CONFIG["username"] or not MAIL_CONFIG["password"]:
        print("Email notification skipped: MAIL_USERNAME/MAIL_PASSWORD not set.")
        return

    when = record["saved_at"].strftime("%Y-%m-%d %H:%M %Z")
    body = (
        f"Someone just responded!\n\n"
        f"Response: {record['response']}\n"
        f"Day: {record['day'] or '—'}\n"
        f"Time: {record['time_slot'] or '—'}\n"
        f"Mood/food: {record['food'] or '—'}\n"
        f"Saved at: {when}\n"
    )

    msg = EmailMessage()
    msg["Subject"] = "New response on your page 💌"
    msg["From"] = MAIL_CONFIG["username"]
    msg["To"] = NOTIFY_EMAIL
    msg.set_content(body)

    try:

        with SMTP_SSL_IPv4(MAIL_CONFIG["server"], MAIL_CONFIG["port"], timeout=10) as smtp:
            smtp.login(MAIL_CONFIG["username"], MAIL_CONFIG["password"])
            smtp.send_message(msg)
        print("Email notification sent.")
    except Exception as err: 
        print(f"Email notification failed: {err}")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/respond", methods=["POST"])
def save_response():
    data = request.get_json(silent=True) or {}

    record = {
        "response": data.get("response", "yes")[:10],
        "day": data.get("day"),
        "time_slot": data.get("time"),
        "food": data.get("food"),
        "saved_at": datetime.now(ist_tz),
    }

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO responses (response, day, time_slot, food, saved_at)
                VALUES (%(response)s, %(day)s, %(time_slot)s, %(food)s, %(saved_at)s)
                """,
                record,
            )
            new_id = cursor.lastrowid

        threading.Thread(target=send_notification_email, args=(record,), daemon=True).start()
        return jsonify({"ok": True, "id": new_id}), 201
    except pymysql.MySQLError as err:
        return jsonify({"ok": False, "error": str(err)}), 500
    finally:
        conn.close()


@app.route("/api/responses", methods=["GET"])
def list_responses():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id, response, day, time_slot, food, saved_at "
                "FROM responses ORDER BY saved_at DESC"
            )
            rows = cursor.fetchall()
        for row in rows:
            if isinstance(row.get("saved_at"), datetime):
                row["saved_at"] = row["saved_at"].isoformat()
        return jsonify({"ok": True, "responses": rows})
    except pymysql.MySQLError as err:
        return jsonify({"ok": False, "error": str(err)}), 500
    finally:
        conn.close()


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
