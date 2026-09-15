import os
from datetime import datetime

import pymysql
import pymysql.cursors
from flask import Flask, jsonify, render_template, request
from zoneinfo import ZoneInfo

app = Flask(__name__)

ist_tz = ZoneInfo("Asia/Kolkata")

# Parse port safely since cloud databases like Aiven use custom port integers
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


# Automatically initialize the database on startup when run by Gunicorn
try:
    init_db()
    print("Database successfully initialized or already exists.")
except Exception as e:
    print(f"Database initialization warning (App will try running anyway): {e}")


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
