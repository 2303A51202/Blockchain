from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3, hashlib, json
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB = "students.db"
ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"  # Change this before deployment.

def connect():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def make_hash(data):
    return hashlib.sha256(data.encode("utf-8")).hexdigest()

def init_db():
    with connect() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            course TEXT NOT NULL,
            year TEXT NOT NULL,
            email TEXT,
            created_at TEXT NOT NULL
        )""")
        con.execute("""CREATE TABLE IF NOT EXISTS blocks (
            idx INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            action TEXT NOT NULL,
            student_roll TEXT NOT NULL,
            payload TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            block_hash TEXT NOT NULL
        )""")

def add_block(action, roll, payload):
    with connect() as con:
        last = con.execute("SELECT block_hash FROM blocks ORDER BY idx DESC LIMIT 1").fetchone()
        previous_hash = last["block_hash"] if last else "0" * 64
        timestamp = datetime.now().isoformat(timespec="seconds")
        payload_text = json.dumps(payload, sort_keys=True)
        raw = f"{timestamp}|{action}|{roll}|{payload_text}|{previous_hash}"
        block_hash = make_hash(raw)
        con.execute("""INSERT INTO blocks
            (timestamp, action, student_roll, payload, previous_hash, block_hash)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (timestamp, action, roll, payload_text, previous_hash, block_hash))

def verify_chain():
    with connect() as con:
        blocks = con.execute("SELECT * FROM blocks ORDER BY idx").fetchall()
    previous = "0" * 64
    for block in blocks:
        raw = f'{block["timestamp"]}|{block["action"]}|{block["student_roll"]}|{block["payload"]}|{block["previous_hash"]}'
        expected = make_hash(raw)
        if block["previous_hash"] != previous or block["block_hash"] != expected:
            return False, block["idx"]
        previous = block["block_hash"]
    return True, len(blocks)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    with connect() as con:
        total = con.execute("SELECT COUNT(*) n FROM students").fetchone()["n"]
        recent = con.execute("SELECT * FROM students ORDER BY id DESC LIMIT 5").fetchall()
        blocks = con.execute("SELECT COUNT(*) n FROM blocks").fetchone()["n"]
    valid, checked = verify_chain()
    return render_template("index.html", total=total, recent=recent, blocks=blocks,
                           valid=valid, checked=checked)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form.get("username") == ADMIN_USER and request.form.get("password") == ADMIN_PASSWORD:
            session["logged_in"] = True
            flash("Welcome back!", "success")
            return redirect(url_for("students"))
        flash("Invalid username or password.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/students")
@login_required
def students():
    q = request.args.get("q", "").strip()
    with connect() as con:
        if q:
            rows = con.execute("""SELECT * FROM students WHERE roll_no LIKE ? OR name LIKE ?
                OR course LIKE ? ORDER BY id DESC""", (f"%{q}%", f"%{q}%", f"%{q}%")).fetchall()
        else:
            rows = con.execute("SELECT * FROM students ORDER BY id DESC").fetchall()
    return render_template("students.html", students=rows, q=q)

@app.route("/students/add", methods=["GET", "POST"])
@login_required
def add_student():
    if request.method == "POST":
        data = {k: request.form.get(k, "").strip() for k in ("roll_no", "name", "course", "year", "email")}
        if not all(data[k] for k in ("roll_no", "name", "course", "year")):
            flash("Please fill in roll number, name, course and year.", "error")
            return render_template("student_form.html", student=data, mode="Add")
        try:
            with connect() as con:
                con.execute("""INSERT INTO students (roll_no,name,course,year,email,created_at)
                    VALUES (?,?,?,?,?,?)""", (*data.values(), datetime.now().isoformat(timespec="seconds")))
            add_block("CREATE", data["roll_no"], data)
            flash("Student record added and committed to the blockchain.", "success")
            return redirect(url_for("students"))
        except sqlite3.IntegrityError:
            flash("That roll number already exists.", "error")
    return render_template("student_form.html", student={}, mode="Add")

@app.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@login_required
def edit_student(student_id):
    with connect() as con:
        student = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    if not student:
        flash("Student not found.", "error")
        return redirect(url_for("students"))
    if request.method == "POST":
        data = {k: request.form.get(k, "").strip() for k in ("roll_no", "name", "course", "year", "email")}
        if not all(data[k] for k in ("roll_no", "name", "course", "year")):
            flash("Please fill in all required fields.", "error")
            return render_template("student_form.html", student=data, mode="Edit")
        try:
            with connect() as con:
                con.execute("""UPDATE students SET roll_no=?,name=?,course=?,year=?,email=? WHERE id=?""",
                            (*data.values(), student_id))
            add_block("UPDATE", data["roll_no"], data)
            flash("Student updated and a new blockchain block was created.", "success")
            return redirect(url_for("students"))
        except sqlite3.IntegrityError:
            flash("That roll number is already in use.", "error")
    return render_template("student_form.html", student=student, mode="Edit")

@app.route("/students/<int:student_id>/delete", methods=["POST"])
@login_required
def delete_student(student_id):
    with connect() as con:
        student = con.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
        if student:
            snapshot = dict(student)
            con.execute("DELETE FROM students WHERE id=?", (student_id,))
            add_block("DELETE", student["roll_no"], snapshot)
            flash("Student deleted. The deletion was recorded in the chain.", "success")
    return redirect(url_for("students"))

@app.route("/blockchain")
@login_required
def blockchain():
    with connect() as con:
        blocks = con.execute("SELECT * FROM blocks ORDER BY idx DESC").fetchall()
    valid, checked = verify_chain()
    return render_template("blockchain.html", blocks=blocks, valid=valid, checked=checked)

@app.route("/verify")
@login_required
def verify():
    valid, checked = verify_chain()
    if valid:
        flash(f"Blockchain verified successfully: {checked} block(s) checked.", "success")
    else:
        flash(f"Integrity error detected at block #{checked}.", "error")
    return redirect(url_for("blockchain"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
