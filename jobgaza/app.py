import sqlite3
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24).hex())

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/jobs')
def jobs():
    search_query = request.args.get('search', '')
    job_type = request.args.get('type', '')
    company_id = request.args.get('company_id', '')
    
    conn = get_db_connection()
    query = "SELECT id, title, company_name, description, requirements, job_type FROM jobs WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    if job_type:
        query += " AND job_type = ?"
        params.append(job_type)
    if company_id:
        query += " AND user_id = ?"
        params.append(company_id)
        
    query += " ORDER BY id DESC"
    jobs_list = conn.execute(query, params).fetchall()
    conn.close()
    return render_template('jobs.html', jobs=jobs_list)

@app.route('/companies')
def companies():
    conn = get_db_connection()
    companies_list = conn.execute("SELECT id, name FROM users WHERE role = 'employer'").fetchall()
    conn.close()
    return render_template('companies.html', companies=companies_list)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['user_role'] = user['role']
            
            flash(f'مرحباً بك مجدداً، {user["name"]}!', 'success')
            
            # التوجيه الذكي والصارم حسب الصلاحية والمشفر في قاعدة البيانات
            if user['role'] == 'seeker':
                return redirect(url_for('seeker_dashboard'))
            elif user['role'] == 'employer':
                return redirect(url_for('employer_dashboard'))
            elif user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('البريد الإلكتروني أو كلمة المرور غير صحيحة!', 'danger')
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        conn = get_db_connection()
        try:
            hashed_password = generate_password_hash(password)
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", 
                           (name, email, hashed_password, role))
            user_id = cursor.lastrowid
            
            if role == 'seeker':
                cursor.execute("INSERT INTO profiles (user_id) VALUES (?)", (user_id,))
                
            conn.commit()
            flash('تم إنشاء حسابك بنجاح! يمكنك الآن تسجيل الدخول.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('هذا البريد الإلكتروني مستخدم بالفعل!', 'danger')
            return redirect(url_for('register'))
        finally:
            conn.close()
            
    return render_template('register.html')

@app.route('/dashboard/seeker', methods=['GET', 'POST'])
def seeker_dashboard():
    if 'user_id' not in session or session['user_role'] != 'seeker':
        flash('يرجى تسجيل الدخول أولاً كباحث عن عمل!', 'danger')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    
    if request.method == 'POST':
        phone = request.form.get('phone')
        bio = request.form.get('bio')
        skills = request.form.get('skills')
        cv_link = request.form.get('cv_link')
        
        conn.execute("UPDATE profiles SET phone=?, bio=?, skills=?, cv_link=? WHERE user_id=?", 
                     (phone, bio, skills, cv_link, session['user_id']))
        conn.commit()
        flash('تم تحديث ملفك الشخصي وسيرتك الذاتية بنجاح!', 'success')
        return redirect(url_for('seeker_dashboard'))
        
    profile = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (session['user_id'],)).fetchone()
    applications = conn.execute('''
        SELECT a.status, a.applied_at, j.title, j.company_name 
        FROM applications a 
        JOIN jobs j ON a.job_id = j.id 
        WHERE a.seeker_id = ? ORDER BY a.id DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('seeker_dashboard.html', profile=profile, applications=applications)

@app.route('/dashboard/employer')
def employer_dashboard():
    if 'user_id' not in session or session['user_role'] != 'employer':
        flash('يرجى تسجيل الدخول أولاً كصاحب عمل!', 'danger')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    my_jobs = conn.execute("SELECT * FROM jobs WHERE user_id = ? ORDER BY id DESC", (session['user_id'],)).fetchall()
    
    applicants = conn.execute('''
        SELECT a.id as app_id, a.applicant_name, a.applicant_email, a.cv_link, a.cover_letter, a.status, j.title as job_title 
        FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE j.user_id = ? ORDER BY a.id DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template('employer_dashboard.html', jobs=my_jobs, applicants=applicants)

@app.route('/create-job', methods=['GET', 'POST'])
def create_job():
    if 'user_id' not in session or session['user_role'] != 'employer':
        flash('هذه الصلاحية خاصة بحسابات الشركات فقط لنشر الوظائف!', 'danger')
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        company_name = session['user_name']
        job_type = request.form.get('job_type')
        description = request.form.get('description')
        requirements = request.form.get('requirements')
        
        conn = get_db_connection()
        conn.execute("INSERT INTO jobs (user_id, title, company_name, job_type, description, requirements) VALUES (?, ?, ?, ?, ?, ?)",
                     (session['user_id'], title, company_name, job_type, description, requirements))
        conn.commit()
        conn.close()
        flash('تم نشر الوظيفة الشاغرة بنجاح وهي متاحة للتقديم الآن!', 'success')
        return redirect(url_for('employer_dashboard'))
        
    return render_template('create-job.html')

@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply(job_id):
    if 'user_id' not in session or session['user_role'] != 'seeker':
        flash('يجب تسجيل الدخول كباحث عن عمل للتمكن من التقديم على الوظائف!', 'danger')
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()

    if not job:
        conn.close()
        flash('الوظيفة المطلوبة غير موجودة أو تم حذفها!', 'danger')
        return redirect(url_for('jobs'))

    if request.method == 'POST':
        applicant_name = request.form.get('name')
        applicant_email = request.form.get('email')
        cv_link = request.form.get('cv_link')
        cover_letter = request.form.get('cover_letter')
        
        existing = conn.execute("SELECT id FROM applications WHERE job_id = ? AND seeker_id = ?", (job_id, session['user_id'])).fetchone()
        if existing:
            flash('لقد قمت بالتقديم على هذه الوظيفة مسبقاً! تابع حالة طلبك من لوحة التحكم.', 'warning')
            conn.close()
            return redirect(url_for('jobs'))
            
        conn.execute('''
            INSERT INTO applications (job_id, seeker_id, applicant_name, applicant_email, cv_link, cover_letter) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (job_id, session['user_id'], applicant_name, applicant_email, cv_link, cover_letter))
        conn.commit()
        conn.close()
        flash('تم إرسال طلب توظيفك بنجاح وحفظ بياناتك في قاعدة البيانات!', 'success')
        return redirect(url_for('seeker_dashboard'))
        
    profile = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('apply.html', job=job, profile=profile)

@app.route('/delete-job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    if 'user_id' not in session or session['user_role'] != 'employer':
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    conn.execute("DELETE FROM jobs WHERE id = ? AND user_id = ?", (job_id, session['user_id']))
    conn.commit()
    conn.close()
    flash('تم حذف الإعلان الوظيفي وجميع طلبات التقديم المرتبطة به بنجاح.', 'info')
    return redirect(url_for('employer_dashboard'))

@app.route('/update-status/<int:app_id>/<string:status>', methods=['POST'])
def update_status(app_id, status):
    if 'user_id' not in session or session['user_role'] != 'employer':
        return redirect(url_for('login'))

    # التحقق من أن القيمة ضمن الحالات المسموحة فقط
    allowed_statuses = ['قيد المراجعة', 'مقبول', 'مرفوض']
    if status not in allowed_statuses:
        flash('حالة غير صالحة!', 'danger')
        return redirect(url_for('employer_dashboard'))

    conn = get_db_connection()
    # التحقق أن الطلب يتبع فعلاً لوظيفة تخص صاحب العمل المسجل دخوله حالياً
    owned = conn.execute('''
        SELECT a.id FROM applications a
        JOIN jobs j ON a.job_id = j.id
        WHERE a.id = ? AND j.user_id = ?
    ''', (app_id, session['user_id'])).fetchone()

    if not owned:
        conn.close()
        flash('غير مصرح لك بتعديل هذا الطلب!', 'danger')
        return redirect(url_for('employer_dashboard'))

    conn.execute("UPDATE applications SET status = ? WHERE id = ?", (status, app_id))
    conn.commit()
    conn.close()
    flash(f'تم تحديث حالة طلب المتقدم إلى ({status}) بنجاح.', 'success')
    return redirect(url_for('employer_dashboard'))

@app.route('/dashboard/admin')
def admin_dashboard():
    if 'user_id' not in session or session['user_role'] != 'admin':
        flash('صلاحية مرفوضة! تحتاج لحساب مدير نظام لتصفح هذه الصفحة.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    all_users = conn.execute("SELECT id, name, email, role FROM users WHERE role != 'admin'").fetchall()
    all_jobs = conn.execute("SELECT id, title, company_name FROM jobs").fetchall()
    conn.close()
    return render_template('admin_dashboard.html', users=all_users, jobs=all_jobs)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        flash('شكراً لتواصلك معنا! تم إرسال رسالتك بنجاح وسيرد الفريق عليك قريباً.', 'success')
        return redirect(url_for('index'))
    return render_template('contact.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('تم تسجيل الخروج، نراك قريباً!', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug_mode, port=5000)