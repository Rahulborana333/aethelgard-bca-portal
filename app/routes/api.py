import os
from werkzeug.utils import secure_filename
from flask import Blueprint, request, jsonify
from datetime import datetime, timezone
from app.extensions import db
from app.models import User, Task, Notification, SamplePaper, EBook, Bookmark
from app.utils import current_user

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/stats')
def api_stats():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    now = datetime.now(timezone.utc)  # timezone-aware to match DB
    tasks = Task.query.filter_by(user_id=user.id).all()
    def _due(t): return t.due_date.replace(tzinfo=timezone.utc) if t.due_date.tzinfo is None else t.due_date
    pending = sum(1 for t in tasks if not t.done and _due(t) > now)
    overdue = sum(1 for t in tasks if not t.done and _due(t) <= now)
    completed = sum(1 for t in tasks if t.done)
    unread = Notification.query.filter_by(user_id=user.id, read=False).count()
    return jsonify({
        'cgpa': user.cgpa, 'attendance': user.attendance, 'rank': user.rank,
        'pending_tasks': pending, 'overdue_tasks': overdue,
        'completed_tasks': completed, 'unread_notifications': unread,
        'name': user.name
    })


@api_bp.route('/tasks', methods=['GET'])
def api_tasks_get():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    tasks = Task.query.filter_by(user_id=user.id).order_by(Task.due_date.asc()).all()
    return jsonify([t.to_dict() for t in tasks])


@api_bp.route('/tasks', methods=['POST'])
def api_tasks_post():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json() or {}
    try:
        due_str = data.get('due', '').replace('Z', '+00:00')  # fix JS toISOString() 'Z' suffix
        due = datetime.fromisoformat(due_str)
    except Exception:
        return jsonify({'error': 'Invalid due date format'}), 400

    task = Task(user_id=user.id, title=data.get('title', ''),
                subject=data.get('subject', 'DBMS'),
                priority=data.get('priority', 'medium'),
                due_date=due, description=data.get('desc', ''))
    db.session.add(task)
    db.session.flush()

    notif = Notification(user_id=user.id, title='New Task Added',
                         message=f'"{task.title}" added under {task.subject}.',
                         type='info')
    db.session.add(notif)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@api_bp.route('/tasks/<int:tid>', methods=['PUT'])
def api_tasks_put(tid):
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    task = Task.query.filter_by(id=tid, user_id=user.id).first_or_404()
    data = request.get_json() or {}

    if 'title' in data:
        task.title = data['title']
    if 'subject' in data:
        task.subject = data['subject']
    if 'priority' in data:
        task.priority = data['priority']
    if 'desc' in data:
        task.description = data['desc']
    if 'due' in data:
        try:
            due_str = data['due'].replace('Z', '+00:00')  # fix JS toISOString() 'Z' suffix
            task.due_date = datetime.fromisoformat(due_str)
        except Exception:
            pass
    if 'done' in data:
        task.done = bool(data['done'])
        if task.done:
            db.session.add(Notification(user_id=user.id, title='Task Completed 🎉',
                                        message=f'"{task.title}" marked as complete!',
                                        type='success'))
    db.session.commit()
    return jsonify(task.to_dict())


@api_bp.route('/tasks/<int:tid>', methods=['DELETE'])
def api_tasks_delete(tid):
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    task = Task.query.filter_by(id=tid, user_id=user.id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/tasks/<int:tid>/upload', methods=['POST'])
def api_tasks_upload(tid):
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    task = Task.query.filter_by(id=tid, user_id=user.id).first_or_404()

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file:
        filename = secure_filename(file.filename)
        upload_folder = os.path.join('app', 'static', 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        file.save(os.path.join(upload_folder, filename))
        task.submission_file = filename
        db.session.commit()
        return jsonify({'success': True, 'filename': filename})


@api_bp.route('/profile', methods=['GET'])
def api_profile_get():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(user.to_dict())


@api_bp.route('/profile', methods=['PUT'])
def api_profile_put():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json() or {}
    if data.get('name'):
        user.name = data['name'].strip()
    if data.get('email'):
        user.email = data['email'].strip()
    if data.get('semester'):
        user.semester = int(data['semester'])
    db.session.commit()
    return jsonify({'success': True, 'message': 'Profile updated successfully!'})


@api_bp.route('/notifications', methods=['GET'])
def api_notifications_get():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    notifs = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    return jsonify([n.to_dict() for n in notifs])


@api_bp.route('/notifications/<int:nid>/read', methods=['POST'])
def api_notif_read(nid):
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    n = Notification.query.filter_by(id=nid, user_id=user.id).first()
    if n:
        n.read = True
        db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/notifications/read-all', methods=['POST'])
def api_notif_read_all():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    Notification.query.filter_by(user_id=user.id, read=False).update({'read': True})
    db.session.commit()
    return jsonify({'success': True})


@api_bp.route('/sample-papers', methods=['GET'])
def api_get_sample_papers():
    user = current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    papers = SamplePaper.query.all()
    return jsonify([p.to_dict() for p in papers])







@api_bp.route('/user/target-cgpa', methods=['POST'])
def update_target_cgpa():
    user = current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json()
    if not data or 'target_cgpa' not in data:
        return jsonify({'error': 'target_cgpa required'}), 400
    try:
        target = float(data['target_cgpa'])
        if target < 0 or target > 10.0:
            return jsonify({'error': 'Invalid target CGPA (must be 0-10.0)'}), 400
        user.target_cgpa = target
        db.session.commit()
        return jsonify({'success': True, 'target_cgpa': target})
    except ValueError:
        return jsonify({'error': 'Invalid value'}), 400


@api_bp.route('/library/books', methods=['GET'])
def get_library_books():
    user = current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    books = EBook.query.all()
    bookmarks = Bookmark.query.filter_by(user_id=user.id).all()
    bookmarked_ids = [b.ebook_id for b in bookmarks]
    
    result = []
    for book in books:
        b_dict = book.to_dict()
        b_dict['is_bookmarked'] = book.id in bookmarked_ids
        result.append(b_dict)
    return jsonify(result)

@api_bp.route('/library/books/<int:book_id>/bookmark', methods=['POST'])
def toggle_bookmark(book_id):
    user = current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    book = EBook.query.get_or_404(book_id)
    
    existing = Bookmark.query.filter_by(user_id=user.id, ebook_id=book.id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'success': True, 'is_bookmarked': False})
    else:
        new_bookmark = Bookmark(user_id=user.id, ebook_id=book.id)
        db.session.add(new_bookmark)
        db.session.commit()
        return jsonify({'success': True, 'is_bookmarked': True})


@api_bp.route('/chat', methods=['POST'])
def api_chat():
    user = current_user()
    if not user: return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.get_json()
    msg = data.get('message', '').lower()
    
    # Simple Rule-Based Academic NLP Engine
    response = "I'm a simple academic bot. You can ask me about exams, syllabus, CGPA, or assignments!"
    
    if 'exam' in msg or 'midterm' in msg or 'schedule' in msg:
        response = "Your final exams start in the 3rd week of June. Check the 'Schedule' tab for the exact timetable!"
    elif 'cgpa' in msg or 'gpa' in msg:
        response = "Your current CGPA is 3.92. You can set a target and calculate your required grades in the 'CGPA Predictor' tab."
    elif 'assignment' in msg or 'task' in msg or 'homework' in msg:
        response = "You have 5 active tasks. Your DBMS Mini Project is due tomorrow!"
    elif 'library' in msg or 'book' in msg or 'notes' in msg:
        response = "We have 8 resources in the E-Library right now, including notes on DSA and DBMS. Go to the E-Library tab to view or bookmark them."
    elif 'hello' in msg or 'hi' in msg:
        response = f"Hello {user.name}! How can I assist you with your academic portal today?"
    elif 'help' in msg:
        response = "I can help you check your schedule, tasks, or explain portal features. Just ask!"

    return jsonify({'success': True, 'response': response})
