# response_formatter.py
class ResponseFormatter:
    @staticmethod
    def clean_markdown(text: str) -> str:
        """Clean markdown formatting to prevent parsing errors"""
        # Remove code blocks
        text = text.replace('```', '')
        text = text.replace('`', '')
        
        # Ensure asterisks are balanced
        asterisk_count = text.count('*')
        if asterisk_count % 2 != 0:
            text = text.replace('*', '')
            
        # Ensure underscores are balanced
        underscore_count = text.count('_')
        if underscore_count % 2 != 0:
            text = text.replace('_', '')
            
        # Clean up newlines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = '\n\n'.join(lines)
        
        return text.strip()

    @staticmethod
    def format_section_response(section_num: int, total_sections: int, text: str) -> str:
        """Format a section response"""
        header = f"📍 *Section {section_num}/{total_sections}*\n"
        cleaned_text = ResponseFormatter.clean_markdown(text)
        return f"{header}\n{cleaned_text}"

    @staticmethod
    def format_final_response(text: str) -> str:
        """Format the final combined response"""
        cleaned_text = ResponseFormatter.clean_markdown(text)
        disclaimer = (
            "\n\n_Note: This information is educational only, not legal advice. "
            "See /disclaimer for full legal disclaimers._"
        )
        return f"{cleaned_text}{disclaimer}"