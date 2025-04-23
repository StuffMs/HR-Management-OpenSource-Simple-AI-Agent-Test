from app import app, db, User
import random
import string

def random_string(length=8):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

with app.app_context():
    # Create a test user
    username = f"testuser_{random_string(5)}"
    password = random_string(10)
    employee_id = f"EMP{random.randint(1000, 9999)}"
    
    # Check if username already exists
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        print(f"Username {username} already exists")
    else:
        # Create new user
        new_user = User(username=username, is_admin=False, employee_code=employee_id)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        print(f"User created successfully:")
        print(f"Username: {username}")
        print(f"Password: {password}")
        print(f"Employee ID: {employee_id}")
        
        # Verify user was created
        created_user = User.query.filter_by(username=username).first()
        if created_user:
            print(f"User verified in database: {created_user.username} (ID: {created_user.id})")
        else:
            print("Failed to verify user in database")