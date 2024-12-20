# pdf_manager.py
import os
import logging
import pypdf
import json
import time
import asyncio
from typing import Dict, List, Tuple, AsyncGenerator
import vertexai
from vertexai.generative_models import GenerativeModel, Part

class LegalGuideManager:
    def __init__(self, project_id: str, location: str = "us-central1", cache_dir: str = ".cache"):
        vertexai.init(project=project_id, location=location)
        self.model = GenerativeModel("gemini-1.5-pro-002")
        self.cache_dir = os.path.abspath(cache_dir)
        self.pdf_chunks = []
        self.chunk_ranges = []
        self.cache = {}
        
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        self._load_cache()
        
        pdf_path = os.path.join(os.path.dirname(__file__), "uk_crypto_law_guide.pdf")
        self._initialize_pdf(pdf_path)

    async def process_chunk(self, question: str, chunk_index: int) -> str:
        """Process a single chunk with improved error handling"""
        cache_key = f"{question.lower().strip()}_{chunk_index}"
        
        if cache_key in self.cache:
            await asyncio.sleep(0.1)  # Small delay for cached responses
            return self.cache[cache_key]
        
        try:
            pdf_file = Part.from_data(
                data=open(self.pdf_chunks[chunk_index], "rb").read(),
                mime_type="application/pdf"
            )
            
            prompt = (
                f"{question}\n\n"
                "Please analyze this section and provide:\n"
                "1. Key relevant information\n"
                "2. Brief, factual responses\n"
                "3. Specific references when applicable\n"
                "\nKeep the response clear and concise."
            )
            
            chat = self.model.start_chat()
            response = chat.send_message([pdf_file, prompt])
            
            if response and response.text:
                # Clean the response
                clean_text = self._sanitize_response(response.text)
                self.cache[cache_key] = clean_text
                self._save_cache()
                return clean_text
            
            return None
            
        except Exception as e:
            logging.error(f"Error processing chunk {chunk_index}: {str(e)}")
            return f"Error processing section {chunk_index + 1}. Please try again."

    async def process_chunks_stream(self, question: str) -> AsyncGenerator[str, None]:
        """Improved async generator for chunk processing"""
        if not self.pdf_chunks:
            yield "Error: No document loaded. Please try again later."
            return

        for chunk_index in range(len(self.pdf_chunks)):
            try:
                response = await self.process_chunk(question, chunk_index)
                if response:
                    yield response
                await asyncio.sleep(0.2)  # Small delay between chunks
            except Exception as e:
                logging.error(f"Error in chunk {chunk_index}: {str(e)}")
                yield f"Error processing section {chunk_index + 1}. Continuing with remaining sections..."

    def _sanitize_response(self, text: str) -> str:
        """Clean and format response text"""
        if not text:
            return ""
            
        # Remove problematic markdown
        text = text.replace('```', '')
        
        # Ensure proper markdown formatting
        lines = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                # Fix unmatched markdown symbols
                asterisk_count = line.count('*')
                if asterisk_count % 2 != 0:
                    line = line.replace('*', '')
                
                underscore_count = line.count('_')
                if underscore_count % 2 != 0:
                    line = line.replace('_', '')
                
                lines.append(line)
        
        # Join with proper spacing
        return '\n\n'.join(lines)

    def _initialize_pdf(self, file_path: str) -> None:
        """Initialize PDF with better error handling"""
        try:
            if not os.path.exists(file_path):
                logging.error(f"PDF file not found at: {file_path}")
                return
                
            reader = pypdf.PdfReader(file_path)
            total_pages = len(reader.pages)
            
            # Split into quarters
            chunk_size = total_pages // 4
            chunks = [
                ("First Quarter", 0, chunk_size),
                ("Second Quarter", chunk_size, chunk_size * 2),
                ("Third Quarter", chunk_size * 2, chunk_size * 3),
                ("Fourth Quarter", chunk_size * 3, total_pages)
            ]
            
            # Clear existing chunks
            self.pdf_chunks = []
            self.chunk_ranges = []
            
            for chunk_index, (chunk_name, start, end) in enumerate(chunks):
                writer = pypdf.PdfWriter()
                for page_num in range(start, end):
                    writer.add_page(reader.pages[page_num])
                
                chunk_file = os.path.join(self.cache_dir, f"chunk_{chunk_index}.pdf")
                with open(chunk_file, 'wb') as f:
                    writer.write(f)
                
                self.pdf_chunks.append(chunk_file)
                self.chunk_ranges.append(f"{chunk_name} (Pages {start+1}-{end})")
            
        except Exception as e:
            logging.error(f"Error initializing PDF: {str(e)}")
            raise

    def _load_cache(self):
        cache_file = os.path.join(self.cache_dir, "response_cache.json")
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                self.cache = json.load(f)

    def _save_cache(self):
        with open(os.path.join(self.cache_dir, "response_cache.json"), 'w') as f:
            json.dump(self.cache, f)

    def __del__(self):
        try:
            for chunk_file in self.pdf_chunks:
                if os.path.exists(chunk_file):
                    os.remove(chunk_file)
        except:
            pass