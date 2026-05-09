from flask import Flask
from .extensions import db, socketio, mail, jwt
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from apscheduler.schedulers.background import BackgroundScheduler


def send_due_reminders(app):
    with app.app_context():
        # Using print to simulate sending email to console as requested
        print("[Scheduler] Running background task: Checking for upcoming deadlines...")


import os

def create_app():
    app = Flask(__name__)
    
    # Ensure instance folder exists for SQLite on production
    os.makedirs(app.instance_path, exist_ok=True)
    
    app.secret_key = 'aethelgard-bca-secret-2025-xK9mP2qR'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aethelgard.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['MAIL_SERVER'] = 'localhost'
    app.config['MAIL_PORT'] = 25

    app.config['JWT_SECRET_KEY'] = 'jwt-super-secret-aethelgard'
    app.config['JWT_TOKEN_LOCATION'] = ['cookies']
    app.config['JWT_COOKIE_SECURE'] = False  # For dev only, True in prod over https
    app.config['JWT_COOKIE_CSRF_PROTECT'] = False  # Simplify for this project

    db.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    mail.init_app(app)
    jwt.init_app(app)

    scheduler = BackgroundScheduler()
    scheduler.add_job(func=send_due_reminders, args=[app], trigger="interval", seconds=3600)
    if not scheduler.running:
        scheduler.start()

    # Register blueprints
    from .routes.views import views_bp
    from .routes.auth import auth_bp
    from .routes.api import api_bp
    from .routes.admin import admin_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(admin_bp)

    # Socket.io Events for Study Room
    @socketio.on('join_study_room')
    def handle_join(data):
        name = data.get('name', 'Anonymous')
        print(f"[SocketIO] User joined study room: {name}")
        socketio.emit('study_room_announcement', {'msg': f"{name} has joined the study session."})

    @socketio.on('send_study_msg')
    def handle_study_msg(data):
        name = data.get('name', 'Anonymous')
        msg = data.get('msg', '')
        print(f"[SocketIO] Message from {name}: {msg}")
        socketio.emit('receive_study_msg', {
            'name': name,
            'msg': msg,
            'time': datetime.now().strftime('%H:%M')
        })

    return app


def init_db(app):
    with app.app_context():
        db.create_all()
        # Lightweight migration: add is_active column if missing
        try:
            db.session.execute(db.text("SELECT is_active FROM user LIMIT 1"))
        except Exception:
            db.session.rollback()
            db.session.execute(db.text("ALTER TABLE user ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            db.session.commit()
        from .models import User, Task, Notification, SamplePaper
        if not User.query.first():
            now = datetime.now()
            demo = User(student_id='BCA2025001', name='Rahul Sharma',
                        email='rahul@aethelgard.edu',
                        password_hash=generate_password_hash('demo123'),
                        semester=6, branch='BCA', cgpa=3.92, attendance=87, rank=3, role='student')
            db.session.add(demo)

            admin = User(student_id='ADMIN', name='Faculty Admin',
                         email='admin@aethelgard.edu',
                         password_hash=generate_password_hash('admin123'),
                         role='admin')
            db.session.add(admin)
            db.session.flush()

            tasks = [
                Task(user_id=demo.id, title='Mini Project: Library Management System',
                     subject='DBMS', priority='high', due_date=now + timedelta(days=1),
                     description='Build LMS with ER diagrams, normalization & SQL queries.'),
                Task(user_id=demo.id, title='Responsive Portfolio Website',
                     subject='Web Technologies', priority='medium', due_date=now + timedelta(days=4),
                     description='Create portfolio using HTML, CSS, JavaScript with responsive design.'),
                Task(user_id=demo.id, title='Implement BST Operations',
                     subject='DSA', priority='medium', due_date=now + timedelta(days=7),
                     description='Insert, delete, inorder, preorder traversal in C++.'),
                Task(user_id=demo.id, title='Network Topology Report',
                     subject='Computer Networks', priority='low', due_date=now + timedelta(days=10),
                     description='Compare star, bus, ring, mesh topologies.'),
                Task(user_id=demo.id, title='SRS Document for Student Portal',
                     subject='Software Engineering', priority='high', due_date=now + timedelta(days=2),
                     description='Complete Software Requirements Specification document.'),
                Task(user_id=demo.id, title='SQL Joins & Subqueries Assignment',
                     subject='DBMS', priority='low', due_date=now - timedelta(days=1),
                     description='Completed practice set on SQL joins.', done=True),
            ]
            notifs = [
                Notification(user_id=demo.id, title='Welcome to Aethelgard Portal!',
                             message='Full-stack portal is live. Backend: Python Flask | Database: SQLite | Auth: Werkzeug.',
                             type='success'),
                Notification(user_id=demo.id, title='Assignment Due Tomorrow',
                             message='DBMS Mini Project is due tomorrow. Submit before 11:59 PM!',
                             type='warning'),
                Notification(user_id=demo.id, title='Semester VI Exam Schedule',
                             message='Examination timetable published. Theory exams begin 3rd week of June.',
                             type='info'),
                Notification(user_id=demo.id, title='Attendance Alert',
                             message='Computer Networks attendance is 78%. Minimum required is 75%. Attend classes.',
                             type='danger'),
            ]
            for t in tasks:
                db.session.add(t)
            for n in notifs:
                db.session.add(n)
            db.session.commit()

            # Seed Sample Papers
            if not SamplePaper.query.first():
                papers = [
                    SamplePaper(title='Previous Year Final Paper 2024', subject='Software Engineering', file_path='se_2024.pdf', type='paper'),
                    SamplePaper(title='Important Questions for Midterms', subject='DBMS', file_path='dbms_important.pdf', type='important_qs')
                ]
                for p in papers:
                    db.session.add(p)
                db.session.commit()

            print("✅  Demo account seeded  →  ID: BCA2025001  |  Password: demo123")
