from app import create_app

app = create_app()
app.testing = True
client = app.test_client()

with app.app_context():
    print("Testing /login...")
    r = client.get('/login')
    print("/login status:", r.status_code)
    
    print("Testing /signup...")
    r = client.get('/signup')
    print("/signup status:", r.status_code)
    
    # login
    client.post('/api/auth/login', json={'student_id': 'BCA2025001', 'password': 'demo123'})
    
    print("Testing /...")
    r = client.get('/')
    print("/ status:", r.status_code)
    if r.status_code != 200:
        print(r.data.decode('utf-8'))
        
    print("Testing /schedule...")
    r = client.get('/schedule')
    print("/schedule status:", r.status_code)
    if r.status_code != 200:
        print(r.data.decode('utf-8'))
        
    print("Testing /task...")
    r = client.get('/task')
    print("/task status:", r.status_code)
    if r.status_code != 200:
        print(r.data.decode('utf-8'))
        
    print("Testing /profile...")
    r = client.get('/profile')
    print("/profile status:", r.status_code)
    if r.status_code != 200:
        print(r.data.decode('utf-8'))
        
    print("Testing /notifications...")
    r = client.get('/notifications')
    print("/notifications status:", r.status_code)
    if r.status_code != 200:
        print(r.data.decode('utf-8'))

