"""
Seed demo students for Aethelgard BCA Portal.
Run: python3 seed_students.py
"""
from app import create_app
from app.extensions import db
from app.models import User, Notification, Task
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

app = create_app()

DEMO_STUDENTS = [
    # (student_id, name, email, password, semester, cgpa, attendance, rank)
    ('BCA2025001', 'Rahul Sharma',     'rahul@bca.edu',   'demo123', 6, 8.5,  87, 1),
    ('BCA2025002', 'Priya Verma',      'priya@bca.edu',   'demo123', 6, 9.1,  92, 2),
    ('BCA2025003', 'Arjun Mehta',      'arjun@bca.edu',   'demo123', 6, 7.8,  78, 3),
    ('BCA2025004', 'Sneha Patel',      'sneha@bca.edu',   'demo123', 6, 6.5,  65, 4),
    ('BCA2025005', 'Rohan Gupta',      'rohan@bca.edu',   'demo123', 5, 5.2,  55, 5),
    ('BCA2025006', 'Anjali Singh',     'anjali@bca.edu',  'demo123', 5, 9.4,  95, 6),
    ('BCA2025007', 'Vikram Nair',      'vikram@bca.edu',  'demo123', 5, 4.8,  48, 7),
    ('BCA2025008', 'Kavya Reddy',      'kavya@bca.edu',   'demo123', 4, 8.0,  82, 8),
    ('BCA2025009', 'Aditya Kumar',     'aditya@bca.edu',  'demo123', 4, 7.2,  70, 9),
    ('BCA2025010', 'Meera Iyer',       'meera@bca.edu',   'demo123', 6, 6.0,  60, 10),
]

SEED_TASKS = [
    ('Mini Project: Library Management System', 'DBMS',                 'high',   1),
    ('Responsive Portfolio Website',             'Web Technologies',     'medium', 4),
    ('Implement BST Operations',                 'DSA',                  'medium', 7),
    ('SRS Document for Student Portal',          'Software Engineering', 'high',   2),
]

with app.app_context():
    added = 0
    updated = 0

    for sid, name, email, pwd, sem, cgpa, att, rank in DEMO_STUDENTS:
        existing = User.query.filter_by(student_id=sid).first()
        if existing:
            # Update CGPA/attendance to 10-point scale
            existing.cgpa = cgpa
            existing.attendance = att
            existing.rank = rank
            existing.target_cgpa = round(min(cgpa + 0.5, 10.0), 1)
            updated += 1
            print(f"  ✏️  Updated  {sid} — {name} | CGPA: {cgpa}/10")
        else:
            user = User(
                student_id=sid, name=name, email=email,
                password_hash=generate_password_hash(pwd),
                semester=sem, cgpa=cgpa, attendance=att, rank=rank,
                target_cgpa=round(min(cgpa + 0.5, 10.0), 1),
                branch='BCA', role='student'
            )
            db.session.add(user)
            db.session.flush()

            now = datetime.now()
            for title, subject, priority, days in SEED_TASKS:
                db.session.add(Task(
                    user_id=user.id, title=title, subject=subject,
                    priority=priority, due_date=now + timedelta(days=days),
                    description=f'Complete {title} before the deadline.', done=False
                ))

            db.session.add(Notification(
                user_id=user.id, title='Welcome to Aethelgard!',
                message='Your full-stack BCA Student Portal is live. Explore all features!',
                type='success'
            ))
            added += 1
            print(f"  ✅  Added   {sid} — {name} | CGPA: {cgpa}/10 | Attendance: {att}%")

    db.session.commit()
    total = User.query.filter_by(role='student').count()
    print(f"\n{'─'*55}")
    print(f"  Done! Added: {added} | Updated: {updated} | Total students: {total}")
    print(f"  All CGPAs are now on 10-point scale ✓")
    print(f"{'─'*55}")
