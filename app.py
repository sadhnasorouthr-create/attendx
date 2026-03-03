import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

# Ensure instance folder exists (important for Render)
os.makedirs("instance", exist_ok=True)

DATABASE = os.path.join("instance", os.environ.get("DATABASE_PATH", "attendance.db"))


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                attended INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


# 👇 IMPORTANT: DB initialize on startup (works with gunicorn)
init_db()


def calc_percentage(attended, total):
    if total == 0:
        return 0.0
    return round((attended / total) * 100, 2)


def predict_attendance(attended, total, extra_total, extra_attend):
    new_total = total + extra_total
    new_attended = attended + extra_attend
    return calc_percentage(new_attended, new_total)


def classes_needed_for_75(attended, total):
    if calc_percentage(attended, total) >= 75:
        return 0
    needed = (0.75 * total - attended) / 0.25
    return max(0, int(needed) + 1)


def classes_can_skip(attended, total):
    if calc_percentage(attended, total) < 75:
        return 0
    skippable = (attended - 0.75 * total) / 0.75
    return max(0, int(skippable))


@app.route("/")
def index():
    with get_db() as conn:
        subjects = conn.execute("SELECT * FROM subjects ORDER BY created_at DESC").fetchall()

    enriched = []
    for s in subjects:
        pct = calc_percentage(s["attended"], s["total"])
        enriched.append({
            "id": s["id"],
            "name": s["name"],
            "total": s["total"],
            "attended": s["attended"],
            "pct": pct,
            "status": "danger" if pct < 75 else ("warning" if pct < 80 else "safe"),
            "need": classes_needed_for_75(s["attended"], s["total"]),
            "can_skip": classes_can_skip(s["attended"], s["total"]),
        })

    overall_total = sum(s["total"] for s in subjects)
    overall_attended = sum(s["attended"] for s in subjects)
    overall_pct = calc_percentage(overall_attended, overall_total)

    return render_template(
        "index.html",
        subjects=enriched,
        overall_pct=overall_pct,
        overall_total=overall_total,
        overall_attended=overall_attended,
    )


@app.route("/add", methods=["POST"])
def add_subject():
    name = request.form.get("name", "").strip()
    total = request.form.get("total", 0)
    attended = request.form.get("attended", 0)

    if not name:
        flash("Subject name cannot be empty.", "error")
        return redirect(url_for("index"))

    try:
        total = int(total)
        attended = int(attended)
    except ValueError:
        flash("Total and attended must be numbers.", "error")
        return redirect(url_for("index"))

    if total < 0 or attended < 0:
        flash("Values cannot be negative.", "error")
        return redirect(url_for("index"))

    if attended > total:
        flash("Attended cannot exceed total.", "error")
        return redirect(url_for("index"))

    with get_db() as conn:
        conn.execute(
            "INSERT INTO subjects (name, total, attended) VALUES (?, ?, ?)",
            (name, total, attended),
        )
        conn.commit()

    flash(f"{name} added successfully!", "success")
    return redirect(url_for("index"))


@app.route("/update/<int:subject_id>", methods=["POST"])
def update_subject(subject_id):
    total = request.form.get("total", 0)
    attended = request.form.get("attended", 0)

    try:
        total = int(total)
        attended = int(attended)
    except ValueError:
        flash("Values must be numbers.", "error")
        return redirect(url_for("index"))

    if total < 0 or attended < 0:
        flash("Values cannot be negative.", "error")
        return redirect(url_for("index"))

    if attended > total:
        flash("Attended cannot exceed total.", "error")
        return redirect(url_for("index"))

    with get_db() as conn:
        conn.execute(
            "UPDATE subjects SET total=?, attended=? WHERE id=?",
            (total, attended, subject_id),
        )
        conn.commit()

    flash("Updated successfully!", "success")
    return redirect(url_for("index"))


@app.route("/delete/<int:subject_id>", methods=["POST"])
def delete_subject(subject_id):
    with get_db() as conn:
        conn.execute("DELETE FROM subjects WHERE id=?", (subject_id,))
        conn.commit()
    flash("Subject deleted.", "info")
    return redirect(url_for("index"))


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()

    try:
        attended = int(data["attended"])
        total = int(data["total"])
        extra_total = int(data["extra_total"])
        extra_attend = int(data["extra_attend"])
    except (KeyError, ValueError, TypeError):
        return jsonify({"error": "Invalid input"}), 400

    if extra_attend > extra_total:
        return jsonify({"error": "Cannot attend more than total future classes"}), 400

    pct = predict_attendance(attended, total, extra_total, extra_attend)

    return jsonify({
        "predicted_pct": pct,
        "status": "danger" if pct < 75 else ("warning" if pct < 80 else "safe"),
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "production") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)