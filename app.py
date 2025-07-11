from flask import Flask, render_template, request, redirect, session, send_from_directory
import os
from werkzeug.utils import secure_filename
from datetime import timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'
app.permanent_session_lifetime = timedelta(minutes=30)

# Define allowed users and passwords
USERS = {
    "obireka@portal.com": {"password": "staff123", "role": "staff"},
    "rocxam@portal.com": {"password": "adminpass123", "role": "admin"}
}

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'mp4', 'avi'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

staff_data = []
edit_requests = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login')
def show_login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    user = USERS.get(email)
    if user and user['password'] == password:
        session['user'] = email
        session['role'] = user['role']
        return redirect('/upload')
    else:
        return "Invalid email or password."

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

    return render_template('upload.html', staff=staff_data, edit_requests=edit_requests)

@app.route('/request_edit/<int:staff_id>', methods=['POST'])
def request_edit(staff_id):
    if 'user' not in session:
        return redirect('/')
    staff = next((s for s in staff_data if s['id'] == staff_id), None)
    if staff and staff['uploaded_by'] == session['user']:
        if staff_id not in edit_requests:
            edit_requests.append(staff_id)
    return redirect('/admin_login?redirect=admin')

@app.route('/admin_login')
def admin_login_redirect():
    return render_template('admin_login.html', redirect_to=request.args.get('redirect'))

@app.route('/approve_edit/<int:staff_id>', methods=['POST'])
def approve_edit(staff_id):
    admin_pass = request.form['adminpass']
    if session.get('user') == "rocxam@portal.com" and admin_pass == "adminpass123":
        return redirect(f'/edit/{staff_id}')
    return "Access denied."

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        admin_pass = request.form['adminpass']
        if session.get('user') == "rocxam@portal.com" and admin_pass == "adminpass123":
            return render_template('admin.html', staff=staff_data, edit_requests=edit_requests)
        else:
            return "Access denied."
    return render_template('admin_login.html', redirect_to='admin')

@app.route('/delete/<int:staff_id>', methods=['POST'])
def delete_staff(staff_id):
    if session.get('user') != 'rocxam@portal.com':
        return "Only admin can delete."
    global staff_data
    staff_data = [s for s in staff_data if s['id'] != staff_id]
    return redirect('/admin')

@app.route('/edit/<int:staff_id>', methods=['GET', 'POST'])
def edit_staff(staff_id):
    staff = next((s for s in staff_data if s['id'] == staff_id), None)
    if not staff:
        return "Staff not found."

    if session.get('user') != staff['uploaded_by'] and session.get('user') != "rocxam@portal.com":
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
        if staff_id in edit_requests:
            edit_requests.remove(staff_id)
        return redirect('/upload')

    return render_template('edit.html', staff=staff)

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
