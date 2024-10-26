from pymongo import MongoClient, errors
from werkzeug.security import generate_password_hash
from user import User
import hashlib
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

# Connect to MongoDB
client = MongoClient(os.getenv("MONGODB_URI"))

chat_db = client.get_database("ChatDb")

# Collections
users_collection = chat_db.get_collection("users")
roommembers = chat_db.get_collection("roommembers")
messages_collection = chat_db.get_collection("messages")

def save_user(username, email, password):
    password_hash = generate_password_hash(password)
    users_collection.insert_one({'_id': username, 'email': email, 'password': password_hash})

def hash_room_id(room_id):
    if room_id is None:
        raise ValueError("Room ID cannot be None")

    room_id_bytes = room_id.encode('utf-8')
    sha256 = hashlib.sha256()
    sha256.update(room_id_bytes)
    return sha256.hexdigest()

def save_room(room_id, username):
    hashed_id = hash_room_id(room_id)
    existing_member = roommembers.find_one({'roomid': hashed_id, 'username': username})

    if not existing_member:
        try:
            roommembers.insert_one({'roomid': hashed_id, 'username': username})
        except errors.DuplicateKeyError:
            print(f"Duplicate entry error: User '{username}' already exists in the room.")

def get_room_members(room_id):
    hashed_id = hash_room_id(room_id)
    members_cursor = roommembers.find({'roomid': hashed_id})
    members = set(member['username'] for member in members_cursor)
    return list(members)

def save_message(room_id, username, message):
    messages_collection.insert_one({
        'roomid': hash_room_id(room_id),
        'username': username,
        'message': message,
        'timestamp': datetime.utcnow()
    })

def get_messages(room_id):
    hashed_id = hash_room_id(room_id)
    messages_cursor = messages_collection.find({'roomid': hashed_id}).sort('timestamp', 1)
    messages = [{'username': msg['username'], 'message': msg['message']} for msg in messages_cursor]
    return messages

def delete_room(room_id):
    hashed_id = hash_room_id(room_id)
    roommembers.delete_many({'roomid': hashed_id})
    messages_collection.delete_many({'roomid': hashed_id})



def get_user(username):
    user_data = users_collection.find_one({'_id': username})
    return User(user_data['_id'], user_data['email'], user_data['password']) if user_data else None
