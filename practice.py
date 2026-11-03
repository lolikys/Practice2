from flask import Flask, render_template, request, redirect, url_for, flash, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'admin'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///Academi.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Промежуточная таблица для связи студентов и курсов
student_course = db.Table('student_course',
    db.Column('student_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')
    name = db.Column(db.String(100), nullable=False)
    courses = db.relationship('Course', secondary=student_course, backref='students')

    def has_password_set(self):
        return self.password_hash != 'unset' and self.password_hash is not None

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    duration = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def admin_required(f):
    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Доступ только для админов', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Вы вошли в систему!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль', 'error')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/admin/courses')
@admin_required
def admin_courses():
    courses = Course.query.all()
    return render_template('admin_courses.html', courses=courses)

@app.route('/admin/courses/add', methods=['GET', 'POST'])
@admin_required
def add_course_admin():
    if request.method == 'POST':
        title = request.form.get('title')
        duration = request.form.get('duration')
        description = request.form.get('description')

        new_course = Course(title=title, duration=duration, description=description)
        db.session.add(new_course)
        db.session.commit()

        flash('Курс успешно добавлен', 'success')
        return redirect(url_for('admin_courses'))

    return render_template('course_form.html', title='Добавить курс')

@app.route('/admin/courses/<int:course_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_course_admin(course_id):
    course = Course.query.get_or_404(course_id)

    if request.method == 'POST':
        course.title = request.form.get('title')
        course.duration = request.form.get('duration')
        course.description = request.form.get('description')

        db.session.commit()
        flash('Курс успешно обновлен', 'success')
        return redirect(url_for('admin_courses'))

    return render_template('course_form.html', title='Редактировать', course=course)

@app.route('/admin/courses/<int:course_id>/delete')
@admin_required
def delete_course_admin(course_id):
    course = Course.query.get_or_404(course_id)

    for student in course.students:
        student.courses.remove(course)

    db.session.delete(course)
    db.session.commit()

    flash('Курс успешно удален', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/courses/<int:course_id>/enroll', methods=['GET', 'POST'])
@admin_required
def enroll_student_to_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        flash('Курс не найден', 'error')
        return redirect(url_for('admin_courses'))

    if request.method == 'POST':
        student_id = request.form.get('student_id')
        student = db.session.get(User, student_id)

        if student:
            if student not in course.students:
                course.students.append(student)
                db.session.commit()
                flash(f'Студент {student.name} добавлен на курс {course.title}', 'success')
            else:
                flash('Студент уже записан на этот курс', 'warning')
        else:
            flash('Студент не найден', 'error')

        return redirect(url_for('course_students', course_id=course_id))

    all_students = db.session.query(User).filter_by(role='student').all()
    available_students = [s for s in all_students if s not in course.students]

    return render_template('enroll_student.html', course=course, students=available_students)

@app.route('/student/courses')
@login_required
def student_courses():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    if not current_user.has_password_set():
        flash('Пожалуйста, установите пароль', 'warning')
        return redirect(url_for('set_student_password'))

    return render_template('student_courses.html')

@app.route('/admin/students')
@admin_required
def students_list():
    students = User.query.filter_by(role='student').all()
    return render_template('students.html', students=students)

@app.route('/admin/students/add', methods=['GET', 'POST'])
@admin_required
def add_student_admin():
    if request.method == 'POST':
        username = request.form.get('username')
        name = request.form.get('name')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Пользователь с таким логином уже существует', 'error')
            return redirect(url_for('add_student_admin'))

        student = User(username=username, name=name, role='student', password_hash='')
        db.session.add(student)
        db.session.commit()

        flash(f'Студент {name} успешно создан', 'success')
        return redirect(url_for('students_list'))

    return render_template('add_student.html')

@app.route('/admin/students/<int:student_id>')
@admin_required
def student_profile_admin(student_id):
    student = User.query.get_or_404(student_id)
    return render_template('student_profile_admin.html', student=student)

@app.route('/admin/students/<int:student_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_student_admin(student_id):
    student = User.query.get_or_404(student_id)

    if request.method == 'POST':
        student.name = request.form.get('name')
        student.username = request.form.get('username')
        db.session.commit()
        flash('Данные студента обновлены', 'success')
        return redirect(url_for('students_list'))

    return render_template('edit_student.html', student=student)

@app.route('/admin/students/<int:student_id>/delete')
@admin_required
def delete_student_admin(student_id):
    student = User.query.get_or_404(student_id)

    for course in student.courses:
        course.students.remove(student)

    db.session.delete(student)
    db.session.commit()

    flash('Студент удален', 'success')
    return redirect(url_for('students_list'))

@app.route('/admin/students/<int:student_id>/set-password', methods=['GET', 'POST'])
@admin_required
def set_admin_student_password(student_id):
    student = db.session.get(User, student_id)
    if not student:
        flash('Студент не найден', 'error')
        return redirect(url_for('students_list'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Пароли не совпадают. Повторите ввод пароля', 'danger')
            return redirect(url_for('set_admin_student_password', student_id=student_id))

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов. Повторите ввод пароля', 'danger')
            return redirect(url_for('set_admin_student_password', student_id=student_id))

        student.set_password(password)
        db.session.commit()
        flash('Пароль успешно установлен', 'success')
        return redirect(url_for('students_list'))

    return render_template('set_password.html', student=student)

@app.route('/admin/courses/<int:course_id>/students')
@admin_required
def course_students(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        flash('Курс не найден', 'error')
        return redirect(url_for('admin_courses'))
    return render_template('course_students.html', course=course)

@app.route('/admin/students/<int:student_id>/courses')
@admin_required
def student_courses_admin(student_id):
    student = db.session.get(User, student_id)
    if not student:
        flash('Студент не найден', 'error')
        return redirect(url_for('students_list'))
    return render_template('student_courses_admin.html', student=student)

@app.route('/student/set-password', methods=['GET', 'POST'])
@login_required
def set_student_password():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    if request.method == 'POST':
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Пароли не совпадают. Повторите ввод пароля', 'danger')
            return redirect(url_for('set_student_password'))

        if len(password) < 6:
            flash('Пароль должен быть не менее 6 символов. Повторите ввод пароля', 'danger')
            return redirect(url_for('set_student_password'))

        current_user.set_password(password)
        db.session.commit()
        flash('Пароль успешно установлен', 'success')
        return redirect(url_for('student_dashboard'))

    return render_template('set_password.html', student=current_user)

@app.route('/student/dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    if not current_user.has_password_set():
        flash('Необходимо установить пароль', 'warning')
        return redirect(url_for('set_student_password'))

    return render_template('student_dashboard.html')

@app.route('/student/profile')
@login_required
def student_profile():
    if current_user.role != 'student':
        flash('Доступ запрещен', 'danger')
        return redirect(url_for('index'))

    if not current_user.has_password_set():
        flash('Пожалуйста, установите пароль для доступа к профилю', 'warning')
        return redirect(url_for('set_student_password'))

    return render_template('student_profile.html')

@app.before_request
def create_admin():
    db.create_all()
    if not User.query.filter_by(username='admin').first():
        admin = User(username='admin', role='admin', name='Администратор системы')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()

def validate_password(password):
    if len(password) < 6:
        return False
    return True

if __name__ == '__main__':
    app.run(debug=True)