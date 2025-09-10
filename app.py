from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash, abort
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api
from datetime import timedelta

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Security configurations
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True  # Requires HTTPS in production
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Configure Cloudinary using environment variables
cloudinary.config(
    cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME', 'dmcbgugli'),
    api_key=os.environ.get('CLOUDINARY_API_KEY', '961589438572493'),
    api_secret=os.environ.get('CLOUDINARY_API_SECRET', 'g0qQo31SP3vGgwtY8M3enNdiNV8'),
    secure=True
)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max file size
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'adminpass123')

# Allowed file extensions and MIME types
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
ALLOWED_MIME_TYPES = {'image/jpeg', 'image/png', 'image/gif', 'application/pdf'}

# Ensure uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# In-memory data storage
staff_data = []
edit_requests = []


# Authentication decorators
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_verified'):
            flash('Admin access required')
            return redirect(url_for('admin'))
        return f(*args, **kwargs)

    return decorated_function


# File validation function
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        if email:  # In a real app, you would verify credentials against a database
            session['user'] = email
            session.permanent = True
            return redirect(url_for('upload'))
        else:
            flash('Please enter a valid email')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out')
    return redirect(url_for('login'))


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        role = request.form.get('role', '').strip()
        file = request.files.get('file')

        # Validate input
        if not name or not role:
            flash('Name and role are required')
            return redirect(url_for('upload'))

        file_url = ""
        filename = ""

        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Invalid file type. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS))
                return redirect(url_for('upload'))

            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            try:
                upload_result = cloudinary.uploader.upload(file, resource_type="auto")
                file_url = upload_result['secure_url']
            except Exception as e:
                flash(f"Cloud upload failed: {str(e)}. File saved locally.")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                file_url = url_for('uploaded_file', filename=filename)

        staff_data.append({
            'id': str(uuid.uuid4()),
            'name': name,
            'role': role,
            'file_url': file_url,
            'file_name': filename,
            'uploaded_by': session['user']
        })

        flash('Staff member added successfully')
        return redirect(url_for('upload'))

    return render_template('upload.html', staff=staff_data, user=session['user'], edit_requests=edit_requests)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        abort(404)


@app.route('/request_edit/<staff_id>', methods=['POST'])
@login_required
def request_edit(staff_id):
    staff = next((s for s in staff_data if s['id'] == staff_id), None)
    if not staff:
        flash('Staff member not found')
        return redirect(url_for('upload'))

    # Check if user owns this record
    if staff['uploaded_by'] != session['user']:
        flash('You can only request edits for your own records')
        return redirect(url_for('upload'))

    if staff_id not in edit_requests:
        edit_requests.append(staff_id)
        flash('Edit request submitted for admin approval')
    else:
        flash('Edit request already pending')

    return redirect(url_for('upload'))


@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        password = request.form.get('adminpass', '')
        if password == ADMIN_PASSWORD:
            session['admin_verified'] = True
            return redirect(url_for('admin'))
        else:
            flash('Access Denied: Incorrect Password')
            return redirect(url_for('admin'))

    if session.get('admin_verified'):
        return render_template('admin.html', staff=staff_data, edit_requests=edit_requests)
    return render_template('admin_login.html')


@app.route('/approve_edit/<staff_id>', methods=['POST'])
@admin_required
def approve_edit(staff_id):
    return redirect(url_for('edit', staff_id=staff_id))


@app.route('/edit/<staff_id>', methods=['GET', 'POST'])
@admin_required
def edit(staff_id):
    staff = next((s for s in staff_data if s['id'] == staff_id), None)
    if not staff:
        flash('Staff not found')
        return redirect(url_for('admin'))

    if request.method == 'POST':
        staff['name'] = request.form.get('name', '').strip()
        staff['role'] = request.form.get('role', '').strip()
        file = request.files.get('file')

        if not staff['name'] or not staff['role']:
            flash('Name and role are required')
            return render_template('edit.html', staff=staff)

        if file and file.filename:
            if not allowed_file(file.filename):
                flash('Invalid file type. Allowed types: ' + ', '.join(ALLOWED_EXTENSIONS))
                return render_template('edit.html', staff=staff)

            filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
            try:
                upload_result = cloudinary.uploader.upload(file, resource_type="auto")
                staff['file_url'] = upload_result['secure_url']
                staff['file_name'] = filename
            except Exception as e:
                flash(f"Upload to Cloudinary failed: {str(e)}. Saving locally.")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                staff['file_url'] = url_for('uploaded_file', filename=filename)
                staff['file_name'] = filename

        if staff_id in edit_requests:
            edit_requests.remove(staff_id)

        flash('Staff member updated successfully')
        return redirect(url_for('admin'))

    return render_template('edit.html', staff=staff)


@app.route('/delete/<staff_id>', methods=['POST'])
@admin_required
def delete(staff_id):
    global staff_data
    staff_data = [s for s in staff_data if s['id'] != staff_id]

    # Remove any pending edit requests for this staff member
    if staff_id in edit_requests:
        edit_requests.remove(staff_id)

    flash('Staff member deleted successfully')
    return redirect(url_for('admin'))


@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500


if __name__ == '__main__':
    # Use environment variable to determine debug mode
    debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(debug=debug_mode)