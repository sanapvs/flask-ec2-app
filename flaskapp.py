"""Tally: a Flask + SQLite3 web app for the AWS EC2 assignment.

Pages
  /            registration form: username, password, personal details, .txt upload
  /profile     shows the saved details, the file's word count and a download button
  /login       re-login with username + password to get back to the profile
  /upload      upload a (different) .txt file from the profile page
  /download    download the stored file
  /logout      end the session
"""
import os
import re
import secrets
import sqlite3

from flask import (Flask, flash, g, redirect, render_template, request,
                   send_from_directory, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

# Under Apache/mod_wsgi the working directory is NOT this folder, so every
# path is built from this file's location instead of being relative.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'users.db')
SCHEMA = os.path.join(BASE_DIR, 'schema.sql')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
SECRET_KEY_FILE = os.path.join(BASE_DIR, 'secret_key')

USERNAME_RE = re.compile(r'^[A-Za-z0-9_]{3,30}$')
MIN_PASSWORD_LENGTH = 6
MAX_UPLOAD_MB = 2

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024


def load_secret_key():
    """Key that signs the login cookie. Created once, then reused across restarts."""
    if not os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, 'w') as f:
            f.write(secrets.token_hex(32))
    with open(SECRET_KEY_FILE) as f:
        return f.read().strip()


app.secret_key = load_secret_key()


# ------------------------------------------------------------------ database

def init_db():
    """Create the uploads folder and the users table if they don't exist yet."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    with open(SCHEMA) as f:
        conn.executescript(f.read())
    conn.close()


def get_db():
    """One connection per request; rows can be read by column name (user['email'])."""
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def find_user(username):
    return get_db().execute(
        'SELECT * FROM users WHERE username = ?', (username,)).fetchone()


def current_user():
    """Row of the logged-in user, or None."""
    username = session.get('username')
    return find_user(username) if username else None


init_db()


# --------------------------------------------------------------- file upload

def is_txt(filename):
    return filename.lower().endswith('.txt')


def read_upload(file):
    """Return (display name, raw bytes, word count) for an uploaded text file."""
    name = os.path.basename(file.filename.replace('\\', '/'))
    data = file.read()
    words = len(data.decode('utf-8', errors='replace').split())  # same rule as `wc -w`
    return name, data, words


def save_file(stored_name, data):
    with open(os.path.join(UPLOAD_FOLDER, stored_name), 'wb') as f:
        f.write(data)


# --------------------------------------------------------------------- pages

@app.route('/')
def index():
    return render_template('register.html', form={})


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return redirect(url_for('index'))

    form = request.form
    username = form.get('username', '').strip()
    password = form.get('password', '')
    confirm = form.get('confirm', '')
    details = {field: form.get(field, '').strip()
               for field in ('firstname', 'lastname', 'email', 'address')}
    upload = request.files.get('textfile')
    has_file = upload is not None and upload.filename != ''

    errors = []
    if not USERNAME_RE.match(username):
        errors.append('Username must be 3-30 letters, numbers or underscores.')
    elif find_user(username):
        errors.append(f'The username "{username}" is taken. Choose another one.')
    if len(password) < MIN_PASSWORD_LENGTH:
        errors.append(f'Password must be at least {MIN_PASSWORD_LENGTH} characters.')
    elif password != confirm:
        errors.append("The two passwords don't match.")
    if not all(details.values()):
        errors.append('Fill in your first name, last name, email and address.')
    elif '@' not in details['email']:
        errors.append('Enter a valid email address.')
    if has_file and not is_txt(upload.filename):
        errors.append('The file must be a .txt text file.')

    if errors:
        for message in errors:
            flash(message, 'error')
        return render_template('register.html', form=form), 400

    file_name = stored_name = word_count = data = None
    if has_file:
        file_name, data, word_count = read_upload(upload)
        stored_name = f'{username}.txt'  # safe: usernames are letters/digits/_ only

    db = get_db()
    try:
        db.execute(
            '''INSERT INTO users (username, password, firstname, lastname, email, address,
                                  filename, stored_filename, word_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (username, generate_password_hash(password),
             details['firstname'], details['lastname'], details['email'], details['address'],
             file_name, stored_name, word_count))
        db.commit()
    except sqlite3.IntegrityError:  # someone grabbed the username a moment ago
        flash(f'The username "{username}" is taken. Choose another one.', 'error')
        return render_template('register.html', form=form), 400

    if data is not None:
        save_file(stored_name, data)

    session.clear()
    session['username'] = username
    flash('Account created.', 'success')
    return redirect(url_for('profile'))


@app.route('/profile')
def profile():
    user = current_user()
    if user is None:
        flash('Log in to see your profile.', 'info')
        return redirect(url_for('login'))
    return render_template('profile.html', user=user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    username = ''
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        user = find_user(username)
        if user and check_password_hash(user['password'], request.form.get('password', '')):
            session.clear()
            session['username'] = user['username']
            flash(f"Welcome back, {user['firstname']}.", 'success')
            return redirect(url_for('profile'))
        flash('Username or password is incorrect.', 'error')
    return render_template('login.html', username=username)


@app.route('/upload', methods=['POST'])
def upload():
    user = current_user()
    if user is None:
        return redirect(url_for('login'))

    file = request.files.get('textfile')
    if file is None or file.filename == '':
        flash('Choose a .txt file to upload.', 'error')
    elif not is_txt(file.filename):
        flash('The file must be a .txt text file.', 'error')
    else:
        name, data, words = read_upload(file)
        stored_name = f"{user['username']}.txt"
        save_file(stored_name, data)
        db = get_db()
        db.execute('UPDATE users SET filename = ?, stored_filename = ?, word_count = ? '
                   'WHERE id = ?', (name, stored_name, words, user['id']))
        db.commit()
        flash(f'Uploaded {name}.', 'success')
    return redirect(url_for('profile'))


@app.route('/download')
def download():
    user = current_user()
    if user is None:
        return redirect(url_for('login'))
    if not user['stored_filename']:
        flash('Upload a file first.', 'info')
        return redirect(url_for('profile'))
    return send_from_directory(UPLOAD_FOLDER, user['stored_filename'],
                               as_attachment=True, download_name=user['filename'])


@app.route('/logout')
def logout():
    session.clear()
    flash('You are logged out.', 'info')
    return redirect(url_for('login'))


@app.errorhandler(413)
def file_too_large(error):
    flash(f'That file is larger than {MAX_UPLOAD_MB} MB. Choose a smaller .txt file.', 'error')
    return redirect(request.referrer or url_for('index'))


if __name__ == '__main__':  # local testing only; on EC2, Apache runs the app
    app.run(debug=True)
