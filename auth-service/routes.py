from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required
from models.user import User
from sqlalchemy import text
from db import db 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import threading
import time
from models.transaction import Transaction
import uuid

auth_bp = Blueprint('auth', __name__)

limiter = Limiter(get_remote_address)

max_concurrent_tasks = 10
semaphore = threading.BoundedSemaphore(value=max_concurrent_tasks)

@auth_bp.route("/api/auth/prepare", methods=["POST"])
def prepare():
    transaction_id = request.json.get("transaction_id")
    data = request.json.get("data")

    try:
        # Create and save transaction as "prepared"
        transaction = Transaction(transaction_id=transaction_id, status="prepared", data=data)
        db.session.add(transaction)
        db.session.commit()

        return jsonify({"transaction_id": transaction_id, "status": "prepared"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/api/auth/commit", methods=["POST"])
def commit():
    transaction_id = request.json.get("transaction_id")

    try:
        transaction = Transaction.query.get(transaction_id)
        if transaction and transaction.status == "prepared":
            # Update status to "committed"
            transaction.status = "committed"
            db.session.commit()
            return jsonify({"status": "committed"}), 200
        else:
            return jsonify({"error": "Transaction not found or not prepared"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@auth_bp.route("/api/auth/abort", methods=["POST"])
def abort():
    transaction_id = request.json.get("transaction_id")

    try:
        # Retrieve the transaction by ID
        transaction = Transaction.query.get(transaction_id)
        if transaction:
            # Update status to "aborted" and commit
            transaction.status = "aborted"
            db.session.commit()

            # Delete the transaction entry from the table
            Transaction.query.filter_by(transaction_id=transaction_id).delete()
            db.session.commit()

            return jsonify({"status": "aborted and deleted"}), 200
        else:
            return jsonify({"error": "Transaction not found"}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

# Register a user
@auth_bp.route('/api/auth/register', methods=['POST'])
@limiter.limit("5 per minute")
def register():
    try:
        semaphore.acquire()
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password') 

        # data = request.get_json()
        # if data.get("email") == "test500error@example.com":
        #     raise Exception("Simulated server error for testing")
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            return jsonify({'message': 'Username already exists'}), 400
        if User.query.filter_by(email=email).first():
            return jsonify({'message': 'Email already exists'}), 400

        # Create new user
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()

        return jsonify({'message': 'User registered successfully'}), 201
    finally:
        semaphore.release() 

# Log in a user
@auth_bp.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    try:
        semaphore.acquire()
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')

        user = User.query.filter_by(email=email).first()

        if user and user.password == password:
            # Create JWT token
            access_token = create_access_token(identity=user.id)
            return jsonify({'message': 'Login successful', 'access_token': access_token, 'user': user.username}), 200
        else:
            return jsonify({'message': 'Invalid email or password'}), 401
    finally:
        semaphore.release()

# Log out a user (dummy route, no JWT revocation here)
@auth_bp.route('/api/auth/logout', methods=['POST'])
@limiter.limit("5 per minute")
@jwt_required()
def logout():
    try:
        semaphore.acquire()
        return jsonify({'message': 'User logged out'}), 200
    finally:
        semaphore.release()

# Status endpoint
@auth_bp.route('/api/auth/status', methods=['GET'])
@limiter.limit("5 per minute")
def status():
    try:
        semaphore.acquire()
        try:
            # time.sleep(4)
            db.session.execute(text('SELECT 1'))  
            return jsonify({'servise': 'auth','status': 'running'}), 200
        except Exception as e:
            return jsonify({'status': 'ERROR', 'database': 'Not connected', 'error': str(e)}), 500
    finally:
        semaphore.release()

# Get all users
@auth_bp.route('/api/auth/users', methods=['GET'])
@limiter.limit("5 per minute")
def get_all_users():
    try:
        semaphore.acquire()
        users = User.query.all()
        user_list = [{'id': user.id, 'username': user.username, 'email': user.email} for user in users]
        return jsonify(user_list), 200
    finally:
        semaphore.release()

# Update a user
@auth_bp.route('/api/auth/users/<int:id>', methods=['PUT'])
@limiter.limit("5 per minute")
@jwt_required()
def update_user(id):
    try:
        semaphore.acquire()
        data = request.get_json()
        user = User.query.get(id)

        if not user:
            return jsonify({'message': 'User not found'}), 404

        if 'username' in data:
            user.username = data['username']
        if 'email' in data:
            user.email = data['email']
        if 'password' in data:
            user.password = data['password']  # In a real-world app, hash this

        db.session.commit()
        return jsonify({'message': 'User updated successfully'}), 200
    finally:
        semaphore.release()



# @auth_bp.route('/api/auth/users/<int:user_id>', methods=['DELETE'])
# @jwt_required()
# def delete_user(user_id):
#     user = User.query.get_or_404(user_id)
#     db.session.delete(user)
#     db.session.commit()
#     return jsonify({'message': 'User deleted successfully'}), 200