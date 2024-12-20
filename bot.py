# bot.py
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction, ParseMode
from telegram import InputMediaVideo, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config import TELEGRAM_TOKEN, GOOGLE_PROJECT_ID
from pdf_manager import LegalGuideManager
from logger_config import setup_logger
from interaction_tracker import InteractionTracker
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler
from tldr_handler import TLDRHandler
from feedback_handler import FeedbackHandler
from response_formatter import ResponseFormatter
from telegram.error import BadRequest

logger = setup_logger()

class LexCommunisBot:
    def __init__(self):
        self.guide_manager = LegalGuideManager(GOOGLE_PROJECT_ID)
        self.tracker = InteractionTracker()
        self.tldr_handler = TLDRHandler()
        self.feedback_handler = FeedbackHandler(self.tracker)
        self.response_cache = {}  # To store responses for TL;DR generation

    async def log_command(self, update: Update, command: str):
        """Log command usage"""
        user = update.effective_user
        await self.tracker.log_interaction(
            user.id,
            user.username,
            'command',
            command
        )
        logger.info(f"Command {command} used by user {user.id} ({user.username})")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Updated start command with streamlined buttons"""
        await self.log_command(update, '/start')
        
        keyboard = [
            [InlineKeyboardButton("❓ Ask Question", switch_inline_query_current_chat="/ask ")],
            [InlineKeyboardButton("📚 Topics", callback_data='topics')],
            [InlineKeyboardButton("⚖️ Disclaimer", callback_data='disclaimer')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "👋 Welcome to LexCommunis Bot!\n\n"
            "I'm your AI assistant for 'The Founders' Guide to UK Crypto Law'. "
            "I can help you understand UK crypto regulations and compliance.\n\n"
            "To get started:\n"
            "🔹 Click *Ask Question* to ask about UK crypto law\n"
            "🔹 View *Topics* to see what's covered\n"
            "🔹 Check the *Disclaimer* for important legal information\n\n"
            "⚖️ *Important*: I provide educational information based solely on the guide. "
            "This is not legal advice."
        )
        await update.message.reply_text(
            welcome_text, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )

    async def ask_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /ask command"""
        if not context.args:
            await update.message.reply_text(
                "Please include your question after /ask\n"
                "Example: /ask What are the key considerations for token design?"
            )
            return
            
        question = ' '.join(context.args)
        await self.process_question(update, question)

    async def process_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for direct text messages"""
        # Process the text message as a question
        await self.process_question(update, context, update.message.text)

    async def process_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question: str) -> None:
        """Simplified process_question with independent chunk handling"""
        try:
            # Initial progress message
            progress_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="🔄 Analyzing your question...",
                parse_mode=ParseMode.MARKDOWN
            )

            # Track responses for TL;DR
            all_responses = []
            total_chunks = len(self.guide_manager.pdf_chunks)
            processed_chunks = 0

            # Process each chunk independently
            async for chunk_response in self.guide_manager.process_chunks_stream(question):
                processed_chunks += 1
                
                # Update progress
                await progress_msg.edit_text(
                    f"📚 Processing section {processed_chunks}/{total_chunks}\n"
                    f"{'▰' * processed_chunks}{'▱' * (total_chunks-processed_chunks)}",
                    parse_mode=ParseMode.MARKDOWN
                )

                if chunk_response:
                    # Format chunk response
                    section_text = (
                        f"📍 *Section {processed_chunks}/{total_chunks}*\n\n"
                        f"{chunk_response}"
                    )
                    
                    # Send each chunk as a separate message
                    try:
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=section_text,
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except BadRequest:
                        # Fallback without markdown if parsing fails
                        clean_text = section_text.replace('*', '').replace('_', '')
                        await context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=clean_text
                        )
                    
                    all_responses.append(chunk_response)

            # Clean up progress message
            await progress_msg.delete()

            # Send final summary message with buttons if we have responses
            if all_responses:
                message_id = str(update.message.message_id)
                self.response_cache[message_id] = "\n\n".join(all_responses)

                final_text = (
                    "✅ *Analysis Complete*\n\n"
                    "I've analyzed all sections of the guide. "
                    "Use the buttons below for a summary or to provide feedback.\n\n"
                    "_Note: This is educational information only, not legal advice._"
                )

                keyboard = [
                    [
                        InlineKeyboardButton("📝 TL;DR", callback_data=f'tldr_{message_id}'),
                        InlineKeyboardButton("✍️ Feedback", callback_data=f'feedback_{message_id}')
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)

                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=final_text,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )

        except Exception as e:
            error_msg = "I apologize, but I encountered an error processing your question. Please try again."
            logging.error(f"Error processing question from user {update.effective_user.id}: {str(e)}")
            if 'progress_msg' in locals():
                await progress_msg.delete()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=error_msg
            )

    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Improved feedback handler"""
        query = update.callback_query
        await query.answer()
        
        try:
            message_id = query.data.split('_')[1]
            
            feedback_text = (
                "📝 *Share Your Feedback*\n\n"
                "*Quick Rating:*\n"
                "Use `/rate {message_id} <1-10>`\n"
                "Example: `/rate {message_id} 8`\n\n"
                "*Detailed Feedback:*\n"
                "Use `/feedback {message_id} <your comments>`\n"
                "Example: `/feedback {message_id} Very helpful explanation!`\n\n"
                "_Your feedback helps us improve! Rate from 1-10 or share detailed thoughts._"
            ).format(message_id=message_id)
            
            await query.message.reply_text(
                feedback_text,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logging.error(f"Error handling feedback: {str(e)}")
            await query.message.reply_text(
                "Sorry, something went wrong while processing your feedback request.",
                parse_mode=ParseMode.MARKDOWN
            )

    async def handle_rate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /rate command"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "Please provide both message ID and score. Example: `/rate 123 8`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        try:
            message_id = int(context.args[0])
            score = int(context.args[1])
            
            if not 1 <= score <= 10:
                await update.message.reply_text("Please provide a score between 1 and 10.")
                return
                
            await self.feedback_handler.log_feedback(
                user_id=update.effective_user.id,
                username=update.effective_user.username,
                message_id=message_id,
                score=score
            )
            
            await update.message.reply_text(
                f"Thank you for your rating of {score}/10! 🌟\n"
                "Your feedback helps us improve."
            )
            
        except ValueError:
            await update.message.reply_text(
                "Invalid input. Please use the format: `/rate message_id score`\n"
                "Example: `/rate 123 8`",
                parse_mode=ParseMode.MARKDOWN
            )

    async def handle_feedback_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /feedback command"""
        if len(context.args) < 2:
            await update.message.reply_text(
                "Please provide both message ID and feedback. Example: `/feedback 123 Very helpful!`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        try:
            message_id = int(context.args[0])
            feedback_text = ' '.join(context.args[1:])
            
            await self.feedback_handler.log_feedback(
                user_id=update.effective_user.id,
                username=update.effective_user.username,
                message_id=message_id,
                comment=feedback_text
            )
            
            await update.message.reply_text(
                "Thank you for your detailed feedback! 🙏\n"
                "Your input helps us improve our responses."
            )
            
        except ValueError:
            await update.message.reply_text(
                "Invalid input. Please use the format: `/feedback message_id your feedback text`",
                parse_mode=ParseMode.MARKDOWN
            )

    async def topics_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /topics command"""
        await self.log_command(update, '/topics')
        
        topics_text = (
            "🚀 *Topics* 🚀\n\n"
            "Here's a breakdown of key topics covered in our guide:\n\n"
            "1. *Product Design and Planning*: Learn about tokenomics, compliance-by-design, "
            "and building successful Web3 projects.\n\n"
            "2. *Token Typologies*: Understand token models in games, SocialFi, DeFi, and more.\n\n"
            "3. *Navigating Legal Risks*: Guidance on AML, sanctions, and FCA compliance in the UK.\n\n"
            "4. *Marketing Cryptoassets*: Insights on UK regulations for promoting crypto products.\n\n"
            "5. *Tax and Accounting*: Practical tips for tax compliance and financial reporting.\n\n"
            "6. *Asset Recovery*: Learn how to trace and recover stolen crypto.\n\n"
            "7. *Token Launch*: Strategies for launching your token with legal and community insights.\n\n"
            "8. *Community Building*: Explore the role of Web3 accelerators and community engagement.\n\n"
            "Use /ask to learn more about any of these topics!"
        )
        await update.message.reply_text(topics_text, parse_mode=ParseMode.MARKDOWN)

    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /help command"""
        await self.log_command(update, '/help')
        
        help_text = (
            "🤖 *Available Commands:*\n\n"
            "/ask [question] - Ask any question about UK crypto law\n"
            "/topics - View main topics covered\n"
            "/help - Show this help message\n"
            "/disclaimer - View legal disclaimer\n\n"
            "*Tips for Better Results:*\n"
            "• Be specific in your questions\n"
            "• Use complete sentences\n"
            "• One question at a time\n"
            "*Example Questions:*\n"
            "• /ask What are the key considerations for DAO governance?\n"
        )
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Updated start command with streamlined buttons"""
        await self.log_command(update, '/start')
        
        keyboard = [
            [InlineKeyboardButton("❓ Ask Question", switch_inline_query_current_chat="/ask ")],
            [InlineKeyboardButton("📚 Topics", callback_data='topics')],
            [InlineKeyboardButton("⚖️ Disclaimer", callback_data='disclaimer')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        welcome_text = (
            "👋 Welcome to LexCommunis Bot!\n\n"
            "I'm your AI assistant for 'The Founders' Guide to UK Crypto Law'. "
            "I can help you understand UK crypto regulations and compliance.\n\n"
            "To get started:\n"
            "🔹 Click *Ask Question* to ask about UK crypto law\n"
            "🔹 View *Topics* to see what's covered\n"
            "🔹 Check the *Disclaimer* for important legal information\n\n"
            "⚖️ *Important*: I provide educational information based solely on the guide. "
            "This is not legal advice."
        )
        await update.message.reply_text(
            welcome_text, 
            reply_markup=reply_markup, 
            parse_mode=ParseMode.MARKDOWN
        )

    async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Updated callback handler for button presses"""
        query = update.callback_query
        await query.answer()
        
        if query.data == 'topics':
            # Send topics directly in the chat
            topics_text = (
                "🚀 *Topics Covered* 🚀\n\n"
                "Here's what you can ask about:\n\n"
                "1. *Product Design and Planning*\n"
                "• Tokenomics and compliance-by-design\n"
                "• Legal structures for Web3 projects\n\n"
                "2. *Token Typologies*\n"
                "• Gaming tokens, SocialFi, DeFi models\n\n"
                "3. *Legal Risks*\n"
                "• AML, sanctions, FCA compliance\n\n"
                "4. *Marketing Regulations*\n"
                "• UK rules for promoting crypto\n\n"
                "5. *Tax and Accounting*\n"
                "• Compliance and reporting\n\n"
                "6. *Asset Recovery*\n"
                "• Tracing and recovering crypto\n\n"
                "7. *Token Launch*\n"
                "• Legal and community strategies\n\n"
                "To ask about any topic, use:\n"
                "`/ask your question here`"
            )
            await query.message.edit_text(
                topics_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("❓ Ask Question", switch_inline_query_current_chat="/ask ")
                ]])
            )
        
        elif query.data == 'disclaimer':
            disclaimer_text = (
                "⚖️ *Legal Disclaimer*\n\n"
                "This bot provides educational information based on 'The Founders' Guide to UK Crypto Law'. "
                "It is not legal, financial, or tax advice.\n\n"
                "• Information is for educational purposes only\n"
                "• Seek professional advice for specific situations\n"
                "• Different laws may apply in England, Wales, Scotland, and Northern Ireland\n"
                "• Content may become outdated\n\n"
                "For legal matters, always consult qualified professionals in your jurisdiction."
            )
            await query.message.edit_text(
                disclaimer_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("◀️ Back", callback_data='start')
                ]])
            )
        
        elif query.data == 'start':
            # Return to start menu
            await query.message.delete()
            await self.start(update, context)
        
        elif query.data.startswith('tldr_'):
            await self.handle_tldr(update, context)
        elif query.data.startswith('feedback_'):
            await self.handle_feedback(update, context)
        elif query.data.startswith('rate_'):
            await self.handle_rating(update, context)

    async def about_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle about info"""
        about_text = (
            "📚 *About the UK Crypto Law Guide*\n\n"
            "This comprehensive guide covers essential legal considerations for Web3 projects "
            "in the UK, authored by industry experts in blockchain law and compliance.\n\n"
            "*Key Areas:*\n"
            "• Token Design & Economics\n"
            "• Legal Structures\n"
            "• Regulatory Compliance\n"
            "• Data Protection\n"
            "• DAO Operations\n\n"
            "Use /ask to learn more about any topic!"
        )
        await update.message.reply_text(about_text, parse_mode=ParseMode.MARKDOWN)

    async def disclaimer_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        disclaimer_text = (
            "⚖️ *DISCLAIMERS*\n\n"
            "The content in this publication is not legal, financial, or tax advice, "
            "nor a recommendation to use any particular product or service. The mention "
            "of specific organizations, technologies, or products does not imply "
            "endorsement or preference over others not mentioned.\n\n"
            "Users are responsible for seeking their own independent, professional "
            "advice based on their individual circumstances. The publishers, editors, "
            "authors, contributors, and reviewers, along with their affiliated entities "
            "and employers, do not accept responsibility or liability for any claims "
            "arising from the use or reliance on this publication.\n\n"
            "None are responsible for outdated or incomplete content. Users must verify "
            "the currency and accuracy of all information contained herein. All rights "
            "reserved.\n\n"
            "While this guide references the UK, please note that different laws may "
            "apply in England and Wales, Scotland, and Northern Ireland. You should "
            "seek advice from suitably qualified professionals in the relevant jurisdiction."
        )
        await update.message.reply_text(disclaimer_text, parse_mode=ParseMode.MARKDOWN)

    async def handle_tldr(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Improved TL;DR handler"""
        query = update.callback_query
        await query.answer()
        
        try:
            message_id = query.data.split('_')[1]
            original_response = self.response_cache.get(message_id)
            
            if not original_response:
                await query.message.reply_text(
                    "Sorry, I couldn't generate a TL;DR for this response. The original message may have expired.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # Send processing message
            processing_msg = await query.message.reply_text(
                "🤔 Generating TL;DR summary...",
                parse_mode=ParseMode.MARKDOWN
            )
            
            tldr = await self.tldr_handler.generate_tldr(original_response)
            await processing_msg.delete()
            
            if tldr:
                keyboard = [[InlineKeyboardButton("✍️ Feedback", callback_data=f'feedback_{message_id}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.message.reply_text(
                    f"📝 *TL;DR Summary:*\n\n{tldr}",
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=reply_markup
                )
            else:
                await query.message.reply_text(
                    "Sorry, I couldn't generate a TL;DR summary at this time.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
        except Exception as e:
            logging.error(f"Error generating TL;DR: {str(e)}")
            await query.message.reply_text(
                "Sorry, something went wrong while generating the TL;DR summary.",
                parse_mode=ParseMode.MARKDOWN
            )

async def callback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Modified callback handler to handle all button presses"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'help':
        await self.help_handler(update, context)
    elif query.data == 'about':
        await self.about_handler(update, context)
    elif query.data == 'disclaimer':
        await self.disclaimer_handler(update, context)
    elif query.data.startswith('tldr_'):
        await self.handle_tldr(update, context)
    elif query.data.startswith('feedback_'):
        await self.handle_feedback(update, context)
    elif query.data.startswith('rate_'):
        await self.handle_rating(update, context)

def main():
    """Initialize and start the bot"""
    logger.info("Starting LexCommunis Bot")
    
    bot = LexCommunisBot()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", bot.start))
    application.add_handler(CommandHandler("help", bot.help_handler))
    application.add_handler(CommandHandler("ask", bot.ask_handler))
    application.add_handler(CommandHandler("topics", bot.topics_handler))
    application.add_handler(CommandHandler("disclaimer", bot.disclaimer_handler))
    application.add_handler(CommandHandler("rate", bot.handle_rate_command))
    application.add_handler(CommandHandler("feedback", bot.handle_feedback_command))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(bot.callback_handler))
    
    # Fixed message handler
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        bot.process_message
    ))
    
    logger.info("Bot is ready to accept connections")
    application.run_polling()

if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    main()