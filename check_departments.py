from app import app, db, Employee

with app.app_context():
    departments = db.session.query(Employee.department).distinct().all()
    departments = [dept[0] for dept in departments]
    
    print('Current Departments:')
    for dept in departments:
        count = Employee.query.filter_by(department=dept).count()
        print(f'{dept}: {count} employees')