# interaction_tracker.py
import json
from datetime import datetime
import os

class InteractionTracker:
    def __init__(self, storage_dir='data'):
        self.storage_dir = storage_dir
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        self.log_file = os.path.join(storage_dir, 'interactions.jsonl')

    async def log_interaction(self, user_id, username, message_type, content, response=None):
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'username': username,
            'message_type': message_type,
            'content': content,
            'response': response
        }
        
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(interaction) + '\n')
