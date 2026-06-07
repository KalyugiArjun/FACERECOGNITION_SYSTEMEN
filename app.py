from flask import Flask, render_template, request, redirect, session, send_file, flash
import sqlite3
import os
from datetime import datetime
import csv

app = Flask(__name__)
app.secret_key = "faceattend_secure_2024"

# ============================================================
# DATABASE INIT — auto-create tables if missing
# ============================================================
def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        enrollment TEXT UNIQUE,
        department TEXT,
        year TEXT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'student',
        image TEXT DEFAULT ''
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT,
        time TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()

# ============================================================
# LOGIN
# ============================================================
@app.route('/')
def login():
    error = request.args.get('error')
    return render_template('login.html', error=error)

@app.route('/register_page')
def register_page():
    return render_template('register.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form['username'].strip().lower()
    password = request.form['password'].strip()

    conn   = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, name, role FROM users
        WHERE LOWER(username)=? AND password=?
    """, (username, password))
    user = cursor.fetchone()
    conn.close()

    if user is None:
        return redirect('/?error=Invalid+Username+or+Password')

    session['id']   = user[0]
    session['user'] = user[1]
    session['role'] = user[2]

    if   session['role'] == "student":   return redirect('/student')
    elif session['role'] == "teacher":   return redirect('/teacher')
    elif session['role'] == "principal": return redirect('/principal')
    return redirect('/?error=Unknown+role')

# ============================================================
# REGISTER
# ============================================================
@app.route('/register', methods=['POST'])
def register():
    name     = request.form['name'].strip()
    enroll   = request.form['enrollment'].strip()
    dept     = request.form['department'].strip()
    year     = request.form['year'].strip()
    username = request.form['username'].strip().lower()
    password = request.form['password'].strip()

    conn   = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users(name,enrollment,department,year,username,password,role)
            VALUES(?,?,?,?,?,?,?)
        """, (name, enroll, dept, year, username, password, "student"))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return redirect('/?error=Username+or+Enrollment+already+exists')
    conn.close()

    # Create dataset folder and capture faces
    path = os.path.join("dataset", name.lower())
    os.makedirs(path, exist_ok=True)
    os.system(f'python capture.py "{name.lower()}"')

    return redirect('/')

# ============================================================
# STUDENT
# ============================================================
@app.route('/student')
def student():
    if 'user' not in session:
        return redirect('/')

    name = session['user']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date,time FROM attendance WHERE name=?", (name,))
    data = cursor.fetchall()
    conn.close()

    present = len(data)
    total   = 30
    percent = round((present / total) * 100, 1) if total else 0

    return render_template('student_dashboard.html',
                           data=data, total=total,
                           present=present, percent=percent, name=name)

@app.route('/profile')
def profile():
    if 'id' not in session:
        return redirect('/')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name,enrollment,department,year,username,image
        FROM users WHERE id=?
    """, (session['id'],))
    profile = cursor.fetchone()
    conn.close()
    return render_template("student_profile.html", profile=profile)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    uid      = session['id']
    name     = request.form['name']
    dept     = request.form['department']
    year     = request.form['year']
    password = request.form['password']
    file     = request.files.get('image')

    os.makedirs('static/profile', exist_ok=True)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if file and file.filename:
        img_name = file.filename
        file.save(os.path.join("static/profile", img_name))
        cursor.execute("""
            UPDATE users SET name=?,department=?,year=?,password=?,image=? WHERE id=?
        """, (name, dept, year, password, img_name, uid))
    else:
        cursor.execute("""
            UPDATE users SET name=?,department=?,year=?,password=? WHERE id=?
        """, (name, dept, year, password, uid))

    conn.commit()
    conn.close()
    return redirect('/profile')

# ============================================================
# TEACHER
# ============================================================
@app.route('/teacher')
def teacher():
    if 'user' not in session or session.get('role') != 'teacher':
        return redirect('/')

    dataset_path = 'dataset'
    students = []
    if os.path.exists(dataset_path):
        students = [f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f))]

    total_students = len(students)

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("SELECT name FROM attendance WHERE date=?", (today,))
    data = cursor.fetchall()
    conn.close()

    present_list = [i[0].lower() for i in data]
    absent_list  = [s.lower() for s in students if s.lower() not in present_list]
    present_count = len(present_list)
    absent_count  = len(absent_list)
    percent = int((present_count / total_students) * 100) if total_students else 0

    return render_template("teacher_dashboard.html",
                           total=total_students, present=present_count,
                           absent=absent_count, percent=percent,
                           plist=present_list, alist=absent_list)

@app.route('/manual_mark/<name>')
def manual_mark(name):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    time  = datetime.now().strftime("%H:%M:%S")
    cursor.execute("SELECT * FROM attendance WHERE name=? AND date=?", (name, today))
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO attendance(name,date,time) VALUES(?,?,?)", (name, today, time))
        conn.commit()
    conn.close()
    return redirect('/teacher')

@app.route('/delete/<name>')
def delete(name):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    cursor.execute("DELETE FROM attendance WHERE name=? AND date=?", (name, today))
    conn.commit()
    conn.close()
    return redirect('/teacher')

@app.route('/export_today')
def export_today():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE date=?", (today,))
    data = cursor.fetchall()
    conn.close()
    with open('today_attendance.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ID', 'Name', 'Date', 'Time'])
        writer.writerows(data)
    return send_file('today_attendance.csv', as_attachment=True)

@app.route('/date_filter', methods=['POST'])
def date_filter():
    if 'user' not in session:
        return redirect('/')
    selected_date = request.form['date']
    dataset_path  = 'dataset'
    students = []
    if os.path.exists(dataset_path):
        students = [f for f in os.listdir(dataset_path) if os.path.isdir(os.path.join(dataset_path, f))]
    total = len(students)
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM attendance WHERE date=?", (selected_date,))
    data = cursor.fetchall()
    conn.close()
    present = [i[0].lower() for i in data]
    absent  = [s.lower() for s in students if s.lower() not in present]
    present_count = len(present)
    absent_count  = len(absent)
    percent = int((present_count / total) * 100) if total else 0
    return render_template("teacher_dashboard.html",
                           total=total, present=present_count,
                           absent=absent_count, percent=percent,
                           plist=present, alist=absent)

@app.route('/start_attendance')
def start_attendance():
    if 'role' not in session or session['role'] != 'teacher':
        return redirect('/')
    os.system("python recognize.py")
    return redirect('/teacher')

# ============================================================
# PRINCIPAL
# ============================================================
@app.route('/principal')
def principal():
    if 'role' not in session or session['role'] != 'principal':
        return redirect('/')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT name,enrollment,department,year FROM users WHERE role='student'")
    students = cursor.fetchall()
    total_students = len(students)

    cursor.execute("SELECT name FROM attendance WHERE date=?", (today,))
    data = cursor.fetchall()
    conn.close()

    present_list = [i[0] for i in data]
    absent_list  = [s[0] for s in students if s[0] not in present_list]
    present_students = len(present_list)
    absent_students  = len(absent_list)
    percent = int((present_students / total_students) * 100) if total_students else 0

    return render_template('principal_dashboard.html',
                           students=students,
                           total_students=total_students,
                           present_students=present_students,
                           absent_students=absent_students,
                           percent=percent,
                           plist=present_list,
                           alist=absent_list)

@app.route('/delete_student/<enroll>')
def delete_student(enroll):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE enrollment=?", (enroll,))
    conn.commit()
    conn.close()
    return redirect('/principal')

@app.route('/add_student', methods=['POST'])
def add_student():
    name     = request.form['name'].strip()
    enroll   = request.form['enrollment'].strip()
    dept     = request.form['department'].strip()
    year     = request.form['year'].strip()
    username = request.form['username'].strip().lower()
    password = request.form['password'].strip()
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users(name,enrollment,department,year,username,password,role)
            VALUES(?,?,?,?,?,?,?)
        """, (name, enroll, dept, year, username, password, "student"))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect('/principal')

@app.route('/edit_student/<enroll>')
def edit_student(enroll):
    if 'role' not in session or session['role'] != 'principal':
        return redirect('/')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name,enrollment,department,year FROM users WHERE enrollment=?", (enroll,))
    student = cursor.fetchone()
    conn.close()
    return render_template('edit_student.html', student=student)

@app.route('/update_student', methods=['POST'])
def update_student():
    name  = request.form['name']
    enroll = request.form['enrollment']
    dept  = request.form['department']
    year  = request.form['year']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name=?,department=?,year=? WHERE enrollment=?",
                   (name, dept, year, enroll))
    conn.commit()
    conn.close()
    return redirect('/principal')

@app.route('/principal_date_filter', methods=['POST'])
def principal_date_filter():
    selected_date = request.form['date']
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(DISTINCT name) FROM attendance WHERE date=?", (selected_date,))
    present_students = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM users WHERE role='student'")
    total_students = cursor.fetchone()[0]
    cursor.execute("SELECT name,enrollment,department,year FROM users WHERE role='student'")
    students = cursor.fetchall()
    conn.close()

    absent_students = total_students - present_students
    percent = int((present_students / total_students) * 100) if total_students else 0

    return render_template('principal_dashboard.html',
                           students=students,
                           total_students=total_students,
                           present_students=present_students,
                           absent_students=absent_students,
                           percent=percent,
                           plist=[], alist=[])

@app.route('/system_reset')
def system_reset():
    if 'role' not in session or session['role'] != 'principal':
        return redirect('/')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE role='student'")
    cursor.execute("DELETE FROM attendance")
    conn.commit()
    conn.close()

    dataset_path = "dataset"
    if os.path.exists(dataset_path):
        for folder in os.listdir(dataset_path):
            fp = os.path.join(dataset_path, folder)
            if os.path.isdir(fp):
                for f in os.listdir(fp):
                    os.remove(os.path.join(fp, f))
                os.rmdir(fp)

    for f in ['trainer/trainer.yml', 'trainer/labels.json', 'attendance.csv', 'today_attendance.csv']:
        if os.path.exists(f):
            os.remove(f)

    return redirect('/principal')

# ============================================================
# DOWNLOAD + LOGOUT
# ============================================================
@app.route('/download')
def download():
    username = session.get('user', '').lower()
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT date,time FROM attendance WHERE name=?", (username,))
    data = cursor.fetchall()
    conn.close()
    with open('attendance.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Time'])
        writer.writerows(data)
    return send_file('attendance.csv', as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
