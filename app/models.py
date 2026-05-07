from datetime import datetime, timezone
from .extensions import db


class User(db.Model):
    """Student user account"""
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    semester = db.Column(db.Integer, default=6)
    branch = db.Column(db.String(50), default='BCA')
    cgpa = db.Column(db.Float, default=3.92)
    target_cgpa = db.Column(db.Float, default=4.0)
    attendance = db.Column(db.Integer, default=87)
    rank = db.Column(db.Integer, default=3)
    role = db.Column(db.String(20), default='student')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    tasks = db.relationship('Task', backref='user', lazy=True, cascade='all, delete-orphan')
    notifications = db.relationship('Notification', backref='user', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'student_id': self.student_id,
            'email': self.email, 'semester': self.semester, 'branch': self.branch,
            'cgpa': self.cgpa, 'target_cgpa': self.target_cgpa, 'attendance': self.attendance, 'rank': self.rank,
            'role': self.role, 'is_active': self.is_active if self.is_active is not None else True,
            'created_at': self.created_at.strftime('%B %Y')
        }


class Task(db.Model):
    """Academic assignment / task"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    priority = db.Column(db.String(20), default='medium')
    due_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text, default='')
    done = db.Column(db.Boolean, default=False)
    submission_file = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'subject': self.subject,
            'priority': self.priority, 'due': self.due_date.isoformat(),
            'desc': self.description, 'done': self.done,
            'submission_file': self.submission_file,
            'created_at': self.created_at.isoformat()
        }


class Notification(db.Model):
    """System / academic notifications"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='info')   # info|warning|success|danger
    read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'message': self.message,
            'type': self.type, 'read': self.read,
            'created_at': self.created_at.strftime('%d %b %Y, %I:%M %p')
        }


class SamplePaper(db.Model):
    """Downloadable Sample Papers and Important Questions"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    type = db.Column(db.String(50), default='paper')  # 'paper' or 'important_qs'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'subject': self.subject,
            'file_path': self.file_path, 'type': self.type,
            'created_at': self.created_at.isoformat()
        }





class EBook(db.Model):
    """Digital E-Books and Notes"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    author = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(50), default='e-book') # e-book, notes
    file_path = db.Column(db.String(500), nullable=False)
    cover_image = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'subject': self.subject,
            'author': self.author, 'category': self.category,
            'file_path': self.file_path, 'cover_image': self.cover_image,
            'created_at': self.created_at.isoformat()
        }


class Bookmark(db.Model):
    """User Bookmarks for EBooks"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    ebook_id = db.Column(db.Integer, db.ForeignKey('e_book.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    ebook = db.relationship('EBook')


class AuditLog(db.Model):
    """Admin action logs"""
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    admin = db.relationship('User', backref='audit_logs')

    def to_dict(self):
        return {
            'id': self.id, 'admin_name': self.admin.name,
            'action': self.action,
            'timestamp': self.timestamp.strftime('%d %b %Y, %I:%M %p')
        }


class SystemSetting(db.Model):
    """Global portal settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String(500), nullable=False)
    description = db.Column(db.String(500))

    @staticmethod
    def get_val(key, default=None):
        s = SystemSetting.query.filter_by(key=key).first()
        return s.value if s else default


