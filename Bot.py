    import logging
import json
import secrets
import string
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from telegram.constants import ParseMode

# --- CONFIGURATION ---
# !!! REPLACE with your bot token from BotFather
BOT_TOKEN = "8079150313:AAEe6wPFYd7JTJ3fgzWR69PcentDAJjmWZc" 

# !!! REPLACE with your own Telegram User ID (get it from @userinfobot)
# This is used to restrict ADMIN commands only to you.
OWNER_ID = 5663291046

# The file to store your private file names and file IDs (admin use)
DB_FILE = "file_db.json"
# The file to store public access codes and file IDs (public use)
CODES_DB_FILE = "codes_db.json"
# --- END CONFIGURATION ---


# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# --- DATABASE HELPERS ---

def load_db(filename):
    """Loads a database from the specified JSON file."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {} # Start with an empty dict if the file doesn't exist

def save_db(db, filename):
    """Saves a database to the specified JSON file."""
    with open(filename, "w") as f:
        json.dump(db, f, indent=2)

def generate_unique_code(length=6):
    """Generates a unique, six-character alphanumeric code."""
    db_codes = load_db(CODES_DB_FILE)
    
    while True:
        characters = string.ascii_uppercase + string.digits
        code = ''.join(secrets.choice(characters) for _ in range(length))
        # Ensure the code is not already in use
        if code not in db_codes:
            return code

# --- COMMAND HANDLERS (ADMIN ONLY) ---

def is_admin(update: Update):
    """Helper function to check if the user is the bot owner."""
    return update.effective_user.id == OWNER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets the user and provides instructions."""
    
    if is_admin(update):
        message = (
            "👋 **Welcome Admin!**\n\n"
            "**Admin Commands:**\n"
            "1. Send any file to save it and get a private filename and public code.\n"
            "2. Use `/list`, `/get <filename>`, and `/delete <filename>`.\n\n"
            "**Public Command:**\n"
            "Any user can use `/access <CODE>`."
        )
    else:
        message = (
            "👋 Welcome! I am a file-sharing bot.\n\n"
            "To retrieve a file, you must have the **unique access code**.\n"
            "**Usage:** `/access <CODE>`"
        )
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lists all files saved in the private database."""
    if not is_admin(update):
        return
        
    db = load_db(DB_FILE)
    if not db:
        await update.message.reply_text("You have no files saved.")
        return

    message = "📁 **Your saved files (Private Database):**\n\n"
    for filename, code in db.items():
        # The 'value' in DB_FILE is now the unique public code
        message += f"• **{filename}** (Code: `{code}`)\n"
        
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def get_file_private(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retrieves and sends a file using its private filename."""
    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Please provide a filename. \nUsage: `/get <filename>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    file_name = " ".join(context.args)
    db = load_db(DB_FILE)
    
    # We now look up the unique code first, then the file_id from the code DB
    unique_code = db.get(file_name)
    db_codes = load_db(CODES_DB_FILE)
    file_id = db_codes.get(unique_code)

    if file_id:
        try:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption=f"Retrieved file: {file_name}")
        except Exception as e:
            await update.message.reply_text(f"❌ Sorry, I couldn't send the file.\n(Error: {e})")
    else:
        await update.message.reply_text(f"File **'{file_name}'** not found in private database.", parse_mode=ParseMode.MARKDOWN)

async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Removes a file reference from both databases."""
    if not is_admin(update):
        return

    if not context.args:
        await update.message.reply_text("Please provide a filename. \nUsage: `/delete <filename>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    file_name = " ".join(context.args)
    
    db = load_db(DB_FILE)
    db_codes = load_db(CODES_DB_FILE)
    
    unique_code = db.pop(file_name, None) # Remove from private DB and get the code
    
    if unique_code:
        db_codes.pop(unique_code, None) # Remove from public code DB
        save_db(db, DB_FILE)
        save_db(db_codes, CODES_DB_FILE)
        await update.message.reply_text(f"🗑️ Reference to **'{file_name}'** (Code: {unique_code}) has been deleted.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"File **'{file_name}'** not found.", parse_mode=ParseMode.MARKDOWN)


# --- COMMAND HANDLER (PUBLIC ACCESS) ---

async def access_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allows ANY user to retrieve a file using a unique code."""
    if not context.args:
        await update.message.reply_text("Please provide the unique code. \nUsage: `/access <CODE>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    code = context.args[0].upper() # Read the code and make it uppercase

    db_codes = load_db(CODES_DB_FILE) 
    file_id = db_codes.get(code)
    
    if file_id:
        try:
            # Send the document (which works for photo, video, etc., via file_id)
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id, caption=f"File retrieved using code: {code}")
        except Exception:
             await update.message.reply_text("❌ Sorry, an error occurred while sending the file. It may be too large or deleted.")
    else:
        await update.message.reply_text(f"File code **'{code}'** not found. Please check the code and try again.", parse_mode=ParseMode.MARKDOWN)


# --- MESSAGE HANDLER (ADMIN UPLOAD) ---

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming media from the Admin only."""
    if not is_admin(update):
        # Public users should only use /access, ignore other messages
        return

    # --- Media Identification Logic (Same as before) ---
    media_object = None
    file_type = "File"
    file_name = None
    
    if update.message.document:
        media_object = update.message.document
        file_name = media_object.file_name
        file_type = "Document"
        
    elif update.message.photo:
        media_object = update.message.photo[-1]
        file_name = f"photo_{media_object.file_unique_id}.jpg"
        file_type = "Photo"
        
    elif update.message.video:
        media_object = update.message.video
        file_name = media_object.file_name if media_object.file_name else f"video_{media_object.file_unique_id}.mp4"
        file_type = "Video"
        
    elif update.message.audio:
        media_object = update.message.audio
        file_name = media_object.file_name
        file_type = "Audio"

    if not media_object:
        # Ignore plain text from admin if it wasn't a command
        return

    file_id = media_object.file_id
    # --- End Media Identification ---


    # 1. Generate unique
    
