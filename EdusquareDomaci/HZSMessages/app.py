from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room, leave_room
import sqlite3
from datetime import datetime



dbPath = '/home/fanste/Desktop/MatejaHZS/HackatonZadatak/HZSCrusaders/db.sqlite3'

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tajni_kljuc_123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dbPath'
app.config['SQLALCHEMY_BINDS'] = {
    'chat': 'sqlite:///chat.db'
}

db = SQLAlchemy(app)
socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Model za poruke
class Message(db.Model):
    __bind_key__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer)
    group_id = db.Column(db.Integer)
    channel = db.Column(db.String(20), default='general')

class Channel(db.Model):
    __bind_key__ = 'chat'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    course_id = db.Column(db.Integer)
    channel_type = db.Column(db.String(20))  # 'general' ili 'help'

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auth_user WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return User(user[0]) if user else None

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@app.route('/')
@login_required
def index():
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT c.id, c.title 
        FROM myapp_course c
        JOIN myapp_courseenrollment e ON c.id = e.course_id
        WHERE e.user_id = ?
    """, (current_user.id,))
    courses = cursor.fetchall()
    conn.close()
    return render_template('index.html', courses=courses)

@app.route('/chat/<int:group_id>')
@app.route('/chat/<int:group_id>/<channel>')
@login_required
def chat(group_id, channel='general'):
    # Get course title
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()
    cursor.execute("SELECT title FROM myapp_course WHERE id = ?", (group_id,))
    course = cursor.fetchone()
    conn.close()
    
    messages = Message.query.filter_by(
        group_id=group_id,
        channel=channel
    ).order_by(Message.timestamp).all()
    
    return render_template('chat.html',
                         messages=messages,
                         group_id=group_id,
                         current_channel=channel,
                         course_title=course[0] if course else "Kurs")

@socketio.on('send_message')
def handle_message(data):
    # Get user info from Django database
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name FROM auth_user WHERE id = ?", (current_user.id,))
    user = cursor.fetchone()
    conn.close()
    
    sender_name = f"{user[0]} {user[1]}"
    
    message = Message(
        content=data['message'],
        user_id=current_user.id,
        group_id=data['group_id']
    )
    db.session.add(message)
    db.session.commit()
    
    emit('receive_message', {
        'message': message.content,
        'user_id': message.user_id,
        'sender_name': sender_name,
        'timestamp': message.timestamp.strftime('%H:%M:%S')
    }, room=str(data['group_id']))

@socketio.on('join')
def on_join(data):
    room = str(data['group_id'])
    join_room(room)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect(dbPath)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM auth_user WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            # Configure Django settings
            from django.conf import settings
            if not settings.configured:
                settings.configure(
                    PASSWORD_HASHERS=[
                        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
                        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
                    ],
                )
            
            from django.contrib.auth.hashers import check_password
            
            if check_password(password, user[1]):  # user[1] je hash lozinke
                user_obj = User(user[0])
                login_user(user_obj)
                return redirect(url_for('index'))
        
        flash('Pogrešan email ili lozinka')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def get_user_name(user_id):
    conn = sqlite3.connect(dbPath)
    cursor = conn.cursor()
    cursor.execute("SELECT first_name, last_name FROM auth_user WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return f"{user[0]} {user[1]}" if user else "Nepoznat korisnik"

# Dodajte ovu funkciju u Jinja2 environment
app.jinja_env.globals.update(get_user_name=get_user_name)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
