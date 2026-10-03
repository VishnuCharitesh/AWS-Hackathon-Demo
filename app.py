import os
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'opensearch-eval-portal-secret-key-2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///opensearch_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'student', 'evaluator', 'admin'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    assignments = db.relationship('Assignment', backref='creator', lazy=True, cascade='all, delete-orphan')
    submissions = db.relationship('Submission', backref='student', lazy=True, cascade='all, delete-orphan')
    evaluations = db.relationship('Evaluation', backref='evaluator', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    total_marks = db.Column(db.Float, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    submissions = db.relationship('Submission', backref='assignment', lazy=True, cascade='all, delete-orphan')

class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    answer_text = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='Submitted')  # 'Submitted', 'Evaluated'

    evaluation = db.relationship('Evaluation', backref='submission', uselist=False, cascade='all, delete-orphan')

class Evaluation(db.Model):
    __tablename__ = 'evaluations'
    id = db.Column(db.Integer, primary_key=True)
    submission_id = db.Column(db.Integer, db.ForeignKey('submissions.id'), unique=True, nullable=False)
    evaluator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    feedback = db.Column(db.Text, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    evaluated_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    username = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=False)
    ip_address = db.Column(db.String(50), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# ---------------------------------------------------------------------------
# Real-time Activity Logging Helper
# ---------------------------------------------------------------------------

def log_activity(action, details, username=None, role=None, user_id=None):
    """Log real-time user actions to the audit database."""
    if not username:
        username = session.get('username', 'System/Guest')
    if not role:
        role = session.get('user_role', 'guest')
    if not user_id:
        user_id = session.get('user_id')

    ip_addr = request.remote_addr if request else '127.0.0.1'

    try:
        log_entry = AuditLog(
            user_id=user_id,
            username=username,
            role=role,
            action=action,
            details=details,
            ip_address=ip_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Audit log error: {e}")

# ---------------------------------------------------------------------------
# Auth Decorators & Context Processors
# ---------------------------------------------------------------------------

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('user_role') not in roles:
                flash('Access denied. You do not have permission to view this page.', 'danger')
                role = session.get('user_role')
                if role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif role == 'evaluator':
                    return redirect(url_for('evaluator_dashboard'))
                elif role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.context_processor
def inject_user():
    current_user = None
    if 'user_id' in session:
        current_user = db.session.get(User, session['user_id'])
    return dict(current_user=current_user)

# ---------------------------------------------------------------------------
# Clean Initial User Seeder (No Mock Assignments/Submissions)
# ---------------------------------------------------------------------------

def init_db():
    with app.app_context():
        db.create_all()
        if User.query.count() == 0:
            print("Initializing default portal user accounts...")
            admin = User(username='admin', email='admin@opensearch.org', role='admin')
            admin.set_password('admin123')

            evaluator1 = User(username='evaluator1', email='evaluator1@opensearch.org', role='evaluator')
            evaluator1.set_password('eval123')

            student1 = User(username='student1', email='student1@example.com', role='student')
            student1.set_password('stud123')

            db.session.add_all([admin, evaluator1, student1])
            db.session.commit()

            log_activity('System Init', 'Initialized database default accounts (admin, evaluator1, student1)', username='System', role='system', user_id=admin.id)
            print("Database ready with 0 mock assignments/submissions. All data will be generated by real-time user inputs.")

# ---------------------------------------------------------------------------
# General & Auth Routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('user_role')
        if role == 'student':
            return redirect(url_for('student_dashboard'))
        elif role == 'evaluator':
            return redirect(url_for('evaluator_dashboard'))
        elif role == 'admin':
            return redirect(url_for('admin_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            
            log_activity('User Login', f'User {user.username} ({user.role}) successfully logged in', username=user.username, role=user.role, user_id=user.id)
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('index'))
        else:
            log_activity('Failed Login Attempt', f'Failed login attempt for username "{username}"', username=username, role='guest')
            flash('Invalid username or password. Please try again.', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        role = request.form.get('role', 'student').strip()

        if not username or not email or not password:
            flash('Please fill out all required fields.', 'danger')
            return render_template('register.html')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')

        if role not in ['student', 'evaluator', 'admin']:
            role = 'student'

        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already registered.', 'danger')
            return render_template('register.html')

        new_user = User(username=username, email=email, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        log_activity('User Registration', f'New user registered: {username} ({role}) with email {email}', username=username, role=role, user_id=new_user.id)
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    username = session.get('username', 'User')
    role = session.get('user_role', 'user')
    user_id = session.get('user_id')

    log_activity('User Logout', f'{username} logged out', username=username, role=role, user_id=user_id)
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ---------------------------------------------------------------------------
# Student Routes
# ---------------------------------------------------------------------------

@app.route('/student/dashboard')
@role_required('student')
def student_dashboard():
    student_id = session['user_id']
    total_assignments = Assignment.query.count()
    student_submissions = Submission.query.filter_by(student_id=student_id).all()
    submitted_count = len(student_submissions)
    evaluated_count = sum(1 for s in student_submissions if s.status == 'Evaluated')
    
    recent_assignments = Assignment.query.order_by(Assignment.created_at.desc()).limit(10).all()
    sub_map = {s.assignment_id: s for s in student_submissions}

    return render_template('student/dashboard.html',
                           total_assignments=total_assignments,
                           submitted_count=submitted_count,
                           evaluated_count=evaluated_count,
                           recent_assignments=recent_assignments,
                           sub_map=sub_map,
                           now=datetime.utcnow())

@app.route('/student/assignments')
@role_required('student')
def student_assignments():
    student_id = session['user_id']
    assignments = Assignment.query.order_by(Assignment.deadline.asc()).all()
    student_submissions = Submission.query.filter_by(student_id=student_id).all()
    sub_map = {s.assignment_id: s for s in student_submissions}
    return render_template('student/assignments.html', assignments=assignments, sub_map=sub_map, now=datetime.utcnow())

@app.route('/student/submit/<int:id>', methods=['GET', 'POST'])
@role_required('student')
def student_submit(id):
    assignment = Assignment.query.get_or_404(id)
    student_id = session['user_id']
    existing_sub = Submission.query.filter_by(assignment_id=id, student_id=student_id).first()

    if request.method == 'POST':
        answer_text = request.form.get('answer_text', '').strip()
        if not answer_text:
            flash('Submission answer content cannot be empty.', 'danger')
            return render_template('student/submit.html', assignment=assignment, submission=existing_sub)

        if existing_sub:
            if existing_sub.status == 'Evaluated':
                flash('This assignment has already been evaluated and cannot be modified.', 'warning')
                return redirect(url_for('student_results'))
            existing_sub.answer_text = answer_text
            existing_sub.submitted_at = datetime.utcnow()
            db.session.commit()
            log_activity('Submission Updated', f'Updated submission for assignment "{assignment.title}"')
            flash('Your submission has been updated successfully!', 'success')
        else:
            new_sub = Submission(
                assignment_id=id,
                student_id=student_id,
                answer_text=answer_text,
                status='Submitted'
            )
            db.session.add(new_sub)
            db.session.commit()
            log_activity('Submission Created', f'Submitted answer for assignment "{assignment.title}" (ID: {assignment.id})')
            flash('Assignment submitted successfully!', 'success')

        return redirect(url_for('student_results'))

    return render_template('student/submit.html', assignment=assignment, submission=existing_sub, now=datetime.utcnow())

@app.route('/student/results')
@role_required('student')
def student_results():
    student_id = session['user_id']
    submissions = Submission.query.filter_by(student_id=student_id).order_by(Submission.submitted_at.desc()).all()
    return render_template('student/results.html', submissions=submissions)

# ---------------------------------------------------------------------------
# Evaluator Routes
# ---------------------------------------------------------------------------

OPENSEARCH_TOPICS = [
    'OpenSearch Basics',
    'Indexing',
    'Query DSL',
    'Match Query',
    'Term Query',
    'Aggregations',
    'Mapping',
    'OpenSearch Dashboards',
    'Security & Access Control',
    'Performance & Tuning'
]

@app.route('/evaluator/dashboard')
@role_required('evaluator')
def evaluator_dashboard():
    evaluator_id = session['user_id']
    total_assignments = Assignment.query.filter_by(created_by_id=evaluator_id).count()
    all_submissions = Submission.query.join(Assignment).filter(Assignment.created_by_id == evaluator_id).all()
    pending_evals = sum(1 for s in all_submissions if s.status == 'Submitted')
    completed_evals = sum(1 for s in all_submissions if s.status == 'Evaluated')
    
    recent_submissions = Submission.query.join(Assignment)\
        .filter(Assignment.created_by_id == evaluator_id)\
        .order_by(Submission.submitted_at.desc()).limit(5).all()

    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()

    return render_template('evaluator/dashboard.html',
                           total_assignments=total_assignments,
                           pending_evals=pending_evals,
                           completed_evals=completed_evals,
                           recent_submissions=recent_submissions,
                           recent_logs=recent_logs)

@app.route('/evaluator/assignments')
@role_required('evaluator')
def evaluator_assignments():
    evaluator_id = session['user_id']
    assignments = Assignment.query.filter_by(created_by_id=evaluator_id).order_by(Assignment.created_at.desc()).all()
    return render_template('evaluator/assignments.html', assignments=assignments)

@app.route('/evaluator/create-assignment', methods=['GET', 'POST'])
@role_required('evaluator')
def create_assignment():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        topic = request.form.get('topic', '').strip()
        instructions = request.form.get('instructions', '').strip()
        total_marks_str = request.form.get('total_marks', '').strip()
        deadline_str = request.form.get('deadline', '').strip()

        if not title or not description or not topic or not instructions or not total_marks_str or not deadline_str:
            flash('All fields are required.', 'danger')
            return render_template('evaluator/create_assignment.html', topics=OPENSEARCH_TOPICS)

        try:
            total_marks = float(total_marks_str)
            if total_marks <= 0:
                flash('Total marks must be greater than zero.', 'danger')
                return render_template('evaluator/create_assignment.html', topics=OPENSEARCH_TOPICS)
        except ValueError:
            flash('Invalid total marks value.', 'danger')
            return render_template('evaluator/create_assignment.html', topics=OPENSEARCH_TOPICS)

        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid deadline date format.', 'danger')
            return render_template('evaluator/create_assignment.html', topics=OPENSEARCH_TOPICS)

        new_assignment = Assignment(
            title=title,
            description=description,
            topic=topic,
            instructions=instructions,
            total_marks=total_marks,
            deadline=deadline,
            created_by_id=session['user_id']
        )
        db.session.add(new_assignment)
        db.session.commit()

        log_activity('Assignment Created', f'Created OpenSearch assignment "{title}" under topic "{topic}" (Marks: {total_marks})')
        flash('Assignment created and published successfully!', 'success')
        return redirect(url_for('evaluator_assignments'))

    return render_template('evaluator/create_assignment.html', topics=OPENSEARCH_TOPICS)

@app.route('/evaluator/edit-assignment/<int:id>', methods=['GET', 'POST'])
@role_required('evaluator')
def edit_assignment(id):
    assignment = Assignment.query.get_or_404(id)
    if assignment.created_by_id != session['user_id'] and session.get('user_role') != 'admin':
        flash('You can only edit assignments you created.', 'danger')
        return redirect(url_for('evaluator_assignments'))

    if request.method == 'POST':
        assignment.title = request.form.get('title', '').strip()
        assignment.description = request.form.get('description', '').strip()
        assignment.topic = request.form.get('topic', '').strip()
        assignment.instructions = request.form.get('instructions', '').strip()
        total_marks_str = request.form.get('total_marks', '').strip()
        deadline_str = request.form.get('deadline', '').strip()

        try:
            assignment.total_marks = float(total_marks_str)
        except ValueError:
            flash('Invalid total marks value.', 'danger')
            return render_template('evaluator/edit_assignment.html', assignment=assignment, topics=OPENSEARCH_TOPICS)

        try:
            assignment.deadline = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
        except ValueError:
            flash('Invalid deadline format.', 'danger')
            return render_template('evaluator/edit_assignment.html', assignment=assignment, topics=OPENSEARCH_TOPICS)

        db.session.commit()
        log_activity('Assignment Updated', f'Updated assignment "{assignment.title}" (ID: {assignment.id})')
        flash('Assignment updated successfully!', 'success')
        return redirect(url_for('evaluator_assignments'))

    return render_template('evaluator/edit_assignment.html', assignment=assignment, topics=OPENSEARCH_TOPICS)

@app.route('/evaluator/delete-assignment/<int:id>', methods=['POST'])
@role_required('evaluator')
def delete_assignment(id):
    assignment = Assignment.query.get_or_404(id)
    if assignment.created_by_id != session['user_id'] and session.get('user_role') != 'admin':
        flash('You can only delete assignments you created.', 'danger')
        return redirect(url_for('evaluator_assignments'))

    title = assignment.title
    db.session.delete(assignment)
    db.session.commit()
    log_activity('Assignment Deleted', f'Deleted assignment "{title}" (ID: {id})')
    flash('Assignment deleted successfully.', 'info')
    return redirect(url_for('evaluator_assignments'))

@app.route('/evaluator/submissions')
@role_required('evaluator')
def evaluator_submissions():
    evaluator_id = session['user_id']
    submissions = Submission.query.join(Assignment)\
        .filter(Assignment.created_by_id == evaluator_id)\
        .order_by(Submission.submitted_at.desc()).all()
    return render_template('evaluator/submissions.html', submissions=submissions)

@app.route('/evaluator/evaluate/<int:id>', methods=['GET', 'POST'])
@role_required('evaluator')
def evaluate_submission(id):
    submission = Submission.query.get_or_404(id)
    evaluator_id = session['user_id']
    assignment = submission.assignment

    if assignment.created_by_id != evaluator_id and session.get('user_role') != 'admin':
        flash('You can only evaluate submissions for assignments you created.', 'danger')
        return redirect(url_for('evaluator_submissions'))

    existing_eval = submission.evaluation

    if request.method == 'POST':
        score_str = request.form.get('score', '').strip()
        feedback = request.form.get('feedback', '').strip()

        if not score_str or not feedback:
            flash('Score and feedback are required.', 'danger')
            return render_template('evaluator/evaluate.html', submission=submission, evaluation=existing_eval)

        try:
            score = float(score_str)
        except ValueError:
            flash('Score must be a valid number.', 'danger')
            return render_template('evaluator/evaluate.html', submission=submission, evaluation=existing_eval)

        if score < 0:
            flash('Score cannot be negative.', 'danger')
            return render_template('evaluator/evaluate.html', submission=submission, evaluation=existing_eval)

        if score > assignment.total_marks:
            flash(f'Score ({score}) cannot exceed maximum total marks ({assignment.total_marks}).', 'danger')
            return render_template('evaluator/evaluate.html', submission=submission, evaluation=existing_eval)

        percentage = round((score / assignment.total_marks) * 100.0, 2)

        if existing_eval:
            existing_eval.score = score
            existing_eval.feedback = feedback
            existing_eval.percentage = percentage
            existing_eval.evaluator_id = evaluator_id
            existing_eval.evaluated_at = datetime.utcnow()
        else:
            new_eval = Evaluation(
                submission_id=submission.id,
                evaluator_id=evaluator_id,
                score=score,
                feedback=feedback,
                percentage=percentage
            )
            db.session.add(new_eval)

        submission.status = 'Evaluated'
        db.session.commit()

        log_activity('Submission Evaluated', f'Graded submission for student "{submission.student.username}" on assignment "{assignment.title}" (Score: {score}/{assignment.total_marks}, {percentage}%)')
        flash('Submission evaluated successfully!', 'success')
        return redirect(url_for('evaluator_submissions'))

    return render_template('evaluator/evaluate.html', submission=submission, evaluation=existing_eval)

# ---------------------------------------------------------------------------
# Admin Routes
# ---------------------------------------------------------------------------

@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    total_users = User.query.count()
    student_count = User.query.filter_by(role='student').count()
    evaluator_count = User.query.filter_by(role='evaluator').count()
    total_assignments = Assignment.query.count()
    total_submissions = Submission.query.count()
    evaluated_submissions = Submission.query.filter_by(status='Evaluated').count()

    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()

    return render_template('admin/dashboard.html',
                           total_users=total_users,
                           student_count=student_count,
                           evaluator_count=evaluator_count,
                           total_assignments=total_assignments,
                           total_submissions=total_submissions,
                           evaluated_submissions=evaluated_submissions,
                           recent_users=recent_users,
                           recent_logs=recent_logs)

@app.route('/admin/users')
@role_required('admin')
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/assignments')
@role_required('admin')
def admin_assignments():
    assignments = Assignment.query.order_by(Assignment.created_at.desc()).all()
    return render_template('admin/assignments.html', assignments=assignments)

@app.route('/admin/submissions')
@role_required('admin')
def admin_submissions():
    submissions = Submission.query.order_by(Submission.submitted_at.desc()).all()
    return render_template('admin/submissions.html', submissions=submissions)

@app.route('/admin/logs')
@role_required('admin')
def admin_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    return render_template('admin/logs.html', logs=logs)

# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
