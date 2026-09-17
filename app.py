import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime

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

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM", "onboarding@resend.dev")
NOTIFY_EMAIL = os.environ.get("NOTIFY_EMAIL", "abhiabhi4a@gmail.com")


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
                    day ENUM('Today', 'Tomorrow', 'Some other day'),
                    time_slot ENUM('9pm & late night', '5pm - 9pm', '3 - 5 (I am busy)'),
                    food VARCHAR(50),
                    shared_message TEXT,
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
    """Email NOTIFY_EMAIL whenever a new response comes in, via Resend's
    HTTPS API. Failures here are logged but never break the save/response
    flow."""
    if not RESEND_API_KEY:
        print("Email notification skipped: RESEND_API_KEY not set.")
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

    payload = json.dumps({
        "from": RESEND_FROM,
        "to": [NOTIFY_EMAIL],
        "subject": "New response on your page 💌",
        "text": body,
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
            # Cloudflare (which fronts Resend's API) blocks requests with
            # the default Python-urllib User-Agent as bot traffic (error
            # code 1010). A normal-looking UA avoids that.
            "User-Agent": "Mozilla/5.0 (compatible; askher-app/1.0)",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            print(f"Email notification sent. (HTTP {resp.status})")
    except urllib.error.HTTPError as err:
        detail = err.read().decode("utf-8", errors="ignore")
        print(f"Email notification failed: HTTP {err.code} — {detail}")
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
        "shared_message": data.get("message"),
        "saved_at": datetime.now(ist_tz),
    }

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO responses (response, day, time_slot, food, shared_message, saved_at)
                VALUES (%(response)s, %(day)s, %(time_slot)s, %(food)s, %(shared_message)s, %(saved_at)s)
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
                "SELECT id, response, day, time_slot, food, shared_message, saved_at "
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
