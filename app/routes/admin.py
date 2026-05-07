from flask import Blueprint, request, jsonify, render_template
from app.extensions import db, socketio
from app.models import User, Notification, EBook, SamplePaper, Task, SystemSetting, AuditLog, Bookmark
from app.utils import admin_required, log_admin_action
from sqlalchemy import func

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/')
@admin_required
def admin_dashboard():
    return render_template('admin.html')


@admin_bp.route('/api/stats', methods=['GET'])
@admin_required
def api_admin_stats():
    total_students = User.query.filter_by(role='student').count()
    active_students = User.query.filter_by(role='student', is_active=True).count()
    suspended_students = User.query.filter_by(role='student', is_active=False).count()
    total_admins = User.query.filter_by(role='admin').count()
    avg_cgpa = db.session.query(func.avg(User.cgpa)).filter(User.role == 'student').scalar() or 0
    avg_attendance = db.session.query(func.avg(User.attendance)).filter(User.role == 'student').scalar() or 0
    total_ebooks = EBook.query.count()
    total_papers = SamplePaper.query.count()
    total_books = total_ebooks + total_papers
    total_tasks = Task.query.count()
    completed_tasks = Task.query.filter_by(done=True).count()
    pending_tasks = Task.query.filter_by(done=False).count()
    total_notifications = Notification.query.count()
    total_bookmarks = Bookmark.query.count()

    # CGPA distribution for pie chart
    high_performers = User.query.filter(User.role == 'student', User.cgpa >= 3.5).count()
    mid_performers = User.query.filter(User.role == 'student', User.cgpa >= 2.5, User.cgpa < 3.5).count()
    low_performers = User.query.filter(User.role == 'student', User.cgpa < 2.5).count()

    # Attendance distribution
    good_attendance = User.query.filter(User.role == 'student', User.attendance >= 80).count()
    avg_att = User.query.filter(User.role == 'student', User.attendance >= 60, User.attendance < 80).count()
    low_attendance = User.query.filter(User.role == 'student', User.attendance < 60).count()

    return jsonify({
        'total_students': total_students,
        'active_students': active_students,
        'suspended_students': suspended_students,
        'total_admins': total_admins,
        'avg_cgpa': round(avg_cgpa, 2),
        'avg_attendance': round(avg_attendance, 1),
        'total_books': total_books,
        'total_ebooks': total_ebooks,
        'total_papers': total_papers,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'total_notifications': total_notifications,
        'total_bookmarks': total_bookmarks,
        'cgpa_dist': {'high': high_performers, 'mid': mid_performers, 'low': low_performers},
        'attendance_dist': {'good': good_attendance, 'avg': avg_att, 'low': low_attendance}
    })


@admin_bp.route('/api/students', methods=['GET'])
@admin_required
def api_get_students():
    students = User.query.filter_by(role='student').order_by(User.created_at.desc()).all()
    return jsonify([s.to_dict() for s in students])


@admin_bp.route('/api/all-users', methods=['GET'])
@admin_required
def api_get_all_users():
    """Get all users including admins for role management"""
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users])


@admin_bp.route('/api/students/<int:sid>', methods=['DELETE'])
@admin_required
def api_delete_student(sid):
    student = User.query.get_or_404(sid)
    if student.role == 'admin':
        return jsonify({'error': 'Cannot delete admin'}), 403

    name = student.name
    db.session.delete(student)
    db.session.commit()
    log_admin_action(f"Deleted student account: {name} ({sid})")
    return jsonify({'success': True})


@admin_bp.route('/api/students/<int:sid>/promote', methods=['POST'])
@admin_required
def api_promote_student(sid):
    student = User.query.get_or_404(sid)
    student.role = 'admin'
    db.session.commit()
    log_admin_action(f"Promoted student to Admin: {student.name}")
    return jsonify({'success': True})


@admin_bp.route('/api/students/<int:sid>/demote', methods=['POST'])
@admin_required
def api_demote_to_student(sid):
    """Demote an admin back to student role"""
    user = User.query.get_or_404(sid)
    if user.role != 'admin':
        return jsonify({'error': 'User is not an admin'}), 400
    user.role = 'student'
    db.session.commit()
    log_admin_action(f"Demoted admin to Student: {user.name}")
    return jsonify({'success': True})


@admin_bp.route('/api/students/<int:sid>/toggle-access', methods=['POST'])
@admin_required
def api_toggle_access(sid):
    """Suspend or restore a student's access"""
    student = User.query.get_or_404(sid)
    if student.role == 'admin':
        return jsonify({'error': 'Cannot suspend admin accounts'}), 403

    student.is_active = not (student.is_active if student.is_active is not None else True)
    db.session.commit()

    action = 'Restored' if student.is_active else 'Suspended'
    log_admin_action(f"{action} access for: {student.name} ({student.student_id})")

    # Notify the student
    notif = Notification(
        user_id=student.id,
        title=f'Account {action}',
        message=f'Your portal access has been {action.lower()} by the administrator.',
        type='success' if student.is_active else 'danger'
    )
    db.session.add(notif)
    db.session.commit()

    return jsonify({'success': True, 'is_active': student.is_active, 'action': action})


@admin_bp.route('/api/students/<int:sid>/update', methods=['PUT'])
@admin_required
def api_update_student(sid):
    """Update student academic details (CGPA, attendance, rank, semester)"""
    student = User.query.get_or_404(sid)
    data = request.get_json() or {}

    if 'cgpa' in data:
        student.cgpa = float(data['cgpa'])
    if 'attendance' in data:
        student.attendance = int(data['attendance'])
    if 'rank' in data:
        student.rank = int(data['rank'])
    if 'semester' in data:
        student.semester = int(data['semester'])

    db.session.commit()
    log_admin_action(f"Updated student details: {student.name}")
    return jsonify({'success': True, 'student': student.to_dict()})


@admin_bp.route('/api/students/<int:sid>/message', methods=['POST'])
@admin_required
def api_send_student_message(sid):
    """Send a direct notification message to a specific student"""
    student = User.query.get_or_404(sid)
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    message = data.get('message', '').strip()
    type_ = data.get('type', 'info')

    if not title or not message:
        return jsonify({'error': 'Title and message are required'}), 400

    notif = Notification(
        user_id=student.id,
        title=title,
        message=message,
        type=type_
    )
    db.session.add(notif)
    db.session.commit()

    # Emit real-time socket event
    socketio.emit('new_notification', {
        'title': title, 'message': message, 'type': type_
    }, room=None)

    log_admin_action(f"Sent direct message to {student.name}: '{title}'")
    return jsonify({'success': True, 'student_name': student.name})


@admin_bp.route('/api/students/<int:sid>/profile', methods=['GET'])
@admin_required
def api_student_profile(sid):
    """Get full student profile including tasks, notifications, bookmarks"""
    student = User.query.get_or_404(sid)

    tasks = [t.to_dict() for t in student.tasks]
    notifications = [n.to_dict() for n in
                     Notification.query.filter_by(user_id=sid)
                     .order_by(Notification.created_at.desc()).limit(10).all()]
    bookmarks = Bookmark.query.filter_by(user_id=sid).count()

    completed = sum(1 for t in student.tasks if t.done)
    pending = sum(1 for t in student.tasks if not t.done)

    return jsonify({
        'student': student.to_dict(),
        'tasks': tasks,
        'task_stats': {'total': len(tasks), 'completed': completed, 'pending': pending},
        'notifications': notifications,
        'bookmarks_count': bookmarks,
    })


@admin_bp.route('/api/library', methods=['GET'])
@admin_required
def api_get_library():
    books = EBook.query.all()
    papers = SamplePaper.query.all()

    res = []
    for b in books:
        d = b.to_dict()
        d['resource_type'] = 'ebook'
        res.append(d)
    for p in papers:
        d = p.to_dict()
        d['resource_type'] = 'paper'
        res.append(d)

    return jsonify(res)


@admin_bp.route('/api/library', methods=['POST'])
@admin_required
def api_add_library():
    data = request.get_json() or {}
    res_type = data.get('type') # 'ebook' or 'paper'

    if res_type == 'ebook':
        item = EBook(
            title=data.get('title'),
            subject=data.get('subject'),
            author=data.get('author'),
            category=data.get('category', 'e-book'),
            file_path=data.get('file_path'),
            cover_image=data.get('cover_image')
        )
    elif res_type == 'paper':
        item = SamplePaper(
            title=data.get('title'),
            subject=data.get('subject'),
            file_path=data.get('file_path'),
            type=data.get('paper_type', 'paper')
        )
    else:
        return jsonify({'error': 'Invalid resource type'}), 400

    if not item.title or not item.file_path:
        return jsonify({'error': 'Title and File Path are required'}), 400

    db.session.add(item)
    db.session.commit()
    log_admin_action(f"Added new {res_type}: {item.title}")
    return jsonify({'success': True, 'item': item.to_dict()})


@admin_bp.route('/api/library/<string:rtype>/<int:rid>', methods=['DELETE'])
@admin_required
def api_delete_library(rtype, rid):
    if rtype == 'ebook':
        item = EBook.query.get_or_404(rid)
    elif rtype == 'paper':
        item = SamplePaper.query.get_or_404(rid)
    else:
        return jsonify({'error': 'Invalid type'}), 400

    title = item.title
    db.session.delete(item)
    db.session.commit()
    log_admin_action(f"Deleted {rtype}: {title}")
    return jsonify({'success': True})


@admin_bp.route('/api/broadcast', methods=['POST'])
@admin_required
def api_broadcast_notification():
    data = request.get_json() or {}
    title = data.get('title')
    message = data.get('message')
    type_ = data.get('type', 'info')

    if not title or not message:
        return jsonify({'error': 'Title and message are required'}), 400

    students = User.query.filter_by(role='student').all()
    for student in students:
        notif = Notification(user_id=student.id, title=title, message=message, type=type_)
        db.session.add(notif)
    db.session.commit()

    socketio.emit('new_notification', {'title': title, 'message': message, 'type': type_})
    log_admin_action(f"Broadcasted notification: {title}")

    return jsonify({'success': True, 'count': len(students)})


@admin_bp.route('/api/logs', methods=['GET'])
@admin_required
def api_get_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()
    return jsonify([l.to_dict() for l in logs])


@admin_bp.route('/api/settings', methods=['GET', 'POST'])
@admin_required
def api_settings():
    if request.method == 'POST':
        data = request.get_json() or {}
        for key, val in data.items():
            setting = SystemSetting.query.filter_by(key=key).first()
            if setting:
                setting.value = str(val)
            else:
                setting = SystemSetting(key=key, value=str(val))
                db.session.add(setting)
        db.session.commit()
        log_admin_action("Updated system settings")
        return jsonify({'success': True})

    settings = SystemSetting.query.all()
    return jsonify({s.key: s.value for s in settings})


@admin_bp.route('/api/export/students', methods=['GET'])
@admin_required
def api_export_students():
    """Export student data as CSV"""
    students = User.query.filter_by(role='student').order_by(User.name).all()
    import io, csv
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student ID', 'Name', 'Email', 'Semester', 'Branch', 'CGPA', 'Attendance', 'Rank', 'Status', 'Joined'])
    for s in students:
        status = 'Active' if (s.is_active if s.is_active is not None else True) else 'Suspended'
        writer.writerow([s.student_id, s.name, s.email, s.semester, s.branch, s.cgpa, s.attendance, s.rank, status, s.created_at.strftime('%Y-%m-%d')])
    csv_data = output.getvalue()
    from flask import Response
    return Response(csv_data, mimetype='text/csv', headers={'Content-Disposition': 'attachment;filename=students_export.csv'})
