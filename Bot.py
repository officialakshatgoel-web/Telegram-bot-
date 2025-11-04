import logging
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

# --- CONFIGURATION ---
# !!! REPLACE with your bot token from BotFather
BOT_TOKEN = "8079150313:AAEe6wPFYd7JTJ3fgzWR69PcentDAJjmWZc" 

# !!! REPLACE with your own Telegram User ID (get it from @userinfobot)
# This makes the bot private to you.
OWNER_ID = 5663291046

# The file to store our file database
DB_FILE = "file_db.json"
# --- END CONFIGURATION ---


# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- DATABASE HELPERS ---

def load_db():
    """Loads the file database from the JSON file."""
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {} # Start with an empty dict if the file doesn't exist

def save_db(db):
    """Saves the file database to the JSON file."""
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

# --- HANDLER FUNCTIONS ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets the user and provides instructions."""
    # Security Check
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Sorry, this is a private file storage bot.")
        return

    await update.message.reply_text(
        "👋 Hello! I am your personal file storage bot.\n\n"
        "**How to use me:**\n"
        "1. Send me any **document, photo, or video**.\n"
        "2. I will save a reference and tell you the saved name.\n"
        "3. Use `/get <filename>` to retrieve it.\n"
        "4. Use `/list` to see all saved files."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Provides a list of commands."""
    if update.effective_user.id != OWNER_ID:
        return
        
    await update.message.reply_text(
        "**Available Commands:**\n"
        "• `/start` - Greet and instructions.\n"
        "• `/list` - Show all files saved.\n"
        "• `/get <filename>` - Retrieve a file by its saved name.\n"
        "• `/delete <filename>` - Remove the file reference from the database."
    )

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming documents, photos, videos, and audio."""
    if update.effective_user.id != OWNER_ID:
        return

    media_object = None
    file_type = "File"
    file_name = None
    
    # 1. Identify the media object and its properties
    if update.message.document:
        media_object = update.message.document
        file_name = media_object.file_name
        file_type = "Document"
        
    elif update.message.photo:
        # Get the largest PhotoSize object
        media_object = update.message.photo[-1]
        # Generate a filename for photos, as they don't have one by default
        file_name = f"photo_{media_object.file_unique_id}.jpg"
        file_type = "Photo"
        
    elif update.message.video:
        media_object = update.message.video
        # Use existing filename or generate one
        file_name = media_object.file_name if media_object.file_name else f"video_{media_object.file_unique_id}.mp4"
        file_type = "Video"
        
    elif update.message.audio:
        media_object = update.message.audio
        file_name = media_object.file_name
        file_type = "Audio"

    # If it's none of the above (e.g., plain text without a command)
    if not media_object:
        if update.message.text:
            # We ignore plain text messages if they aren't commands
            return
        await update.message.reply_text("I only save documents, photos, videos, and audio. Please try again.")
        return

    file_id = media_object.file_id

    # 2. Save the file reference
    db = load_db()
    db[file_name] = file_id
    save_db(db)
    
    await update.message.reply_text(
        f"✅ **{file_type} saved!**\n"
        f"Name: `{file_name}`\n"
        f"Use `/get {file_name}` to retrieve it."
        , parse_mode=ParseMode.MARKDOWN
    )

async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retrieves and sends a file using its file_id."""
    if update.effective_user.id != OWNER_ID:
        return

    # Check for filename argument
    if not context.args:
        await update.message.reply_text("Please provide a filename. \nUsage: `/get <filename>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    file_name = " ".join(context.args)
    
    db = load_db()
    file_id = db.get(file_name)
    
    if file_id:
        try:
            # Send the document (this function works for all media types using file_id)
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption=f"Retrieved file: {file_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ Sorry, I couldn't send the file.\n(Error: {e})")
    else:
        await update.message.reply_text(f"File **'{file_name}'** not found. Use `/list` to see available files.", parse_mode=ParseMode.MARKDOWN)

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all files saved in the database."""
    if update.effective_user.id != OWNER_ID:
        return
        
    db = load_db()
    if not db:
        await update.message.reply_text("You have no files saved.")
        return

    # Format the list of files
    message = "📁 **Your saved files:**\n\n"
    for filename in db.keys():
        message += f"• `{filename}`\n"
        
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes a file reference from the database."""
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("Please provide a filename. \nUsage: `/delete <filename>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    file_name = " ".join(context.args)
    
    db = load_db()
    if file_name in db:
        del db[file_name]
        save_db(db)
        await update.message.reply_text(f"🗑️ Reference to **'{file_name}'** has been deleted.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"File **'{file_name}'** not found.", parse_mode=ParseMode.MARKDOWN)

# --- MAIN APPLICATION ---

def main():
    """Starts the bot."""
    # Create the Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # 1. Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get", get_file))
    application.add_handler(CommandHandler("list", list_files))
    application.add_handler(CommandHandler("delete", delete_file))
    
    # 2. Message Handler for Media
    # This filter listens for Documents, Photos, Videos, and Audio
    media_filter = filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO
    application.add_handler(MessageHandler(media_filter, handle_media))
    
    # Start the bot
    print("🤖 Bot is running... Press Ctrl+C to stop.")
    application.run_polling(poll_interval=1.0)

if __name__ == '__main__':
    main()
        
