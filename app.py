from flask import Flask, render_template, request, redirect, session, send_from_directory
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
from datetime import timedelta
app.permanent_session_lifetime = timedelta(minutes=30)
app.secret_key = 'your_secret_key_here'

# Define allowed users and passwords
USERS = {
    "obireka@portal.com": "staff123",
    "rocxam@portal.com": "adminpass123"
}

# File upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'mp4', 'avi'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# In-memory staff storage
staff_data = []
edit_requests = []


# Helper function to check file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Home route: login page
@app.route('/')
def home():
    return render_template('login.html')

# Login route
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    if email in USERS and USERS[email] == password:
        session['user'] = email
        return redirect('/upload')
    else:
        return "Invalid email or password."

# Upload page (staff only)
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            staff_data.append({
                'id': len(staff_data),
                'name': name,
                'role': role,
                'file': filename,
                'uploaded_by': session['user']
            })

        else:
            return "Invalid file type"

    return render_template('upload.html', staff=staff_data)

#request_edit/<int:staff_id>
@app.route('/request_edit/<int:staff_id>', methods=['POST'])
def request_edit(staff_id):
    if 'user' not in session:
        return redirect('/')

    # Only allow requesting edit for your own uploads
    staff = next((s for s in staff_data if s['id'] == staff_id), None)
    if staff and staff['uploaded_by'] == session['user']:
        if staff_id not in edit_requests:
            edit_requests.append(staff_id)
    return redirect('/upload')

#approve_edit/<int:staff_id>
@app.route('/approve_edit/<int:staff_id>', methods=['POST'])
def approve_edit(staff_id):
    admin_pass = request.form['adminpass']
    if session.get('user') == "rocxam@portal.com" and admin_pass == "adminpass123":
        return redirect(f'/edit/{staff_id}')
    return "Access denied."




# Admin panel login page + password check
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        admin_pass = request.form['adminpass']
        if session.get('user') == "rocxam@portal.com" and admin_pass == "adminpass123":
            return render_template('admin.html', staff=staff_data)
        else:
            return "Access denied."
    return render_template('admin_login.html')
@app.route('/delete/<int:staff_id>', methods=['POST'])
def delete_staff(staff_id):
    if session.get('user') != 'rocxam@portal.com':
        return "Only admin can delete."

    global staff_data
    staff_data = [s for s in staff_data if s['id'] != staff_id]
    return redirect('/admin')


# File serving route
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


    # Prevent duplicate requests
    if staff_id not in edit_requests:
        edit_requests.append(staff_id)
    return redirect('/upload')
#edit/<int:staff_id>
@app.route('/edit/<int:staff_id>', methods=['GET', 'POST'])
def edit_staff(staff_id):
    staff = next((s for s in staff_data if s['id'] == staff_id), None)
    if not staff:
        return "Staff not found."

    # Only allow uploader to edit if approved
    if staff_id not in edit_requests or session.get('user') != staff['uploaded_by']:
        return "Not authorized."

    if request.method == 'POST':
        staff['name'] = request.form['name']
        staff['role'] = request.form['role']

        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            staff['file'] = filename

        # Remove request after editing
        edit_requests.remove(staff_id)
        return redirect('/upload')

    return render_template('edit.html', staff=staff)


# Run the app
if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
