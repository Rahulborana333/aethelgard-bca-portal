from functools import wraps
from flask import redirect
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from .models import User, AuditLog
from .extensions import db

def current_user():
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        return User.query.get(uid) if uid else None
    except Exception:
        return None

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if not user or user.role != 'admin':
            return redirect('/')
        return f(*args, **kwargs)
    return wrapper

def log_admin_action(action):
    user = current_user()
    if user:
        log = AuditLog(admin_id=user.id, action=action)
        db.session.add(log)
        db.session.commit()
