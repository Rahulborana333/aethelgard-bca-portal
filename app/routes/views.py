from flask import Blueprint, render_template, redirect
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models import EBook, User
from app.utils import current_user

views_bp = Blueprint('views', __name__)


def is_logged_in():
    try:
        verify_jwt_in_request(optional=True)
        return get_jwt_identity() is not None
    except Exception:
        return False


@views_bp.route('/')
def index():
    if not is_logged_in():
        return redirect('/login')
    # If the logged-in user is an admin, redirect them to the admin panel
    user = current_user()
    if user and user.role == 'admin':
        return redirect('/admin/')
    return render_template('index.html')


@views_bp.route('/login')
def login_page():
    if is_logged_in():
        # Redirect admins directly to admin panel from login page too
        user = current_user()
        if user and user.role == 'admin':
            return redirect('/admin/')
        return redirect('/')
    return render_template('login.html')


@views_bp.route('/signup')
def signup_page():
    if is_logged_in():
        return redirect('/')
    return render_template('signup.html')


@views_bp.route('/task')
def task_page():
    if not is_logged_in():
        return redirect('/login')
    return render_template('task.html')


@views_bp.route('/schedule')
def schedule_page():
    if not is_logged_in():
        return redirect('/login')
    return render_template('schedule.html')


@views_bp.route('/profile')
def profile_page():
    if not is_logged_in():
        return redirect('/login')
    return render_template('profile.html')


@views_bp.route('/notifications')
def notifications_page():
    if not is_logged_in():
        return redirect('/login')
    return render_template('notifications.html')





@views_bp.route('/cgpa-predictor')
def cgpa_predictor_page():
    if not is_logged_in(): return redirect('/login')
    return render_template('cgpa.html')

@views_bp.route('/library')
def library_page():
    if not is_logged_in(): return redirect('/login')
    return render_template('library.html')

@views_bp.route('/view-pdf/<int:book_id>')
def view_pdf(book_id):
    if not is_logged_in(): return redirect('/login')
    book = EBook.query.get_or_404(book_id)
    return render_template('view_pdf.html', book=book)

@views_bp.route('/study-room')
def study_room():
    if not is_logged_in(): return redirect('/login')
    return render_template('study.html')
