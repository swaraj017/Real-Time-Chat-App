from flask import Flask, render_template, request, redirect, url_for
from flask_socketio import SocketIO, join_room, leave_room, emit
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from pymongo.errors import DuplicateKeyError
from db import get_user, save_user, save_room, get_room_members, save_message, get_messages, delete_room

app = Flask(__name__)
app.secret_key = "My Chatt App"

socketio = SocketIO(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@app.route('/')
def index():
    return render_template("index.html")  # Corrected template filename

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    message = ""
    if request.method == "POST":
        username = request.form.get('username')
        password_input = request.form.get('password')
        user = get_user(username)
        if user and user.check_password(password_input):
            login_user(user)
            return redirect(url_for("index"))
        else:
            message = "Failed to Login"
    return render_template('login.html', message=message)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    message = ''
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        try:
            save_user(username, email, password)
            return redirect(url_for('login'))
        except DuplicateKeyError:
            message = "User already exists!"
    return render_template('signup.html', message=message)

@app.route('/chatt')
@login_required
def chat():
    username = request.args.get('username')
    room = request.args.get('room')
    if username and room:
        # Save user to room if not already present
        save_room(room, username)

        # Get room members
        members = get_room_members(room)

        # Get existing messages
        messages = get_messages(room)

        # Render the chat page with the updated list of members and existing messages
        return render_template("chat.html", username=username, room=room, members=members, messages=messages)
    else:
        # Handle the case where username or room is not provided
        return redirect(url_for("index"))

@app.route('/delete_room/<room>', methods=['POST'])
@login_required
def delete_chat(room):
    # Check if the user is authorized to delete the room (implement your own logic here)
    if current_user.is_authenticated:
        delete_room(room)
        return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))

@socketio.on('join_room')
def handle_join_room_event(data):
    username = data['username']
    room = data['room']

    app.logger.info("{} has joined the room {}".format(username, room))
    join_room(room)
    socketio.emit('join_room_announcement', data, room=room)

@socketio.on('leave_room')
def handle_leave_room_event(data):
    username = data['username']
    room = data['room']

    app.logger.info("{} has left the room {}".format(username, room))
    leave_room(room)
    socketio.emit('leave_room_announcement', data, room=room)

@socketio.on('send_message')
def handle_send_message(data):
    room_id = data['room']
    username = data['username']
    message = data['message']

    # Save message to database
    save_message(room_id, username, message)

    app.logger.info(f"{username} has sent a message to room {room_id}")
    emit('receive_mess', {
        'username': username,
        'message': message
    }, room=room_id)

@login_manager.user_loader
def load_user(username):
    return get_user(username)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)


