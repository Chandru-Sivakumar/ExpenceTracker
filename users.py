import json
import os
import datetime
from werkzeug.security import generate_password_hash, check_password_hash

USERS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'users.json')

def init_users_file():
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)

def get_users():
    init_users_file()
    with open(USERS_FILE, 'r') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def add_user(username, password):
    users = get_users()
    if username in users:
        return False, "Username already exists"
    
    users[username] = {
        'password': generate_password_hash(password),
        'created_at': str(datetime.datetime.now())
    }
    save_users(users)
    return True, "User created successfully"

def verify_user(username, password):
    users = get_users()
    if username not in users:
        return False
    
    return check_password_hash(users[username]['password'], password) 