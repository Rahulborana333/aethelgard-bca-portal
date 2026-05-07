from app import create_app
from app.extensions import db
from app.models import EBook

app = create_app()

with app.app_context():
    if not EBook.query.first():
        books = [
            EBook(title='Introduction to Algorithms', subject='DSA', author='Thomas H. Cormen', category='e-book', file_path='algorithms.pdf'),
            EBook(title='Database System Concepts', subject='DBMS', author='Silberschatz, Korth, Sudarshan', category='e-book', file_path='dbms_concepts.pdf'),
            EBook(title='Data Communications and Networking', subject='Computer Networks', author='Behrouz A. Forouzan', category='e-book', file_path='networking_forouzan.pdf'),
            EBook(title='Modern Operating Systems', subject='OS', author='Andrew S. Tanenbaum', category='e-book', file_path='modern_os.pdf'),
            EBook(title='Software Engineering: A Practitioner\'s Approach', subject='Software Engineering', author='Roger S. Pressman', category='e-book', file_path='se_pressman.pdf'),
            EBook(title='Lecture Notes: Binary Trees & BST', subject='DSA', author='Dr. A. Sharma', category='notes', file_path='bst_notes.pdf'),
            EBook(title='SQL Joins & Subqueries Cheatsheet', subject='DBMS', author='Prof. M. Gupta', category='notes', file_path='sql_cheatsheet.pdf'),
            EBook(title='OSI Model Explained', subject='Computer Networks', author='Dr. S. Reddy', category='notes', file_path='osi_notes.pdf')
        ]
        db.session.add_all(books)
        db.session.commit()
        print("✅ E-Library successfully seeded with 8 dummy resources.")
    else:
        print("ℹ️ E-Library is already seeded.")
