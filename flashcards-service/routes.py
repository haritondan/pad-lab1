from flask import Blueprint, request, jsonify
from app import db
from models.flashcard_set import FlashcardSet
from models.flashcard import Flashcard

flashcards_bp = Blueprint('flashcards_bp', __name__)

# Get all flashcard sets
@flashcards_bp.route('/api/flashcards', methods=['GET'])
def get_flashcard_sets():
    flashcard_sets = FlashcardSet.query.all()
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

# Get a single flashcard set by ID
@flashcards_bp.route('/api/flashcards/<int:set_id>', methods=['GET'])
def get_flashcard_set(set_id):
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    result = {
        "setId": flashcard_set.id,
        "title": flashcard_set.title,
        "subject": flashcard_set.subject,
        "creatorId": flashcard_set.creator_id,
        "cards": [{"cardId": card.id, "question": card.question, "answer": card.answer} for card in flashcard_set.flashcards]
    }
    return jsonify(result), 200

# Create a new flashcard set
@flashcards_bp.route('/api/flashcards', methods=['POST'])
def create_flashcard_set():
    data = request.get_json()
    title = data.get('title')
    subject = data.get('subject')
    creator_id = data.get('creatorId')
    cards_data = data.get('cards', [])

    new_flashcard_set = FlashcardSet(title=title, subject=subject, creator_id=creator_id)
    db.session.add(new_flashcard_set)
    db.session.commit()

    # Add the flashcards to the set
    for card in cards_data:
        new_flashcard = Flashcard(set_id=new_flashcard_set.id, question=card['question'], answer=card['answer'])
        db.session.add(new_flashcard)
    
    db.session.commit()

    return jsonify({"message": "Flashcard set created successfully", "title": title}), 201

# Update a flashcard set
@flashcards_bp.route('/api/flashcards/<int:set_id>', methods=['PUT'])
def update_flashcard_set(set_id):
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

# Delete a flashcard set
@flashcards_bp.route('/api/flashcards/<int:set_id>', methods=['DELETE'])
def delete_flashcard_set(set_id):
    flashcard_set = FlashcardSet.query.get_or_404(set_id)
    db.session.delete(flashcard_set)
    db.session.commit()
    return jsonify({"message": "Flashcard set deleted successfully"}), 200
