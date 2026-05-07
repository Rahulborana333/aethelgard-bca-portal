from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from app.extensions import db
from app.models import User, Task, Notification
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
from app.utils import current_user

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@auth_bp.route('/register', methods=['POST'])
def api_register():
    data = request.get_json() or {}
    student_id = data.get('student_id', '').strip()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    if not all([student_id, name, email, password]):
        return jsonify({'error': 'All fields are required'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    if User.query.filter_by(student_id=student_id).first():
        return jsonify({'error': 'Student ID already registered'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already registered'}), 409

    user = User(student_id=student_id, name=name, email=email,
                semester=int(data.get('semester', 6)),
                password_hash=generate_password_hash(password))
    db.session.add(user)
    db.session.flush()

    # Seed default tasks
    now = datetime.now()
    seed_tasks = [
        Task(user_id=user.id, title='Mini Project: Library Management System',
             subject='DBMS', priority='high', due_date=now + timedelta(days=1),
             description='Build LMS with ER diagrams, normalization & SQL queries.'),
        Task(user_id=user.id, title='Responsive Portfolio Website',
             subject='Web Technologies', priority='medium', due_date=now + timedelta(days=4),
             description='Create portfolio using HTML, CSS, JavaScript.'),
        Task(user_id=user.id, title='Implement BST Operations',
             subject='DSA', priority='medium', due_date=now + timedelta(days=7),
             description='Insert, delete, traversal operations in C++.'),
        Task(user_id=user.id, title='SRS Document for Student Portal',
             subject='Software Engineering', priority='high', due_date=now + timedelta(days=2),
             description='Software Requirements Specification document.'),
    ]
    seed_notifs = [
        Notification(user_id=user.id, title='Welcome to Aethelgard!',
                     message='Your full-stack student portal is live. Built with Python Flask & SQLite.',
                     type='success'),
        Notification(user_id=user.id, title='Assignment Due Tomorrow',
                     message='DBMS Mini Project is due tomorrow. Submit before the deadline!',
                     type='warning'),
        Notification(user_id=user.id, title='Exam Schedule Published',
                     message='Semester VI examination timetable is now available. Check schedule page.',
                     type='info'),
    ]
    for t in seed_tasks:
        db.session.add(t)
    for n in seed_notifs:
        db.session.add(n)
    db.session.commit()

    access_token = create_access_token(identity=str(user.id))
    resp = jsonify({'success': True, 'name': user.name})
    set_access_cookies(resp, access_token)
    return resp, 201


@auth_bp.route('/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    student_id = data.get('student_id', '').strip()
    password = data.get('password', '')

    if not student_id or not password:
        return jsonify({'error': 'Student ID and password are required'}), 400

    user = User.query.filter_by(student_id=student_id).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid Student ID or password'}), 401

    access_token = create_access_token(identity=str(user.id))
    resp = jsonify({'success': True, 'name': user.name, 'role': getattr(user, 'role', 'student')})
    set_access_cookies(resp, access_token)
    return resp


@auth_bp.route('/logout', methods=['POST'])
def api_logout():
    resp = jsonify({'success': True})
    unset_jwt_cookies(resp)
    return resp


@auth_bp.route('/me')
def api_me():
    user = current_user()
    if not user:
        return jsonify({'authenticated': False}), 401
    return jsonify({'authenticated': True, **user.to_dict()})
