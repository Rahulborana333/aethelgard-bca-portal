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

    # CGPA distribution for pie chart (10-point scale)
    high_performers = User.query.filter(User.role == 'student', User.cgpa >= 8.0).count()
    mid_performers = User.query.filter(User.role == 'student', User.cgpa >= 5.0, User.cgpa < 8.0).count()
    low_performers = User.query.filter(User.role == 'student', User.cgpa < 5.0).count()

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


# ═══════════════════════════════════════════════════
#  AI INTELLIGENCE ENGINE
# ═══════════════════════════════════════════════════

def _calc_health_score(student):
    """Calculate AI Health Score (0–100) for a student."""
    cgpa = student.cgpa or 0
    attendance = student.attendance or 0
    tasks = student.tasks
    task_completion = (sum(1 for t in tasks if t.done) / len(tasks) * 100) if tasks else 50
    score = round((cgpa / 10.0) * 40 + (attendance / 100) * 35 + (task_completion / 100) * 25)
    return score, round(task_completion)


@admin_bp.route('/api/ai/insights', methods=['GET'])
@admin_required
def api_ai_insights():
    """AI-powered class-wide insights and recommendations."""
    students = User.query.filter_by(role='student').all()
    if not students:
        return jsonify({'insights': [], 'class_health': 0, 'at_risk_count': 0,
                        'recommendations': [], 'total_students': 0})

    total = len(students)
    at_risk, low_cgpa, low_att, high_perf, suspended_list = [], [], [], [], []

    for s in students:
        score, _ = _calc_health_score(s)
        is_active = s.is_active if s.is_active is not None else True
        if not is_active:
            suspended_list.append(s)
        if (s.cgpa or 0) < 5.0:
            low_cgpa.append(s)
        if (s.attendance or 0) < 60:
            low_att.append(s)
        if (s.cgpa or 0) < 5.0 and (s.attendance or 0) < 60:
            at_risk.append(s)
        if (s.cgpa or 0) >= 8.0 and (s.attendance or 0) >= 80:
            high_perf.append(s)

    avg_cgpa = sum(s.cgpa or 0 for s in students) / total
    avg_att = sum(s.attendance or 0 for s in students) / total
    all_scores = [_calc_health_score(s)[0] for s in students]
    class_health = round(sum(all_scores) / total)

    insights, recommendations = [], []

    if at_risk:
        insights.append({'type': 'danger', 'icon': 'crisis_alert',
            'title': f'{len(at_risk)} Students Critically At Risk',
            'desc': f'{len(at_risk)} students have CGPA below 2.5 AND attendance below 60%. Immediate intervention is required.',
            'count': len(at_risk), 'names': [s.name for s in at_risk[:3]]})
        recommendations.append(f'Schedule urgent counseling sessions for {len(at_risk)} at-risk students.')

    if len(low_att) > total * 0.25:
        recommendations.append('Send an urgent attendance warning broadcast — over 25% of students are below 60%.')

    if low_att:
        insights.append({'type': 'warning', 'icon': 'event_busy',
            'title': f'{len(low_att)} Students Have Poor Attendance',
            'desc': f'{len(low_att)} out of {total} students have attendance below 60%, risking exam eligibility.',
            'count': len(low_att), 'names': []})

    if low_cgpa:
        insights.append({'type': 'warning', 'icon': 'grade',
            'title': f'{len(low_cgpa)} Students Below Minimum CGPA',
            'desc': f'{len(low_cgpa)} students have CGPA below 5.0. Additional academic support is recommended.',
            'count': len(low_cgpa), 'names': []})

    if high_perf:
        insights.append({'type': 'success', 'icon': 'emoji_events',
            'title': f'{len(high_perf)} High Performers Identified',
            'desc': f'{len(high_perf)} students have CGPA ≥ 8.0 and attendance ≥ 80%. Consider merit recognition.',
            'count': len(high_perf), 'names': [s.name for s in high_perf[:3]]})
        recommendations.append(f'Send merit congratulation notifications to {len(high_perf)} high performers.')

    if avg_att >= 80:
        insights.append({'type': 'success', 'icon': 'trending_up',
            'title': 'Excellent Class Attendance Rate',
            'desc': f'Average attendance is {round(avg_att, 1)}% — above the 80% threshold. Great overall engagement!',
            'count': None, 'names': []})

    if suspended_list:
        insights.append({'type': 'info', 'icon': 'manage_accounts',
            'title': f'{len(suspended_list)} Accounts Currently Suspended',
            'desc': f'{len(suspended_list)} student accounts are suspended. Review these cases and restore if resolved.',
            'count': len(suspended_list), 'names': []})

    if not recommendations:
        recommendations.append('All systems look healthy! Keep monitoring student performance regularly.')

    return jsonify({
        'insights': insights, 'class_health': class_health,
        'at_risk_count': len(at_risk), 'high_performers_count': len(high_perf),
        'avg_cgpa': round(avg_cgpa, 2), 'avg_attendance': round(avg_att, 1),
        'recommendations': recommendations, 'total_students': total,
        'low_cgpa_count': len(low_cgpa), 'low_att_count': len(low_att)
    })


@admin_bp.route('/api/ai/at-risk', methods=['GET'])
@admin_required
def api_ai_at_risk():
    """Get all students with AI health scores, sorted worst-first."""
    students = User.query.filter_by(role='student').all()
    result = []
    for s in students:
        health_score, task_completion = _calc_health_score(s)
        is_active = s.is_active if s.is_active is not None else True

        if health_score >= 75:
            risk_level, risk_label = 'low', 'Healthy'
        elif health_score >= 55:
            risk_level, risk_label = 'medium', 'Monitor'
        elif health_score >= 35:
            risk_level, risk_label = 'high', 'At Risk'
        else:
            risk_level, risk_label = 'critical', 'Critical'

        issues = []
        if (s.cgpa or 0) < 5.0:
            issues.append('Low CGPA')
        if (s.attendance or 0) < 60:
            issues.append('Poor Attendance')
        if not is_active:
            issues.append('Suspended')
        if task_completion < 30 and s.tasks:
            issues.append('Low Task Completion')

        result.append({**s.to_dict(), 'health_score': health_score,
                        'risk_level': risk_level, 'risk_label': risk_label,
                        'task_completion': task_completion, 'issues': issues})

    result.sort(key=lambda x: x['health_score'])
    return jsonify(result)


@admin_bp.route('/api/ai/smart-message/<int:sid>', methods=['GET'])
@admin_required
def api_ai_smart_message(sid):
    """Generate AI-suggested personalized messages for a student."""
    student = User.query.get_or_404(sid)
    cgpa = student.cgpa or 0
    attendance = student.attendance or 0
    tasks = student.tasks
    task_completion = (sum(1 for t in tasks if t.done) / len(tasks) * 100) if tasks else 50
    health_score, _ = _calc_health_score(student)

    suggestions = []

    if attendance < 60:
        suggestions.append({'type': 'danger', 'label': '🚨 Attendance Warning',
            'title': 'Urgent: Critical Attendance Alert',
            'message': f'Dear {student.name}, your current attendance stands at {attendance}%, which is critically below the required 75% threshold. You are at immediate risk of being barred from semester examinations. Please attend all upcoming classes without fail and contact your faculty advisor at the earliest.'})

    if cgpa < 5.0:
        suggestions.append({'type': 'warning', 'label': '⚠️ CGPA Alert',
            'title': 'Academic Performance Needs Improvement',
            'message': f'Dear {student.name}, we have noted that your CGPA of {cgpa} is below the minimum required standard of 5.0 out of 10. Please make use of the E-Library resources, attend remedial sessions, and consult your subject teachers for guidance. Your improvement in upcoming assessments is critical.'})

    if cgpa >= 8.0 and attendance >= 80:
        suggestions.append({'type': 'success', 'label': '🏆 Merit Recognition',
            'title': 'Outstanding Academic Achievement — Congratulations!',
            'message': f'Dear {student.name}, we are delighted to recognize your outstanding academic performance! Your CGPA of {cgpa} out of 10 and attendance of {attendance}% place you among the top performers of this semester. Your dedication and hard work are truly commendable. Keep excelling!'})

    if task_completion < 40 and tasks:
        suggestions.append({'type': 'warning', 'label': '📋 Task Reminder',
            'title': 'Pending Assignments Require Immediate Attention',
            'message': f'Dear {student.name}, our records show that several of your assignments remain incomplete on the academic portal. Timely submission of tasks is an important part of your overall academic profile. Please review your pending tasks and submit them before the respective deadlines.'})

    if attendance >= 90:
        suggestions.append({'type': 'success', 'label': '🎖️ Attendance Star',
            'title': 'Excellent Attendance — Keep It Up!',
            'message': f'Dear {student.name}, your attendance of {attendance}% is truly exemplary and reflects your commitment to academics. The faculty and administration appreciate your regularity. Keep up this wonderful habit throughout the semester!'})

    suggestions.append({'type': 'info', 'label': '📢 General Reminder',
        'title': 'General Academic Update & Reminder',
        'message': f'Dear {student.name}, this is a general reminder to stay on track with your academic responsibilities. Regular attendance, timely assignment completion, and active use of portal resources are key to your success. The faculty team is always available for guidance and support.'})

    return jsonify({'student': student.to_dict(), 'health_score': health_score,
                    'task_completion': round(task_completion), 'suggestions': suggestions})
