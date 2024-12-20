# feedback_handler.py
import json
import logging
from datetime import datetime
from typing import Optional
from interaction_tracker import InteractionTracker

class FeedbackHandler:
    def __init__(self, tracker: InteractionTracker):
        self.tracker = tracker
        
    async def log_feedback(self, user_id: int, username: str, 
                          message_id: int, score: Optional[int] = None, 
                          comment: Optional[str] = None):
        """Log user feedback for a specific response."""
        feedback = {
            'message_id': message_id,
            'score': score,
            'comment': comment,
            'timestamp': datetime.now().isoformat()
        }
        
        await self.tracker.log_interaction(
            user_id=user_id,
            username=username,
            message_type='feedback',
            content=json.dumps(feedback)
        )