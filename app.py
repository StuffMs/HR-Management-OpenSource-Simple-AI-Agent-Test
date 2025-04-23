from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from functools import wraps
from markupsafe import Markup
import os
import json
import hashlib
import uuid
from werkzeug.utils import secure_filename
from google_drive_helper import GoogleDriveHelper

app = Flask(__name__)

# Add nl2br filter
@app.template_filter('nl2br')
def nl2br(value):
    if value:
        return Markup(value.replace('\n', '<br>'))

# Load configuration from config.py
try:
    app.config.from_object('config')
except ImportError:
    # Fallback configuration if config.py doesn't exist
    app.config['SECRET_KEY'] = 'your-secret-key'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///employees.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size
    app.config['GOOGLE_DRIVE_ENABLED'] = False
    
    # File upload configuration
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
    app.config['PROFILE_PICTURES_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pictures')
    app.config['DOCUMENTS_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'documents')

# Increase request body size limit for file uploads
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app)

# Set up upload folders if not defined in config
if 'UPLOAD_FOLDER' not in app.config:
    app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
    app.config['PROFILE_PICTURES_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pictures')
    app.config['DOCUMENTS_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'documents')

# File type configuration
app.config['ALLOWED_DOCUMENT_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}
app.config['ALLOWED_IMAGE_EXTENSIONS'] = {'jpg', 'jpeg', 'png', 'gif'}

# Initialize Google Drive helper
drive_helper = None
if app.config.get('GOOGLE_DRIVE_ENABLED', False):
    try:
        credentials_file = app.config.get('GOOGLE_DRIVE_CREDENTIALS_FILE')
        root_folder_name = app.config.get('GOOGLE_DRIVE_ROOT_FOLDER_NAME', 'Employee Management System')
        drive_helper = GoogleDriveHelper(credentials_file, root_folder_name)
        app.logger.info("Google Drive integration enabled")
    except Exception as e:
        app.logger.error(f"Failed to initialize Google Drive: {str(e)}")
        app.config['GOOGLE_DRIVE_ENABLED'] = False

db = SQLAlchemy(app)

# Helper function to check if file extension is allowed
def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Please log in to access this page', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin', False):
            flash('You do not have permission to access this page', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# User model for authentication
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=True)
    employee_code = db.Column(db.String(50), nullable=True)  # Store the employee ID code
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with Employee
    employee = db.relationship('Employee', backref=db.backref('user', lazy=True, uselist=False), foreign_keys=[employee_id])
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def set_password(self, password):
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

# Education model
class Education(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    institution = db.Column(db.String(100), nullable=False)
    degree = db.Column(db.String(100), nullable=False)
    field_of_study = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Education {self.degree} from {self.institution}>'

# Certification model
class Certification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    issuing_organization = db.Column(db.String(100), nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=True)
    credential_id = db.Column(db.String(100), nullable=True)
    credential_url = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Certification {self.name} from {self.issuing_organization}>'

# Document model for storing employee documents
class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)  # certificate, experience_letter, offer_letter, etc.
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    drive_file_id = db.Column(db.String(255), nullable=True)  # Google Drive file ID
    
    def __repr__(self):
        return f'<Document {self.document_type}: {self.original_filename}>'
    
    def get_url(self):
        """Get the URL for the document, either from Google Drive or local storage."""
        if self.drive_file_id and drive_helper and drive_helper.is_enabled():
            # For Google Drive files, use the drive: prefix to indicate it's a Google Drive file
            return url_for('uploaded_file', filename=f'drive:{self.drive_file_id}')
        else:
            # For local files, use the full path with forward slashes
            clean_filename = self.filename.replace('\\', '/')
            return url_for('uploaded_file', filename=f'documents/{clean_filename}')

# Employee model - updated with new fields
class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=True)  # Added employee ID field
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    department = db.Column(db.String(50), nullable=False)
    position = db.Column(db.String(50), nullable=False)
    hire_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    current_address = db.Column(db.String(200), nullable=False)  # Renamed from address
    permanent_address = db.Column(db.String(200), nullable=True)  # Added permanent address
    profile_picture = db.Column(db.String(255), nullable=True)  # Store filename of profile picture
    drive_profile_pic_id = db.Column(db.String(255), nullable=True)  # Google Drive profile picture ID
    drive_folder_id = db.Column(db.String(255), nullable=True)  # Google Drive folder ID for this employee
    salary = db.Column(db.Float, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    educations = db.relationship('Education', backref='employee', lazy=True, cascade="all, delete-orphan")
    certifications = db.relationship('Certification', backref='employee', lazy=True, cascade="all, delete-orphan")
    documents = db.relationship('Document', backref='employee', lazy=True, cascade="all, delete-orphan")
    
    def get_profile_picture_url(self):
        """Get the URL for the profile picture, either from Google Drive or local storage."""
        if self.drive_profile_pic_id and drive_helper and drive_helper.is_enabled():
            # For Google Drive files, use the drive: prefix to indicate it's a Google Drive file
            return url_for('uploaded_file', filename=f'drive:{self.drive_profile_pic_id}')
        elif self.profile_picture:
            # For local files, use the full path with forward slashes
            clean_filename = self.profile_picture.replace('\\', '/')
            return url_for('uploaded_file', filename=f'profile_pictures/{clean_filename}')
        else:
            return url_for('static', filename='img/default-profile.png')
    
    def __repr__(self):
        return f'<Employee {self.first_name} {self.last_name}>'

# Create database tables and default admin user
with app.app_context():
    db.create_all()
    
    # Create default admin user if it doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(username='admin', is_admin=True)
        admin.set_password('admin')
        db.session.add(admin)
        db.session.commit()
        print("Default admin user created")

@app.route('/login', methods=['GET', 'POST'])
def login():
    # If user is already logged in, redirect to index
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['logged_in'] = True
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            session['user_id'] = user.id
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    session.pop('is_admin', None)
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/admin/create-user', methods=['GET', 'POST'])
@login_required
def create_user():
    # Check if user is admin
    if not session.get('is_admin', False):
        flash('You do not have permission to access this page', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        employee_id = request.form.get('employee_id')
        
        # Validate inputs
        if not username or not password or not employee_id:
            flash('All fields are required', 'danger')
            return render_template('create_user.html')
            
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return render_template('create_user.html')
        
        # Check if employee_id already has a user account
        existing_user_with_employee_code = User.query.filter_by(employee_code=employee_id).first()
        if existing_user_with_employee_code:
            flash('A user account already exists for this Employee ID', 'danger')
            return render_template('create_user.html')
        
        # Check if employee_id already exists in Employee table
        existing_employee = Employee.query.filter_by(employee_id=employee_id).first()
        
        # Create new user
        new_user = User(username=username, is_admin=False, employee_code=employee_id)
        new_user.set_password(password)
        
        # If employee exists, link the user to the employee
        if existing_employee:
            new_user.employee_id = existing_employee.id
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('User created successfully', 'success')
            
            # Return the username and password to display to the admin in the modal
            return render_template('create_user.html', 
                                  new_username=username, 
                                  new_password=password, 
                                  new_employee_id=employee_id)
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating user: {str(e)}', 'danger')
            return render_template('create_user.html')
    
    return render_template('create_user.html')

@app.route('/')
@login_required
def index():
    # Check if user is logged in
    if 'logged_in' not in session:
        return redirect(url_for('login'))
        
    # Check if user is admin
    if session.get('is_admin', False):
        # Admin dashboard
        # Get all unique departments
        departments = db.session.query(Employee.department).distinct().all()
        departments = [dept[0] for dept in departments]
        
        # Count employees per department and total
        department_counts = {}
        total_employees = 0
        
        for dept in departments:
            count = Employee.query.filter_by(department=dept).count()
            department_counts[dept] = count
            total_employees += count
        
        return render_template('index.html', 
                              departments=departments, 
                              department_counts=department_counts,
                              total_employees=total_employees)
    else:
        # Employee dashboard
        # Get the current user
        user = User.query.filter_by(username=session.get('username')).first()
        
        # Check if user has an employee profile
        if user and user.employee_id:
            employee = db.session.get(Employee, user.employee_id)
            if employee:
                educations = Education.query.filter_by(employee_id=employee.id).all()
                certifications = Certification.query.filter_by(employee_id=employee.id).all()
                documents = Document.query.filter_by(employee_id=employee.id).all()
                return render_template('employee_dashboard.html', 
                                      employee=employee, 
                                      educations=educations, 
                                      certifications=certifications,
                                      documents=documents)
        
        # Redirect to self-onboarding if no profile exists
        flash('Please complete your profile information', 'info')
        return redirect(url_for('self_onboarding'))

@app.route('/department/<department>')
@login_required
def department_employees(department):
    employees = Employee.query.filter_by(department=department).all()
    return render_template('department_employees.html', department=department, employees=employees)

@app.route('/add-department', methods=['GET', 'POST'])
@admin_required
def add_department():
    if request.method == 'POST':
        department_name = request.form.get('department_name')
        
        if not department_name:
            flash('Department name cannot be empty', 'danger')
            return redirect(url_for('add_department'))
        
        # Check if department already exists
        existing_departments = db.session.query(Employee.department).distinct().all()
        existing_departments = [dept[0] for dept in existing_departments if dept[0]]
        
        if department_name in existing_departments:
            flash(f'Department "{department_name}" already exists', 'warning')
            return redirect(url_for('index'))
        
        # Create a placeholder employee to establish the department
        placeholder = Employee(
            first_name="Department",
            last_name="Placeholder",
            email=f"{department_name.lower().replace(' ', '.')}@example.com",
            phone="N/A",
            department=department_name,
            position="Department Head",
            hire_date=datetime.now(timezone.utc),
            salary=0,
            current_address="N/A",
            permanent_address="N/A",
            notes="This is a placeholder record to establish the department. You can delete this record after adding real employees to this department."
        )
        
        db.session.add(placeholder)
        db.session.commit()
        
        flash(f'Department "{department_name}" has been added successfully', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_department.html')

@app.route('/search')
@login_required
def search_employees():
    query = request.args.get('query', '')
    if not query:
        return redirect(url_for('index'))
    
    # Search by name or position
    employees = Employee.query.filter(
        db.or_(
            Employee.first_name.ilike(f'%{query}%'),
            Employee.last_name.ilike(f'%{query}%'),
            Employee.position.ilike(f'%{query}%')
        )
    ).all()
    
    return render_template('search_results.html', employees=employees, query=query)

@app.route('/positions')
@login_required
def get_positions():
    query = request.args.get('q', '')
    positions = db.session.query(Employee.position).distinct().filter(
        Employee.position.ilike(f'%{query}%')
    ).all()
    return jsonify([position[0] for position in positions])

@app.route('/add', methods=['GET', 'POST'])
@admin_required
def add_employee():
    # Get all unique departments for the dropdown
    departments = db.session.query(Employee.department).distinct().all()
    departments = [dept[0] for dept in departments]
    
    # Add default departments if none exist
    if not departments:
        departments = [
            "Human Resources", "Information Technology", "Finance", 
            "Marketing", "Operations", "Sales", 
            "Research & Development", "Customer Support"
        ]
    
    if request.method == 'POST':
        employee_id = request.form.get('employee_id', '')
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone = request.form['phone']
        department = request.form['department']
        position = request.form['position']
        hire_date_str = request.form['hire_date']
        current_address = request.form['current_address']
        permanent_address = request.form.get('permanent_address', '')
        salary = request.form.get('salary', 0)
        notes = request.form.get('notes', '')
        
        # Convert string date to datetime object
        hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
        
        # Convert salary to float if provided
        try:
            salary = float(salary) if salary else 0
        except ValueError:
            salary = 0
        
        # Check if email already exists
        existing_employee = Employee.query.filter_by(email=email).first()
        if existing_employee:
            flash('Email already exists!', 'danger')
            return redirect(url_for('add_employee'))
        
        # Check if employee_id already exists (if provided)
        if employee_id:
            existing_employee_id = Employee.query.filter_by(employee_id=employee_id).first()
            if existing_employee_id:
                flash('Employee ID already exists!', 'danger')
                return redirect(url_for('add_employee'))
        
        # Create new employee
        new_employee = Employee(
            employee_id=employee_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            department=department,
            position=position,
            hire_date=hire_date,
            current_address=current_address,
            permanent_address=permanent_address,
            salary=salary,
            notes=notes
        )
        
        # Add to database
        db.session.add(new_employee)
        db.session.commit()
        
        # Process education information if provided
        education_count = int(request.form.get('education_count', 0))
        for i in range(education_count):
            if request.form.get(f'institution_{i}'):
                institution = request.form.get(f'institution_{i}')
                degree = request.form.get(f'degree_{i}')
                field_of_study = request.form.get(f'field_of_study_{i}')
                start_date_str = request.form.get(f'edu_start_date_{i}')
                end_date_str = request.form.get(f'edu_end_date_{i}')
                description = request.form.get(f'edu_description_{i}', '')
                
                # Convert string dates to datetime objects
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                
                education = Education(
                    employee_id=new_employee.id,
                    institution=institution,
                    degree=degree,
                    field_of_study=field_of_study,
                    start_date=start_date,
                    end_date=end_date,
                    description=description
                )
                db.session.add(education)
        
        # Process certification information if provided
        cert_count = int(request.form.get('certification_count', 0))
        for i in range(cert_count):
            if request.form.get(f'cert_name_{i}'):
                name = request.form.get(f'cert_name_{i}')
                issuing_organization = request.form.get(f'issuing_organization_{i}')
                issue_date_str = request.form.get(f'issue_date_{i}')
                expiry_date_str = request.form.get(f'expiry_date_{i}')
                credential_id = request.form.get(f'credential_id_{i}', '')
                credential_url = request.form.get(f'credential_url_{i}', '')
                
                # Convert string dates to datetime objects
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else None
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None
                
                certification = Certification(
                    employee_id=new_employee.id,
                    name=name,
                    issuing_organization=issuing_organization,
                    issue_date=issue_date,
                    expiry_date=expiry_date,
                    credential_id=credential_id,
                    credential_url=credential_url
                )
                db.session.add(certification)
        
        db.session.commit()
        
        flash('Employee added successfully!', 'success')
        return redirect(url_for('index'))
    
    return render_template('add_employee.html', departments=departments)

@app.route('/employee/<int:id>')
@login_required
def employee_details(id):
    employee = Employee.query.get_or_404(id)
    educations = Education.query.filter_by(employee_id=id).all()
    certifications = Certification.query.filter_by(employee_id=id).all()
    return render_template('employee_details.html', employee=employee, educations=educations, certifications=certifications)

@app.route('/employee/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_employee(id):
    employee = Employee.query.get_or_404(id)
    
    # Get all unique departments for the dropdown
    departments = db.session.query(Employee.department).distinct().all()
    departments = [dept[0] for dept in departments]
    
    if request.method == 'POST':
        # Check if employee_id is being changed and if it already exists
        new_employee_id = request.form.get('employee_id', '')
        if new_employee_id and new_employee_id != employee.employee_id:
            existing_employee_id = Employee.query.filter_by(employee_id=new_employee_id).first()
            if existing_employee_id:
                flash('Employee ID already exists!', 'danger')
                return redirect(url_for('edit_employee', id=employee.id))
        
        employee.employee_id = new_employee_id
        employee.first_name = request.form['first_name']
        employee.last_name = request.form['last_name']
        employee.email = request.form['email']
        employee.phone = request.form['phone']
        employee.department = request.form['department']
        employee.position = request.form['position']
        employee.hire_date = datetime.strptime(request.form['hire_date'], '%Y-%m-%d').date()
        employee.current_address = request.form['current_address']
        employee.permanent_address = request.form.get('permanent_address', '')
        
        # Get salary and notes
        salary = request.form.get('salary', 0)
        employee.notes = request.form.get('notes', '')
        
        # Convert salary to float if provided
        try:
            employee.salary = float(salary) if salary else 0
        except ValueError:
            employee.salary = 0
        
        # Update education information
        # First, remove all existing education records for this employee
        Education.query.filter_by(employee_id=employee.id).delete()
        
        # Then add the new education records
        education_count = int(request.form.get('education_count', 0))
        for i in range(education_count):
            if request.form.get(f'institution_{i}'):
                institution = request.form.get(f'institution_{i}')
                degree = request.form.get(f'degree_{i}')
                field_of_study = request.form.get(f'field_of_study_{i}')
                start_date_str = request.form.get(f'edu_start_date_{i}')
                end_date_str = request.form.get(f'edu_end_date_{i}')
                description = request.form.get(f'edu_description_{i}', '')
                
                # Convert string dates to datetime objects
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                
                education = Education(
                    employee_id=employee.id,
                    institution=institution,
                    degree=degree,
                    field_of_study=field_of_study,
                    start_date=start_date,
                    end_date=end_date,
                    description=description
                )
                db.session.add(education)
        
        # Update certification information
        # First, remove all existing certification records for this employee
        Certification.query.filter_by(employee_id=employee.id).delete()
        
        # Then add the new certification records
        cert_count = int(request.form.get('certification_count', 0))
        for i in range(cert_count):
            if request.form.get(f'cert_name_{i}'):
                name = request.form.get(f'cert_name_{i}')
                issuing_organization = request.form.get(f'issuing_organization_{i}')
                issue_date_str = request.form.get(f'issue_date_{i}')
                expiry_date_str = request.form.get(f'expiry_date_{i}')
                credential_id = request.form.get(f'credential_id_{i}', '')
                credential_url = request.form.get(f'credential_url_{i}', '')
                
                # Convert string dates to datetime objects
                issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else None
                expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None
                
                certification = Certification(
                    employee_id=employee.id,
                    name=name,
                    issuing_organization=issuing_organization,
                    issue_date=issue_date,
                    expiry_date=expiry_date,
                    credential_id=credential_id,
                    credential_url=credential_url
                )
                db.session.add(certification)
        
        db.session.commit()
        flash('Employee updated successfully!', 'success')
        return redirect(url_for('employee_details', id=employee.id))
    
    educations = Education.query.filter_by(employee_id=id).all()
    certifications = Certification.query.filter_by(employee_id=id).all()
    return render_template('edit_employee.html', employee=employee, departments=departments, educations=educations, certifications=certifications)

@app.route('/employee/<int:id>/delete', methods=['POST'])
@admin_required
def delete_employee(id):
    employee = Employee.query.get_or_404(id)
    db.session.delete(employee)
    db.session.commit()
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/all-employees')
@login_required
def all_employees():
    employees = Employee.query.all()
    return render_template('all_employees.html', employees=employees)

@app.route('/self-onboarding', methods=['GET', 'POST'])
@login_required
def self_onboarding():
    # Check if user is an employee (not admin)
    if session.get('is_admin', False):
        flash('This page is for employees only', 'warning')
        return redirect(url_for('index'))
    
    # Get the current user
    user = User.query.filter_by(username=session.get('username')).first()
    
    if not user:
        flash('User not found. Please log in again.', 'danger')
        return redirect(url_for('logout'))
    
    # Check if user already has an employee profile
    if user.employee_id:
        employee = db.session.get(Employee, user.employee_id)
        educations = Education.query.filter_by(employee_id=employee.id).all()
        certifications = Certification.query.filter_by(employee_id=employee.id).all()
        documents = Document.query.filter_by(employee_id=employee.id).all()
        
        # Get all unique departments for the dropdown
        departments = db.session.query(Employee.department).distinct().all()
        departments = [dept[0] for dept in departments]
        
        if request.method == 'POST':
            # Update employee information
            employee.employee_id = request.form.get('employee_id', '')
            employee.first_name = request.form['first_name']
            employee.last_name = request.form['last_name']
            employee.email = request.form['email']
            employee.phone = request.form['phone']
            employee.current_address = request.form['current_address']
            employee.permanent_address = request.form.get('permanent_address', '')
            
            # Handle profile picture upload
            if 'profile_picture' in request.files and request.files['profile_picture'].filename:
                profile_pic = request.files['profile_picture']
                if profile_pic and allowed_file(profile_pic.filename, app.config['ALLOWED_IMAGE_EXTENSIONS']):
                    try:
                        # Create employee folder if it doesn't exist
                        employee_folder = os.path.join(app.config['PROFILE_PICTURES_FOLDER'], f"{employee.employee_id}_{employee.first_name}_{employee.last_name}")
                        os.makedirs(employee_folder, exist_ok=True)
                        
                        # Generate unique filename
                        filename = secure_filename(profile_pic.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        file_path = os.path.join(employee_folder, unique_filename)
                        
                        # Save the file in chunks to handle large files
                        profile_pic.save(file_path)
                        
                        # Update employee record with the new profile picture
                        employee.profile_picture = os.path.join(f"{employee.employee_id}_{employee.first_name}_{employee.last_name}", unique_filename)
                    except Exception as e:
                        flash(f'Error uploading profile picture: {str(e)}', 'danger')
            
            # Handle document uploads
            for doc_type in ['certificate', 'experience_letter', 'offer_letter']:
                if doc_type in request.files and request.files[doc_type].filename:
                    doc_file = request.files[doc_type]
                    if doc_file and allowed_file(doc_file.filename, app.config['ALLOWED_DOCUMENT_EXTENSIONS']):
                        try:
                            # Create employee document folder if it doesn't exist
                            employee_folder = os.path.join(app.config['DOCUMENTS_FOLDER'], f"{employee.employee_id}_{employee.first_name}_{employee.last_name}")
                            os.makedirs(employee_folder, exist_ok=True)
                            
                            # Generate unique filename
                            filename = secure_filename(doc_file.filename)
                            unique_filename = f"{doc_type}_{uuid.uuid4().hex}_{filename}"
                            file_path = os.path.join(employee_folder, unique_filename)
                            
                            # Save the file in chunks to handle large files
                            doc_file.save(file_path)
                            
                            # Create document record
                            document = Document(
                                employee_id=employee.id,
                                filename=os.path.join(f"{employee.employee_id}_{employee.first_name}_{employee.last_name}", unique_filename),
                                original_filename=filename,
                                document_type=doc_type
                            )
                            db.session.add(document)
                        except Exception as e:
                            flash(f'Error uploading {doc_type}: {str(e)}', 'danger')
            
            # Update education information
            # First, remove all existing education records for this employee
            Education.query.filter_by(employee_id=employee.id).delete()
            
            # Then add the new education records
            education_count = int(request.form.get('education_count', 0))
            for i in range(education_count):
                if request.form.get(f'institution_{i}'):
                    institution = request.form.get(f'institution_{i}')
                    degree = request.form.get(f'degree_{i}')
                    field_of_study = request.form.get(f'field_of_study_{i}')
                    start_date_str = request.form.get(f'edu_start_date_{i}')
                    end_date_str = request.form.get(f'edu_end_date_{i}')
                    description = request.form.get(f'edu_description_{i}', '')
                    
                    # Convert string dates to datetime objects
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                    
                    education = Education(
                        employee_id=employee.id,
                        institution=institution,
                        degree=degree,
                        field_of_study=field_of_study,
                        start_date=start_date,
                        end_date=end_date,
                        description=description
                    )
                    db.session.add(education)
            
            # Update certification information
            # First, remove all existing certification records for this employee
            Certification.query.filter_by(employee_id=employee.id).delete()
            
            # Then add the new certification records
            cert_count = int(request.form.get('certification_count', 0))
            for i in range(cert_count):
                if request.form.get(f'cert_name_{i}'):
                    name = request.form.get(f'cert_name_{i}')
                    issuing_organization = request.form.get(f'issuing_organization_{i}')
                    issue_date_str = request.form.get(f'issue_date_{i}')
                    expiry_date_str = request.form.get(f'expiry_date_{i}')
                    credential_id = request.form.get(f'credential_id_{i}', '')
                    credential_url = request.form.get(f'credential_url_{i}', '')
                    
                    # Convert string dates to datetime objects
                    issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else None
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None
                    
                    certification = Certification(
                        employee_id=employee.id,
                        name=name,
                        issuing_organization=issuing_organization,
                        issue_date=issue_date,
                        expiry_date=expiry_date,
                        credential_id=credential_id,
                        credential_url=credential_url
                    )
                    db.session.add(certification)
            
            db.session.commit()
            flash('Your profile has been updated successfully!', 'success')
            return redirect(url_for('self_onboarding'))
        
        return render_template('self_onboarding.html', 
                              employee=employee, 
                              departments=departments, 
                              educations=educations, 
                              certifications=certifications,
                              documents=documents)
    else:
        # User doesn't have an employee profile yet, create a basic one
        if request.method == 'POST':
            # Create new employee
            new_employee = Employee(
                employee_id=request.form.get('employee_id', ''),
                first_name=request.form['first_name'],
                last_name=request.form['last_name'],
                email=request.form['email'],
                phone=request.form['phone'],
                department=request.form.get('department', 'Unassigned'),
                position=request.form.get('position', 'New Hire'),
                hire_date=datetime.now(timezone.utc).date(),
                current_address=request.form['current_address'],
                permanent_address=request.form.get('permanent_address', ''),
                salary=0,  # Salary will be set by admin
                notes=''
            )
            
            # Add to database
            db.session.add(new_employee)
            db.session.commit()
            
            # Link employee to user
            user.employee_id = new_employee.id
            db.session.commit()
            
            # Handle profile picture upload
            if 'profile_picture' in request.files and request.files['profile_picture'].filename:
                profile_pic = request.files['profile_picture']
                if profile_pic and allowed_file(profile_pic.filename, app.config['ALLOWED_IMAGE_EXTENSIONS']):
                    try:
                        # Generate unique filename
                        filename = secure_filename(profile_pic.filename)
                        unique_filename = f"{uuid.uuid4().hex}_{filename}"
                        
                        # Check if Google Drive is enabled
                        drive_file_id = None
                        if app.config.get('GOOGLE_DRIVE_ENABLED', False) and drive_helper.is_enabled():
                            # Create or get employee folder in Google Drive
                            employee_folder_name = f"{new_employee.employee_id}_{new_employee.first_name}_{new_employee.last_name}"
                            
                            if not new_employee.drive_folder_id:
                                employee_folder_id = drive_helper.create_folder(
                                    folder_name=employee_folder_name, 
                                    parent_id=drive_helper.root_folder_id
                                )
                                # Update employee record with folder ID
                                new_employee.drive_folder_id = employee_folder_id
                                db.session.commit()
                            else:
                                employee_folder_id = new_employee.drive_folder_id
                            
                            # Upload profile picture to Google Drive
                            # Save file temporarily to disk
                            temp_file_path = os.path.join(app.config['PROFILE_PICTURES_FOLDER'], 'temp', unique_filename)
                            os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
                            profile_pic.save(temp_file_path)
                            
                            # Upload to Google Drive
                            drive_file_id = drive_helper.upload_file(
                                file_path=temp_file_path,
                                file_name=unique_filename,
                                parent_folder_id=employee_folder_id,
                                mime_type=profile_pic.content_type
                            )
                            
                            # Make the file publicly accessible
                            if drive_file_id:
                                drive_helper.make_file_public(drive_file_id)
                            
                            # Remove temporary file
                            try:
                                os.remove(temp_file_path)
                            except:
                                pass
                            
                            # Update employee record with the Drive file ID
                            new_employee.drive_profile_pic_id = drive_file_id
                        
                        # Also save locally as backup
                        employee_folder = os.path.join(app.config['PROFILE_PICTURES_FOLDER'], f"{new_employee.employee_id}_{new_employee.first_name}_{new_employee.last_name}")
                        os.makedirs(employee_folder, exist_ok=True)
                        file_path = os.path.join(employee_folder, unique_filename)
                        profile_pic.save(file_path)
                        
                        # Update employee record with the new profile picture
                        new_employee.profile_picture = os.path.join(f"{new_employee.employee_id}_{new_employee.first_name}_{new_employee.last_name}", unique_filename)
                        db.session.commit()
                    except Exception as e:
                        flash(f'Error uploading profile picture: {str(e)}', 'danger')
            
            # Handle document uploads
            for doc_type in ['certificate', 'experience_letter', 'offer_letter']:
                if doc_type in request.files and request.files[doc_type].filename:
                    doc_file = request.files[doc_type]
                    if doc_file and allowed_file(doc_file.filename, app.config['ALLOWED_DOCUMENT_EXTENSIONS']):
                        try:
                            # Generate unique filename
                            filename = secure_filename(doc_file.filename)
                            unique_filename = f"{doc_type}_{uuid.uuid4().hex}_{filename}"
                            
                            # Check if Google Drive is enabled
                            drive_file_id = None
                            if app.config.get('GOOGLE_DRIVE_ENABLED', False) and drive_helper.is_enabled():
                                # Create employee folder in Google Drive if it doesn't exist
                                employee_folder_name = f"{new_employee.employee_id}_{new_employee.first_name}_{new_employee.last_name}"
                                
                                # Create or get employee folder in Google Drive
                                if not new_employee.drive_folder_id:
                                    employee_folder_id = drive_helper.create_folder(
                                        folder_name=employee_folder_name, 
                                        parent_id=drive_helper.root_folder_id
                                    )
                                    # Update employee record with folder ID
                                    new_employee.drive_folder_id = employee_folder_id
                                    db.session.commit()
                                else:
                                    employee_folder_id = new_employee.drive_folder_id
                                
                                # Upload file to Google Drive
                                # Save file temporarily to disk
                                temp_file_path = os.path.join(app.config['DOCUMENTS_FOLDER'], 'temp', unique_filename)
                                os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
                                doc_file.save(temp_file_path)
                                
                                # Upload to Google Drive
                                drive_file_id = drive_helper.upload_file(
                                    file_path=temp_file_path,
                                    file_name=unique_filename,
                                    parent_folder_id=employee_folder_id,
                                    mime_type=doc_file.content_type
                                )
                                
                                # Make the file publicly accessible
                                if drive_file_id:
                                    drive_helper.make_file_public(drive_file_id)
                                
                                # Remove temporary file
                                try:
                                    os.remove(temp_file_path)
                                except:
                                    pass
                            
                            # Also save locally as backup
                            employee_folder = os.path.join(app.config['DOCUMENTS_FOLDER'], f"{new_employee.employee_id}_{new_employee.first_name}_{new_employee.last_name}")
                            os.makedirs(employee_folder, exist_ok=True)
                            file_path = os.path.join(employee_folder, unique_filename)
                            doc_file.save(file_path)
                            
                            # Create document record
                            document = Document(
                                employee_id=new_employee.id,
                                filename=os.path.join(f"{new_employee.employee_id}_{new_employee.first_name}_{new_employee.last_name}", unique_filename),
                                original_filename=filename,
                                document_type=doc_type,
                                drive_file_id=drive_file_id
                            )
                            db.session.add(document)
                            db.session.commit()
                        except Exception as e:
                            flash(f'Error uploading {doc_type}: {str(e)}', 'danger')
            
            # Process education information if provided
            education_count = int(request.form.get('education_count', 0))
            for i in range(education_count):
                if request.form.get(f'institution_{i}'):
                    institution = request.form.get(f'institution_{i}')
                    degree = request.form.get(f'degree_{i}')
                    field_of_study = request.form.get(f'field_of_study_{i}')
                    start_date_str = request.form.get(f'edu_start_date_{i}')
                    end_date_str = request.form.get(f'edu_end_date_{i}')
                    description = request.form.get(f'edu_description_{i}', '')
                    
                    # Convert string dates to datetime objects
                    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
                    
                    education = Education(
                        employee_id=new_employee.id,
                        institution=institution,
                        degree=degree,
                        field_of_study=field_of_study,
                        start_date=start_date,
                        end_date=end_date,
                        description=description
                    )
                    db.session.add(education)
            
            # Process certification information if provided
            cert_count = int(request.form.get('certification_count', 0))
            for i in range(cert_count):
                if request.form.get(f'cert_name_{i}'):
                    name = request.form.get(f'cert_name_{i}')
                    issuing_organization = request.form.get(f'issuing_organization_{i}')
                    issue_date_str = request.form.get(f'issue_date_{i}')
                    expiry_date_str = request.form.get(f'expiry_date_{i}')
                    credential_id = request.form.get(f'credential_id_{i}', '')
                    credential_url = request.form.get(f'credential_url_{i}', '')
                    
                    # Convert string dates to datetime objects
                    issue_date = datetime.strptime(issue_date_str, '%Y-%m-%d').date() if issue_date_str else None
                    expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').date() if expiry_date_str else None
                    
                    certification = Certification(
                        employee_id=new_employee.id,
                        name=name,
                        issuing_organization=issuing_organization,
                        issue_date=issue_date,
                        expiry_date=expiry_date,
                        credential_id=credential_id,
                        credential_url=credential_url
                    )
                    db.session.add(certification)
            
            db.session.commit()
            
            flash('Your profile has been created successfully!', 'success')
            return redirect(url_for('self_onboarding'))
        
        # Get all unique departments for the dropdown
        departments = db.session.query(Employee.department).distinct().all()
        departments = [dept[0] for dept in departments]
        
        # Create a placeholder employee object to pre-fill the employee ID if available
        placeholder_employee = None
        
        # Check if there's an employee with the same employee_id that was used during user creation
        if user and user.employee_code:
            # Find employee by employee_id
            existing_employee = Employee.query.filter_by(employee_id=user.employee_code).first()
            if not existing_employee:
                # Create a placeholder to pre-fill the form
                placeholder_employee = Employee(employee_id=user.employee_code)
        
        return render_template('self_onboarding.html', 
                              employee=placeholder_employee, 
                              departments=departments, 
                              educations=[], 
                              certifications=[],
                              documents=[])

# Route removed to avoid duplicate endpoint

@app.route('/register', methods=['GET', 'POST'])
def register():
    # If user is already logged in, redirect to index
    if 'logged_in' in session:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        
        # Create new user
        new_user = User(username=username, is_admin=False)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# Route to serve uploaded files
@app.route('/uploads/<path:filename>')
@login_required
def uploaded_file(filename):
    # Check if user is authorized to access this file
    user = User.query.filter_by(username=session.get('username')).first()
    
    # Check if it's a Google Drive file ID
    if filename.startswith('drive:'):
        file_id = filename.replace('drive:', '')
        if app.config.get('GOOGLE_DRIVE_ENABLED', False) and drive_helper and drive_helper.is_enabled():
            # Admin can access any file
            if session.get('is_admin', False):
                # Instead of redirecting, render a page with an iframe to view the file
                return render_template('view_drive_file.html', 
                                      file_url=drive_helper.get_file_url(file_id),
                                      download_url=drive_helper.get_download_url(file_id))
            
            # Regular user can only access their own files
            if user and user.employee_id:
                employee = db.session.get(Employee, user.employee_id)
                if employee and employee.drive_folder_id:
                    # Check if file is in user's folder
                    if drive_helper.is_file_in_folder(file_id, employee.drive_folder_id):
                        # Instead of redirecting, render a page with an iframe to view the file
                        return render_template('view_drive_file.html', 
                                              file_url=drive_helper.get_file_url(file_id),
                                              download_url=drive_helper.get_download_url(file_id))
            
            # If not authorized
            flash('You are not authorized to access this file', 'danger')
            return redirect(url_for('index'))
        else:
            flash('Google Drive integration is not enabled', 'danger')
            return redirect(url_for('index'))
    
    # Handle local files
    # Determine if it's a profile picture or a document
    if filename.startswith('profile_pictures/'):
        # Remove the 'profile_pictures/' prefix
        file_path = filename[len('profile_pictures/'):]
        upload_path = app.config['PROFILE_PICTURES_FOLDER']
        
        # Handle backslashes in the path
        file_path = file_path.replace('\\', '/')
        
        # Extract the actual filename from the path
        if '/' in file_path:
            parts = file_path.split('/')
            folder_name = parts[0]  # First part is the folder
            filename = parts[-1]    # Last part is the filename
            upload_path = os.path.join(upload_path, folder_name)
        else:
            filename = file_path
    elif filename.startswith('documents/'):
        # Remove the 'documents/' prefix
        file_path = filename[len('documents/'):]
        upload_path = app.config['DOCUMENTS_FOLDER']
        
        # Handle backslashes in the path
        file_path = file_path.replace('\\', '/')
        
        # Extract the actual filename from the path
        if '/' in file_path:
            parts = file_path.split('/')
            folder_name = parts[0]  # First part is the folder
            filename = parts[-1]    # Last part is the filename
            upload_path = os.path.join(upload_path, folder_name)
        else:
            filename = file_path
    else:
        # If no prefix, try to determine from the path
        if '/' in filename:
            parts = filename.split('/')
            if parts[0] == 'documents':
                upload_path = app.config['DOCUMENTS_FOLDER']
                folder_name = parts[1] if len(parts) > 2 else ''
                filename = parts[-1]
                if folder_name:
                    upload_path = os.path.join(upload_path, folder_name)
            elif parts[0] == 'profile_pictures':
                upload_path = app.config['PROFILE_PICTURES_FOLDER']
                folder_name = parts[1] if len(parts) > 2 else ''
                filename = parts[-1]
                if folder_name:
                    upload_path = os.path.join(upload_path, folder_name)
            else:
                # Default to documents folder
                upload_path = app.config['DOCUMENTS_FOLDER']
                filename = parts[-1]
        else:
            # Default to documents folder
            upload_path = app.config['DOCUMENTS_FOLDER']
            
    # Log the path for debugging
    app.logger.info(f"Accessing file: {os.path.join(upload_path, filename)}")

    # Admin can access any file
    if session.get('is_admin', False):
        return send_from_directory(upload_path, filename)
    
    # Regular user can only access their own files
    if user and user.employee_id:
        employee = db.session.get(Employee, user.employee_id)
        
        # Check if the file belongs to this employee
        if employee:
            employee_folder_prefix = f"{employee.employee_id}_{employee.first_name}_{employee.last_name}"
            if os.path.basename(upload_path).startswith(employee_folder_prefix) or filename.startswith(employee_folder_prefix):
                return send_from_directory(upload_path, filename)
    
    # If not authorized
    flash('You are not authorized to access this file', 'danger')
    return redirect(url_for('index'))

# Route to delete a document
@app.route('/delete-document/<int:document_id>', methods=['POST'])
@login_required
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    # Check if user is authorized to delete this document
    user = User.query.filter_by(username=session.get('username')).first()
    
    # Admin can delete any document
    is_authorized = session.get('is_admin', False)
    
    # Regular user can only delete their own documents
    if not is_authorized and user and user.employee_id:
        is_authorized = document.employee_id == user.employee_id
    
    if not is_authorized:
        flash('You are not authorized to delete this document', 'danger')
        return redirect(url_for('index'))
    
    # Delete the file from the filesystem
    file_path = os.path.join(app.config['DOCUMENTS_FOLDER'], document.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete the document record
    db.session.delete(document)
    db.session.commit()
    
    flash('Document deleted successfully', 'success')
    return redirect(url_for('self_onboarding'))

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=12000, help='Port to run the server on')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the server on')
    args = parser.parse_args()
    
    app.run(host=args.host, port=args.port, debug=True)