import time
from flask import Blueprint, request, jsonify
from db import db
from models.flashcard_set import FlashcardSet
from models.flashcard import Flashcard
from sqlalchemy import text
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask_limiter import Limiter  
from flask_limiter.util import get_remote_address
import threading

max_concurrent_tasks = 3  # Adjust this number based on your system's capacity
semaphore = threading.BoundedSemaphore(value=max_concurrent_tasks)


flashcards_bp = Blueprint('flashcards_bp', __name__)

limiter = Limiter(get_remote_address)

# Get all flashcard sets
@flashcards_bp.route('/api/flashcards', methods=['GET'])
@limiter.limit("5 per minute")
def get_flashcard_sets():
    try:
        semaphore.acquire()
        flashcard_sets = FlashcardSet.query.all()
        # time.sleep(6)  # Simulate a slow request
        results = [
            {
                "setId": fs.id,
                "title": fs.title,
                "subject": fs.subject,
                "creatorId": fs.creator_id,
                "cards": [{"cardId": card.id, "question": card.question, "answer": card.answer} for card in fs.flashcards]
            }
            for fs in flashcard_sets
        ]
        return jsonify({"flashcardSets": results}), 200
    finally:
        semaphore.release()

# Get a single flashcard set by ID
@flashcards_bp.route('/api/flashcards/<int:set_id>', methods=['GET'])
@limiter.limit("5 per minute")
def get_flashcard_set(set_id):
    try:
        semaphore.acquire()
        flashcard_set = FlashcardSet.query.get_or_404(set_id)
        result = {
            "setId": flashcard_set.id,
            "title": flashcard_set.title,
            "subject": flashcard_set.subject,
            "creatorId": flashcard_set.creator_id,
            "cards": [{"cardId": card.id, "question": card.question, "answer": card.answer} for card in flashcard_set.flashcards]
        }
        return jsonify(result), 200
    finally:
        semaphore.release()

# Create a new flashcard set
@flashcards_bp.route('/api/flashcards', methods=['POST'])
@limiter.limit("5 per minute")
@jwt_required()
def create_flashcard_set():
    try:
        semaphore.acquire()
        data = request.get_json()
        title = data.get('title')
        subject = data.get('subject')
        cards_data = data.get('cards', [])

        creator_id = get_jwt_identity()

        new_flashcard_set = FlashcardSet(title=title, subject=subject, creator_id=creator_id)
        db.session.add(new_flashcard_set)
        db.session.commit()

        # Add the flashcards to the set
        for card in cards_data:
            new_flashcard = Flashcard(set_id=new_flashcard_set.id, question=card['question'], answer=card['answer'])
            db.session.add(new_flashcard)
        
        db.session.commit()

        return jsonify({"message": "Flashcard set created successfully", "title": title}), 201
    finally:
        semaphore.release()

# Update a flashcard set
@flashcards_bp.route('/api/flashcards/<int:set_id>', methods=['PUT'])
@limiter.limit("5 per minute")
def update_flashcard_set(set_id):
    try:
        semaphore.acquire()
        flashcard_set = FlashcardSet.query.get_or_404(set_id)
        data = request.get_json()

        flashcard_set.title = data.get('title', flashcard_set.title)
        flashcard_set.subject = data.get('subject', flashcard_set.subject)

        # Update or create flashcards
        for card_data in data.get('cards', []):
            flashcard = Flashcard.query.filter_by(id=card_data['cardId'], set_id=set_id).first()
            if flashcard:
                flashcard.question = card_data.get('question', flashcard.question)
                flashcard.answer = card_data.get('answer', flashcard.answer)
            else:
                new_card = Flashcard(set_id=set_id, question=card_data['question'], answer=card_data['answer'])
                db.session.add(new_card)

        db.session.commit()

        return jsonify({"message": "Flashcard set updated successfully"}), 200
    finally:
        semaphore.release()

# Delete a flashcard set
@flashcards_bp.route('/api/flashcards/<int:set_id>', methods=['DELETE'])
@limiter.limit("5 per minute")
def delete_flashcard_set(set_id):
    try:
        semaphore.acquire()
        flashcard_set = FlashcardSet.query.get_or_404(set_id)
        db.session.delete(flashcard_set)
        db.session.commit()
        return jsonify({"message": "Flashcard set deleted successfully"}), 200
    finally:
        semaphore.release()



@flashcards_bp.route('/api/flashcards/status', methods=['GET'])
@limiter.limit("5 per minute")
def status():
    try:
        semaphore.acquire()
        try:
            with db.engine.connect() as connection:
                result = connection.execute(text('SELECT 1')).fetchone()
            if result and result[0] == 1:
                return jsonify({
                    "service": "flashcards",
                    "status": "running"
                }), 200
            else:
                return jsonify({
                    "service": "flashcards",
                    "status": "ERROR",
                    "database": "Connected but query returned unexpected result"
                }), 500
        except Exception as e:
            return jsonify({
                "service": "flashcards",
                "status": "ERROR",
                "database": "Not connected",
                "error": str(e)
            }), 500
    finally:
        semaphore.release()

