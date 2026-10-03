import sqlite3
from werkzeug.security import generate_password_hash

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # تفعيل دعم المفاتيح الأجنبية (Foreign Keys) للربط بين الجداول
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # حذف الجداول القديمة لإعادة التأسيس النظيف
    cursor.execute('DROP TABLE IF EXISTS applications')
    cursor.execute('DROP TABLE IF EXISTS jobs')
    cursor.execute('DROP TABLE IF EXISTS profiles')
    cursor.execute('DROP TABLE IF EXISTS users')
    
    # 1. جدول المستخدمين (باحث، شركة، مدير)
    cursor.execute('''
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL -- 'seeker', 'employer', 'admin'
    )
    ''')
    
    # 2. جدول الملفات الشخصية للباحثين عن عمل
    cursor.execute('''
    CREATE TABLE profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        phone TEXT,
        bio TEXT,
        cv_link TEXT,
        skills TEXT,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')
    
    # 3. جدول الوظائف (مرتبط بمعرف الشركة الناشرة)
    cursor.execute('''
    CREATE TABLE jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL, -- معرف الشركة من جدول users
        title TEXT NOT NULL,
        company_name TEXT NOT NULL,
        job_type TEXT NOT NULL, -- 'full_time', 'part_time', 'remote', etc.
        description TEXT NOT NULL,
        requirements TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')
    
    # 4. جدول طلبات التقديم على الوظائف (يربط الباحث بالوظيفة مع الحالة)
    cursor.execute('''
    CREATE TABLE applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        seeker_id INTEGER NOT NULL, -- معرف الباحث عن عمل
        applicant_name TEXT NOT NULL,
        applicant_email TEXT NOT NULL,
        cv_link TEXT NOT NULL,
        cover_letter TEXT,
        status TEXT DEFAULT 'قيد المراجعة', -- 'قيد المراجعة', 'مقبول', 'مرفوض'
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs (id) ON DELETE CASCADE,
        FOREIGN KEY (seeker_id) REFERENCES users (id) ON DELETE CASCADE
    )
    ''')
    
    # ==================== حقن البيانات الافتراضية الذكية ====================
    
    # إضافة مستخدمين (شركات وباحثين عن عمل ومدير) - كلمات المرور مشفّرة
    users_data = [
        ('شركة تكنولوجيا النخبة', 'elite@example.com', generate_password_hash('123456'), 'employer'),
        ('منظمة الغد الدولية', 'alghad@example.com', generate_password_hash('123456'), 'employer'),
        ('أحمد محمد علي', 'ahmed@example.com', generate_password_hash('123456'), 'seeker'),
        ('مدير المنصة', 'admin@jobgaza.ps', generate_password_hash('admin123'), 'admin')
    ]
    cursor.executemany("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)", users_data)
    
    # إضافة ملف شخصي افتراضي لأحمد
    cursor.execute("INSERT INTO profiles (user_id, phone, bio, cv_link, skills) VALUES (3, '0599123456', 'مطور ويب طموح من غزة', 'https://drive.google.com/sample-cv', 'HTML, CSS, JavaScript, Python')")
    
    # إضافة وظائف افتراضية مرتبطة بالشركات (Elite معرفها 1، Alghad معرفها 2)
    jobs_data = [
        (1, 'مطور واجهات أمامية (Frontend)', 'شركة تكنولوجيا النخبة', 'full_time', 'مطلوب مطور واجهات متمكن من تحويل تصاميم Figma إلى أكواد تفاعلية.', 'خبرة سنة، إجادة جافا سكريبت'),
        (1, 'مهندس بيانات سحابية', 'شركة تكنولوجيا النخبة', 'remote', 'إدارة وتأمين قواعد البيانات السحابية الحساسة الخاصة بالشركات.', 'خبرة في SQL والسيرفرات'),
        (2, 'أخصائي دعم فني ميداني', 'منظمة الغد الدولية', 'part_time', 'متابعة وصيانة شبكات الاتصال الداخلية وحل المشاكل التقنية.', 'شهادة في تكنولوجيا المعلومات أو هندسة الحاسوب')
    ]
    cursor.executemany("INSERT INTO jobs (user_id, title, company_name, job_type, description, requirements) VALUES (?, ?, ?, ?, ?, ?)", jobs_data)
    
    conn.commit()
    conn.close()
    print("🎯 تم تحديث هيكل قاعدة البيانات وزرع البيانات المترابطة بنجاح!")

if __name__ == '__main__':
    init_db()