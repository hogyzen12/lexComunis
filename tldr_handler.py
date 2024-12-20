# tldr_handler.py
import logging
import openai
from typing import Optional
from config import OPENAI_API_KEY

class TLDRHandler:
    def __init__(self):
        self.api_key = OPENAI_API_KEY
        openai.api_key = self.api_key
        
    async def generate_tldr(self, content: str) -> Optional[str]:
        """Generate a TL;DR version of the given content using OpenAI."""
        try:
            response = await openai.ChatCompletion.acreate(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Create a brief TL;DR summary of the following text, focusing on the key points and actionable insights:"},
                    {"role": "user", "content": content}
                ],
                max_tokens=150,
                temperature=0.7
            )
            
            return "TL;DR:\n" + response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error generating TL;DR: {str(e)}")
            return None