from app import app, db, User, Employee

with app.app_context():
    # Check if admin user exists
    admin = User.query.filter_by(username='admin').first()
    print(f'Admin exists: {admin is not None}')
    
    if admin is None:
        # Create admin user
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("Admin user created")
    
    # List all users
    print('\nCurrent Users:')
    for u in User.query.all():
        print(f'{u.id}: {u.username} - Admin: {u.is_admin} - Employee ID: {u.employee_id}')
    
    # List all employees
    print('\nCurrent Employees:')
    for e in Employee.query.all():
        print(f'{e.id}: {e.first_name} {e.last_name} - {e.department} ({e.position}) - Salary: ${e.salary}')