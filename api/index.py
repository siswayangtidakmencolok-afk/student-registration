import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    send_file,
    abort,
)
from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    DateField,
    SelectField,
    TextAreaField,
    TelField,
    FileField,
)
from wtforms.validators import DataRequired, Email, Length
from werkzeug.utils import secure_filename
import sqlite3
import csv
from datetime import datetime

# ---------- Config ----------
DB_PATH = "/tmp/students.db"
UPLOAD_FOLDER = "/tmp/uploads"
ALLOWED_EXT = {"png", "jpg", "jpeg", "gif"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder="../templates")
app.config["SECRET_KEY"] = "ganti_dengan_secret_key_kamu"  # ganti di produksi
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # max 2MB file


# ---------- Database helpers ----------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute(
        """
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        dob TEXT,
        grade TEXT,
        phone TEXT,
        parent TEXT,
        address TEXT,
        photo TEXT,
        created_at TEXT NOT NULL
    );
    """
    )
    conn.commit()
    conn.close()


init_db()


# ---------- Forms ----------
class RegistrationForm(FlaskForm):
    name = StringField(
        "Nama Lengkap", validators=[DataRequired(), Length(min=2, max=120)]
    )
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    dob = DateField("Tanggal Lahir", format="%Y-%m-%d", validators=[DataRequired()])
    grade = SelectField(
        "Kelas",
        choices=[
            ("7", "7"),
            ("8", "8"),
            ("9", "9"),
            ("10", "10"),
            ("11", "11"),
            ("12", "12"),
        ],
        validators=[DataRequired()],
    )
    phone = TelField(
        "Nomor Telepon", validators=[DataRequired(), Length(min=8, max=20)]
    )
    parent = StringField(
        "Nama Orang Tua / Wali", validators=[DataRequired(), Length(min=2, max=120)]
    )
    address = TextAreaField(
        "Alamat", validators=[DataRequired(), Length(min=5, max=500)]
    )
    photo = FileField("Foto (opsional)")


# ---------- Helpers ----------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT


# ---------- Routes ----------
@app.route("/", methods=["GET", "POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        name = form.name.data.strip()
        email = form.email.data.strip().lower()
        dob = form.dob.data.strftime("%Y-%m-%d")
        grade = form.grade.data
        phone = form.phone.data.strip()
        parent = form.parent.data.strip()
        address = form.address.data.strip()

        # handle photo upload
        photo_filename = None
        f = request.files.get("photo")
        if f and f.filename:
            if allowed_file(f.filename):
                filename = secure_filename(f.filename)
                # add timestamp to filename to avoid collisions
                ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
                filename = f"{ts}_{filename}"
                save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                f.save(save_path)
                photo_filename = filename
            else:
                flash(
                    "Format file foto tidak diperbolehkan. Hanya png/jpg/jpeg/gif.",
                    "danger",
                )
                return redirect(url_for("register"))

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO students (name, email, dob, grade, phone, parent, address, photo, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                name,
                email,
                dob,
                grade,
                phone,
                parent,
                address,
                photo_filename,
                datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

        flash("Pendaftaran berhasil! Terima kasih.", "success")
        return redirect(url_for("list_students"))

    return render_template("register.html", form=form)


@app.route("/students")
def list_students():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY created_at DESC").fetchall()
    conn.close()
    return render_template("list.html", students=rows)


@app.route("/download_csv")
def download_csv():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM students ORDER BY created_at DESC").fetchall()
    conn.close()

    if not rows:
        flash("Belum ada data untuk diunduh.", "warning")
        return redirect(url_for("list_students"))

    csv_path = "/tmp/students_export.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "id",
                "name",
                "email",
                "dob",
                "grade",
                "phone",
                "parent",
                "address",
                "photo",
                "created_at",
            ]
        )
        for r in rows:
            writer.writerow(
                [
                    r["id"],
                    r["name"],
                    r["email"],
                    r["dob"],
                    r["grade"],
                    r["phone"],
                    r["parent"],
                    r["address"],
                    r["photo"],
                    r["created_at"],
                ]
            )
    return send_file(csv_path, as_attachment=True)


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    if os.path.exists(path):
        return send_file(path)
    abort(404)


# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
