from flask import Flask, request, jsonify, render_template_string, render_template, redirect, url_for
import sqlite3
import requests
import json
import hashlib
import secrets
import os
from dotenv import load_dotenv

app = Flask(__name__)
DB_FILE = "db3.db"  # Your SQLite DB

load_dotenv()
OPENROUTER_API_KEY=os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_KEY2=os.getenv("OPENROUTER_API_KEY2")
MODEL_NAME2 = "openai/gpt-oss-120b:free"                                                      # or try: "gpt-3.5-turbo" / "mistral-7b"

# Admin credentials
ADMIN_EMAIL = "1da23ec414.ec@drait.edu.in"
ADMIN_PASSWORD = "Admin@2025"

# Initialize authentication database
def init_auth_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create students table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students_login (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create faculty table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faculty_login (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create study_materials table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            department TEXT NOT NULL,
            semester INTEGER NOT NULL,
            subject_name TEXT NOT NULL,
            link TEXT NOT NULL,
            faculty_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            department TEXT NOT NULL,
            semester INTEGER NOT NULL,
            section TEXT NOT NULL,
            subject TEXT NOT NULL,
            student_name TEXT NOT NULL,
            usn TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('present', 'absent')),
            class_hour INTEGER NOT NULL,
            faculty_email TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create students_info table for attendance management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            semester INTEGER NOT NULL,
            section TEXT NOT NULL,
            roll_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conn.commit()
    # Ensure schema upgrades for existing installations
    try:
        # Attendance table - add missing columns if table existed before
        cursor.execute("PRAGMA table_info(attendance)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        if 'student_name' not in existing_columns:
            cursor.execute("ALTER TABLE attendance ADD COLUMN student_name TEXT")
        if 'usn' not in existing_columns:
            cursor.execute("ALTER TABLE attendance ADD COLUMN usn TEXT")
        if 'class_hour' not in existing_columns:
            cursor.execute("ALTER TABLE attendance ADD COLUMN class_hour INTEGER")
        conn.commit()
    except Exception as e:
        print(f"Schema upgrade warning: {e}")
    finally:
        conn.close()

# Password hashing functions
def hash_password(password):
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return f"{salt}:{password_hash.hex()}"

def verify_password(password, stored_hash):
    try:
        salt, hash_hex = stored_hash.split(':')
        password_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return password_hash.hex() == hash_hex
    except:
        return False

# Authentication functions
def register_user(email, password, role, name=""):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    table = 'students_login' if role == 'student' else 'faculty_login'
    
    try:
        cursor.execute(f'''
            INSERT INTO {table} (email, password_hash, name) 
            VALUES (?, ?, ?)
        ''', (email.lower(), password_hash, name))
        conn.commit()
        conn.close()
        return True, "Registration successful"
    except sqlite3.IntegrityError:
        conn.close()
        return False, "Email already exists"
    except Exception as e:
        conn.close()
        return False, f"Registration failed: {str(e)}"

def authenticate_user(email, password, role):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    table = 'students_login' if role == 'student' else 'faculty_login'
    
    cursor.execute(f'''
        SELECT password_hash, name FROM {table} WHERE email = ?
    ''', (email.lower(),))
    
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        return False, "User not found"
    
    stored_hash, name = result
    
    if verify_password(password, stored_hash):
        return True, {"email": email, "role": role, "name": name}
    else:
        return False, "Invalid password"

# Study Materials Functions
def add_study_material(date, department, semester, subject_name, link, faculty_email):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO study_materials (date, department, semester, subject_name, link, faculty_email) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, department, semester, subject_name, link, faculty_email))
        conn.commit()
        conn.close()
        return True, "Study material added successfully"
    except Exception as e:
        conn.close()
        return False, f"Failed to add study material: {str(e)}"

def get_study_materials(department=None, semester=None):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    if department and semester:
        cursor.execute('''
            SELECT * FROM study_materials 
            WHERE department = ? AND semester = ? 
            ORDER BY created_at DESC
        ''', (department, semester))
    elif department:
        cursor.execute('''
            SELECT * FROM study_materials 
            WHERE department = ? 
            ORDER BY created_at DESC
        ''', (department,))
    else:
        cursor.execute('''
            SELECT * FROM study_materials 
            ORDER BY created_at DESC
        ''')
    
    results = cursor.fetchall()
    conn.close()
    return results

# Attendance Functions
def get_students_by_class(department: str, semester: int, section: str):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT * FROM students_info 
        WHERE department = ? AND semester = ? AND section = ?
        ORDER BY 
            CASE WHEN (SELECT name FROM pragma_table_info('students_info') WHERE name='roll_number') IS NOT NULL THEN roll_number END,
            name
        ''',
        (department, semester, section),
    )

    rows = cursor.fetchall()
    # map columns
    col_names = [desc[0] for desc in cursor.description]
    conn.close()

    students = []
    for row in rows:
        row_dict = {col_names[i]: row[i] for i in range(len(col_names))}
        student = {
            'id': row_dict.get('id'),
            'name': row_dict.get('name') or row_dict.get('student_name') or '',
            'usn': row_dict.get('usn') or row_dict.get('roll_number') or '',
            'department': row_dict.get('department'),
            'semester': row_dict.get('semester'),
            'section': row_dict.get('section'),
        }
        students.append(student)

    return students

def add_attendance_records(attendance_data: list[dict]):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    try:
        print(f"Processing {len(attendance_data)} attendance records")

        for i, record in enumerate(attendance_data):
            print(f"Inserting record {i}: {record}")

            # Ensure record is a tuple/list in the correct order per updated schema:
            # date, department, semester, section, subject, student_name, usn, status, class_hour, faculty_email
            record_tuple = (
                record.get('date'),
                record.get('department'),
                int(record.get('semester')) if record.get('semester') is not None else None,
                record.get('section'),
                record.get('subject'),
                record.get('student_name'),
                record.get('usn'),
                record.get('status'),
                int(record.get('class_hour')) if record.get('class_hour') is not None else None,
                record.get('faculty_email'),
            )

            cursor.execute(
                '''
                INSERT INTO attendance (
                    date, department, semester, section, subject, student_name, usn, status, class_hour, faculty_email
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                record_tuple,
            )

        conn.commit()
        print("All attendance records inserted successfully")
        conn.close()
        return True, "Attendance updated successfully"
    except Exception as e:
        print(f"Error in add_attendance_records: {str(e)}")
        conn.close()
        return False, f"Failed to update attendance: {str(e)}"

# Initialize auth database on startup
init_auth_db()

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

# Utility: get DB schema automatically
def get_db_schema(db_file):
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    schema = {}
    for table_name in tables:
        table = table_name[0]
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        schema[table] = [col[1] for col in columns]  # col[1] is column name
    conn.close()
    return schema

# Generate SQL using Ollama
def generate_sql(user_query, schema):
    """
    Generate SQL query from natural language using OpenRouter API.
    """
    prompt = f"""
You are an AI that converts user questions into SQL queries for a college database.
Database schema:
{schema}

Guidelines:
1. Do NOT use JOINs — tables are not connected by foreign keys.
2. Only respond with a valid single SQL SELECT query (for SQLite).
3. Only apply filters explicitly mentioned in the user's query — don't assume extra conditions.
4. Return plain SQL (no ```sql``` or formatting) with ; at the end of SQL.
5. All identifiers (table/column names) must be lowercase.
6. if shortforms are given like 'ECE' expand it to full "electronics and communication engineering"
7. if sem entered like 7th, seventh, 7th sem, etc: consider it as 7 only. remove all other prefix and only keep number.


User query: "{user_query}"
"""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME2,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 256
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        res_json = response.json()

        # Extract AI-generated SQL
        if "choices" in res_json:
            sql_query = res_json["choices"][0]["message"]["content"].strip()
        else:
            sql_query = "Error: No SQL generated."

        return sql_query

    except Exception as e:
        return f"API Error: {e}"

# Execute SQL safely
def run_sql(sql_query):
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # ✅ Allows name-based column access
        cursor = conn.cursor()
        cursor.execute(sql_query)
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return "No results found."
        
        result = [dict(row) for row in rows]
        print(result)
        return result  

    except Exception as e:
        return {"error": f"SQL Error: {e}"}

#generating final response
def generate_response(user_input, answer):
    if not answer:
        return {"type": "text", "content": "Sorry, I couldn't find any matching information."} 

    prompt = f"""
        You are a helpful and friendly college assistant, your name "NAVYA". Use the following:
        1. User query: {user_input}
        2. Database response: {answer}
        3. to answer the user's query. if user query is like small talk, answer it accordingly dont search database for it.
        4. from a simple phrase, dont give a long answer. dont add symbols like * , # , etc in response.
        5. if {answer} is too long find the most relevant information among them and give answer. Keep the tone polite and conversational.
        6. if it's link, you must provide it as hyperlink to open as: <a href="/link" target="_blank" style="text-decoration:none"><b>Click here</b></a>. if link is not there in database response, don't just make it up.
        7. If asked for for result of an USN provide the latest result only. dont give older results.
        8. if asked for latest updates show results from latest_udates table. dont make it on your own.
        9. never say like "SQL query error", "I couldn't process that", "syntax error", "college database", "error connecting to server" like that. if you dont get db response: apolgize and reply gently.
        """


    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY2}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL_NAME2,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 400 
    }

    try:
        response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        res_json = response.json()

        if "choices" in res_json:
            final_response = res_json["choices"][0]["message"]["content"].strip()
        else:
            final_response = "Error."
        print("----->",final_response)
        return final_response

    except Exception as e:
        return f"API Error: {e}"

# Routes
@app.route('/')
def home():
    #return render_template_string(HTML_PAGE)
    return render_template("index.html")

@app.route('/admin')
def admin_page():
    return render_template('admin_portal.html')

@app.route('/faculty/add-notes')
def add_notes_page():
    return render_template("add_notes.html")

@app.route('/faculty/attendance')
def attendance_page():
    return render_template("attendance.html")

@app.route('/faculty/attendance-report')
def attendance_report_page():
    return render_template("attendance_report.html")

@app.route('/api/register', methods=['POST'])
def api_register():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', '')
        name = data.get('name', '').strip()
        
        if not all([email, password, role]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        if role not in ['student', 'faculty']:
            return jsonify({'success': False, 'message': 'Invalid role'}), 400
        
        success, message = register_user(email, password, role, name)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/login', methods=['POST'])
def api_login():
    try:
        data = request.json
        email = data.get('email', '').strip()
        password = data.get('password', '')
        role = data.get('role', '')
        
        if not all([email, password, role]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Check for admin login
        if role == 'admin':
            if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
                return jsonify({
                    'success': True, 
                    'message': 'Login successful', 
                    'user': {
                        'email': ADMIN_EMAIL,
                        'role': 'admin',
                        'name': 'Administrator'
                    }
                })
            else:
                return jsonify({'success': False, 'message': 'Invalid admin credentials'}), 401
        
        # Existing student/faculty login
        if role not in ['student', 'faculty']:
            return jsonify({'success': False, 'message': 'Invalid role'}), 400
        
        success, result = authenticate_user(email, password, role)
        
        if success:
            return jsonify({'success': True, 'message': 'Login successful', 'user': result})
        else:
            return jsonify({'success': False, 'message': result}), 401
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/add-study-material', methods=['POST'])
def api_add_study_material():
    try:
        data = request.json
        date = data.get('date', '').strip()
        department = data.get('department', '').strip()
        semester = data.get('semester', 0)
        subject_name = data.get('subject_name', '').strip()
        link = data.get('link', '').strip()
        faculty_email = data.get('faculty_email', '').strip()
        
        if not all([date, department, semester, subject_name, link, faculty_email]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        success, message = add_study_material(date, department, semester, subject_name, link, faculty_email)
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/get-students', methods=['POST'])
def api_get_students():
    try:
        data = request.json
        department = data.get('department', '').strip()
        semester = data.get('semester', 0)
        section = data.get('section', '').strip()
        
        if not all([department, semester, section]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        students = get_students_by_class(department, semester, section)
        return jsonify({'success': True, 'students': students})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/add-attendance', methods=['POST'])
def api_add_attendance():
    try:
        data = request.json
        print(f"Received attendance data: {data}")  # Debug log
        
        attendance_data = data.get('attendance_data', [])
        print(f"Attendance records count: {len(attendance_data)}")  # Debug log
        
        if not attendance_data:
            return jsonify({'success': False, 'message': 'No attendance data provided'}), 400
        
        # Log each record being processed
        for i, record in enumerate(attendance_data):
            print(f"Record {i}: {record}")
        
        success, message = add_attendance_records(attendance_data)
        print(f"Database operation result: success={success}, message={message}")  # Debug log
        
        if success:
            return jsonify({'success': True, 'message': message})
        else:
            return jsonify({'success': False, 'message': message}), 400
            
    except Exception as e:
        print(f"Error in api_add_attendance: {str(e)}")  # Debug log
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/api/attendance-report', methods=['POST'])
def api_attendance_report():
    try:
        data = request.json
        department = data.get('department', '').strip()
        semester = int(data.get('semester', 0))
        section = data.get('section', '').strip()
        subject = data.get('subject', '').strip()

        if not all([department, semester, section, subject]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()

        # Aggregate attendance: total classes held per subject and per student breakdown
        cursor.execute('''
            SELECT usn, student_name,
                   SUM(CASE WHEN status IN ('present','absent') THEN 1 ELSE 0 END) AS total_classes,
                   SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) AS attended
            FROM attendance
            WHERE department = ? AND semester = ? AND section = ? AND subject = ?
            GROUP BY usn, student_name
            ORDER BY student_name
        ''', (department, semester, section, subject))

        rows = cursor.fetchall()
        conn.close()

        results = []
        for usn, student_name, total_classes, attended in rows:
            percentage = (attended / total_classes * 100) if total_classes else 0
            results.append({
                'usn': usn,
                'student_name': student_name,
                'total_classes': total_classes,
                'attended': attended,
                'percentage': round(percentage, 2)
            })

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        print(f"Error in api_attendance_report: {str(e)}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route('/ask', methods=['POST'])
def ask():
    user_input = request.json.get('query', "")
    schema = get_db_schema(DB_FILE)
    sql_query = generate_sql(user_input, schema)
    print(sql_query)
    answer = run_sql(sql_query)
    ai_response=generate_response(user_input, answer)
    return jsonify({'answer': ai_response})


# ===== LATEST UPDATE ROUTES =====

@app.route('/api/latest-updates', methods=['GET'])
def get_latest_updates():
    try:
        conn = get_db_connection()
        updates = conn.execute('SELECT * FROM latest_updates ORDER BY date DESC').fetchall()
        conn.close()
        
        updates_list = [dict(row) for row in updates]
        return jsonify({'success': True, 'data': updates_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Add new latest update
@app.route('/api/add-latest-update', methods=['POST'])
def add_latest_update():
    try:
        data = request.get_json()
        date = data.get('date')
        news = data.get('news')
        link = data.get('link', '')
        
        if not date or not news:
            return jsonify({'success': False, 'message': 'Date and news are required'}), 400
        
        conn = get_db_connection()
        conn.execute('INSERT INTO latest_updates (date, news, link) VALUES (?, ?, ?)',
                     (date, news, link))
        conn.commit()
        
        # Get the newly inserted record
        new_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        new_update = conn.execute('SELECT * FROM latest_updates WHERE id = ?', (new_id,)).fetchone()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Update added successfully', 'data': dict(new_update)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Delete latest update
@app.route('/api/delete-latest-update/<int:id>', methods=['DELETE'])
def delete_latest_update(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM latest_updates WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Update deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== SYLLABUS ROUTES =====

# Get all syllabus records
@app.route('/api/syllabus', methods=['GET'])
def get_syllabus():
    try:
        conn = get_db_connection()
        syllabus = conn.execute('SELECT * FROM syllabus ORDER BY date DESC').fetchall()
        conn.close()
        
        syllabus_list = [dict(row) for row in syllabus]
        return jsonify({'success': True, 'data': syllabus_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Add new syllabus
@app.route('/api/add-syllabus', methods=['POST'])
def add_syllabus():
    try:
        data = request.get_json()
        department = data.get('department')
        sem = data.get('sem')
        link = data.get('link')
        date = data.get('date')
        
        if not department or not sem or not link:
            return jsonify({'success': False, 'message': 'Department, semester, and link are required'}), 400
        
        conn = get_db_connection()
        conn.execute('INSERT INTO syllabus (department, sem, link, date) VALUES (?, ?, ?, ?)',
                     (department, sem, link, date))
        conn.commit()
        
        # Get the newly inserted record
        new_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        new_syllabus = conn.execute('SELECT * FROM syllabus WHERE id = ?', (new_id,)).fetchone()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Syllabus added successfully', 'data': dict(new_syllabus)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Delete syllabus
@app.route('/api/delete-syllabus/<int:id>', methods=['DELETE'])
def delete_syllabus(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM syllabus WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Syllabus deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ===== TIMETABLE ROUTES =====

# Get all timetable records
@app.route('/api/timetable', methods=['GET'])
def get_timetable():
    try:
        conn = get_db_connection()
        timetable = conn.execute('SELECT * FROM timetable ORDER BY date DESC').fetchall()
        conn.close()
        
        timetable_list = [dict(row) for row in timetable]
        return jsonify({'success': True, 'data': timetable_list})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Add new timetable
@app.route('/api/add-timetable', methods=['POST'])
def add_timetable():
    try:
        data = request.get_json()
        department = data.get('department')
        sem = data.get('sem')
        link = data.get('link')
        date = data.get('date')
        
        if not department or not sem or not link:
            return jsonify({'success': False, 'message': 'Department, semester, and link are required'}), 400
        
        conn = get_db_connection()
        conn.execute('INSERT INTO timetable (department, sem, link, date) VALUES (?, ?, ?, ?)',
                     (department, sem, link, date))
        conn.commit()
        
        # Get the newly inserted record
        new_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        new_timetable = conn.execute('SELECT * FROM timetable WHERE id = ?', (new_id,)).fetchone()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Timetable added successfully', 'data': dict(new_timetable)})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Delete timetable
@app.route('/api/delete-timetable/<int:id>', methods=['DELETE'])
def delete_timetable(id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM timetable WHERE id = ?', (id,))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Timetable deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# Run Flask app
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)