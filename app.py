from flask import Flask, render_template, request, redirect, url_for, send_from_directory, session, flash
from werkzeug.utils import secure_filename
import os
import uuid
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Configure Cloudinary
cloudinary.config(
    cloud_name='dmcbgugli',
    api_key='961589438572493',
    api_secret='g0qQo31SP3vGgwtY8M3enNdiNV8',
    secure=True
)

app = Flask(__name__)
app.secret_key = 'super-secret-key'

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ADMIN_PASSWORD = 'adminpass123'

# Ensure uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# In-memory data storage
staff_data = []
edit_requests = []

@app.route('/')
def index():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['user'] = request.form['email']
        return redirect('/upload')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        file = request.files['file']
        file_url = ""
        filename = ""

        if file and file.filename:
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

        return redirect('/upload')

    return render_template('upload.html', staff=staff_data, user=session['user'], edit_requests=edit_requests)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return "File not found", 404

@app.route('/request_edit/<staff_id>', methods=['POST'])
def request_edit(staff_id):
    if staff_id not in edit_requests:
        edit_requests.append(staff_id)
    return redirect('/upload')

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form['adminpass'] == ADMIN_PASSWORD:
            session['admin_verified'] = True
            return redirect('/admin')
        else:
            flash('Access Denied: Incorrect Password')
            return redirect('/admin')

    if session.get('admin_verified'):
        return render_template('admin.html', staff=staff_data, edit_requests=edit_requests)
    return render_template('admin_login.html')

@app.route('/approve_edit/<staff_id>', methods=['POST'])
def approve_edit(staff_id):
    if request.form['adminpass'] == ADMIN_PASSWORD:
        return redirect(f'/edit/{staff_id}')
    flash("Access Denied")
    return redirect('/admin')

@app.route('/edit/<staff_id>', methods=['GET', 'POST'])
def edit(staff_id):
    staff = next((s for s in staff_data if s['id'] == staff_id), None)
    if not staff:
        return "Staff not found"

    if request.method == 'POST':
        staff['name'] = request.form['name']
        staff['role'] = request.form['role']
        file = request.files['file']

        if file and file.filename:
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

        return redirect('/admin')

    return render_template('edit.html', staff=staff)

@app.route('/delete/<staff_id>', methods=['POST'])
def delete(staff_id):
    global staff_data
    staff_data = [s for s in staff_data if s['id'] != staff_id]
    return redirect('/admin')
