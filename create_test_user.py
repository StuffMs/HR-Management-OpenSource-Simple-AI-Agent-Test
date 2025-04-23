from app import app, db, User
import hashlib

# Use application context
with app.app_context():
    # Check if test user exists
    user = User.query.filter_by(username='testuser').first()
    print(f'Regular user exists: {user is not None}')

    # Create test user if it doesn't exist
    if not user:
        new_user = User(username='testuser', password_hash=hashlib.sha256('password'.encode()).hexdigest(), is_admin=False)
        db.session.add(new_user)
        db.session.commit()
        print('Created new test user')
    
    # Check if admin user exists
    admin = User.query.filter_by(username='admin').first()
    print(f'Admin user exists: {admin is not None}')
    
    # Create admin user if it doesn't exist
    if not admin:
        new_admin = User(username='admin', password_hash=hashlib.sha256('admin'.encode()).hexdigest(), is_admin=True)
        db.session.add(new_admin)
        db.session.commit()
        print('Created new admin user')