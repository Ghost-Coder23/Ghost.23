from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this to a random secret key in production

UPLOAD_FOLDER = 'flask_mini_web_os/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Simple user store for demo (username -> hashed password)
users = {
    'admin': generate_password_hash('admin123')
}

@app.route('/')
def splash():
    # Render splash page that redirects to login after delay
    return render_template('splash.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username in users and check_password_hash(users[username], password):
            session['username'] = username
            return redirect(url_for('main'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

import time
from flask import jsonify

BASE_DIRS = ['videos', 'documents', 'downloads', 'pictures', 'trash', 'music']

# Ensure base directories exist
for d in BASE_DIRS:
    path = os.path.join(UPLOAD_FOLDER, d)
    if not os.path.exists(path):
        os.makedirs(path)

@app.route('/main', methods=['GET', 'POST'])
@login_required
def main():
    current_dir = request.args.get('dir', 'desktop')
    # Ensure current_dir is valid or default
    if current_dir != 'root' and current_dir not in BASE_DIRS and current_dir != 'recents' and current_dir != 'desktop':
        flash('Invalid directory')
        return redirect(url_for('main'))

    if request.method == 'POST':
        # Handle file upload
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            save_dir = UPLOAD_FOLDER if current_dir == 'root' else os.path.join(UPLOAD_FOLDER, current_dir)
            os.makedirs(save_dir, exist_ok=True)
            file.save(os.path.join(save_dir, filename))
            flash(f'File {filename} uploaded successfully to {current_dir}')

    # List files for display
    files = []
    if current_dir == 'root':
        # Show base directories and files in root
        dirs = BASE_DIRS
        root_files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f))]
        files = [{'name': d, 'type': 'dir'} for d in dirs] + [{'name': f, 'type': 'file'} for f in root_files]
    elif current_dir == 'recents':
        # Get recent files from all base dirs sorted by modification time descending
        recent_files = []
        for d in BASE_DIRS:
            dir_path = os.path.join(UPLOAD_FOLDER, d)
            if os.path.exists(dir_path):
                for f in os.listdir(dir_path):
                    f_path = os.path.join(dir_path, f)
                    if os.path.isfile(f_path):
                        modtime = os.path.getmtime(f_path)
                        recent_files.append({'name': f, 'type': 'file', 'dir': d, 'modtime': modtime})
        # Sort recents by modtime descending, limit to 20
        recent_files = sorted(recent_files, key=lambda x: x['modtime'], reverse=True)[:20]
        files = recent_files
    else:
        dir_path = os.path.join(UPLOAD_FOLDER, current_dir)
        if os.path.exists(dir_path):
            files = [{'name': f, 'type': 'file'} for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))]
        else:
            flash(f'Directory {current_dir} not found')
            files = []

    theme = session.get('theme', 'default')
    return render_template('main.html', files=files, current_dir=current_dir, theme=theme)

@app.route('/uploads/<dir>/<filename>')
@login_required
def uploaded_file(dir, filename):
    if dir not in BASE_DIRS and dir != 'root':
        flash('Invalid directory')
        return redirect(url_for('main'))
    if dir == 'root':
        directory = UPLOAD_FOLDER
    else:
        directory = os.path.join(UPLOAD_FOLDER, dir)
    return send_from_directory(directory, filename)

@app.route('/delete/<dir>/<filename>', methods=['POST'])
@login_required
def delete_file(dir, filename):
    if dir not in BASE_DIRS and dir != 'root':
        flash('Invalid directory')
        return redirect(url_for('main'))
    src_path = os.path.join(UPLOAD_FOLDER if dir == 'root' else os.path.join(UPLOAD_FOLDER, dir), filename)
    trash_dir = os.path.join(UPLOAD_FOLDER, 'trash')
    os.makedirs(trash_dir, exist_ok=True)
    if os.path.exists(src_path):
        try:
            os.rename(src_path, os.path.join(trash_dir, filename))
            flash(f'Moved {filename} to trash')
        except Exception as e:
            flash(f'Error moving file to trash: {e}')
    else:
        flash(f'File {filename} not found')
    return redirect(url_for('main', dir=dir))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        # Save all settings to session
        settings_data = {
            'theme': request.form.get('theme', 'kali'),
            'background': request.form.get('background', 'default'),
            'clock_format': request.form.get('clock_format', '24'),
            'default_view': request.form.get('default_view', 'list'),
            'show_hidden': request.form.get('show_hidden') == 'true',
            'upload_limit': int(request.form.get('upload_limit', 10)),
            'auto_save': request.form.get('auto_save') == 'true',
            'sound_effects': request.form.get('sound_effects') == 'true',
            'animation_speed': request.form.get('animation_speed', 'normal'),
            'session_timeout': int(request.form.get('session_timeout', 60)),
            'remember_login': request.form.get('remember_login') == 'true',
            'language': request.form.get('language', 'en'),
            'timezone': request.form.get('timezone', 'UTC')
        }

        # Store settings in session
        for key, value in settings_data.items():
            session[key] = value

        flash('Settings saved successfully!')
        return redirect(url_for('settings'))

    # Load current settings for display
    current_settings = {
        'theme': session.get('theme', 'kali'),
        'background': session.get('background', 'default'),
        'clock_format': session.get('clock_format', '24'),
        'default_view': session.get('default_view', 'list'),
        'show_hidden': session.get('show_hidden', False),
        'upload_limit': session.get('upload_limit', 10),
        'auto_save': session.get('auto_save', True),
        'sound_effects': session.get('sound_effects', False),
        'animation_speed': session.get('animation_speed', 'normal'),
        'session_timeout': session.get('session_timeout', 60),
        'remember_login': session.get('remember_login', False),
        'language': session.get('language', 'en'),
        'timezone': session.get('timezone', 'UTC')
    }

    return render_template('settings.html', settings=current_settings)

# Removed duplicate route upload route without directory parameter
# The new route '/uploads/<dir>/<filename>' is the intended one
# So, we delete this old route to fix view function mapping conflict

# @app.route('/uploads/<filename>')
# @login_required
# def uploaded_file(filename):
#     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Removed old delete route without directory parameter to prevent endpoint conflict
# The route below implements delete with directory param and supersedes this

# @app.route('/delete/<filename>', methods=['POST'])
# @login_required
# def delete_file(filename):
#     pass
    if os.path.exists(file_path):
        os.remove(file_path)
        flash(f'File {filename} deleted')
    else:
        flash(f'File {filename} not found')
    return redirect(url_for('main'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)
