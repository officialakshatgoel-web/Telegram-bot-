import logging
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# --- CONFIGURATION ---
# !!! REPLACE with your bot token from BotFather
BOT_TOKEN = "123456789:YOUR_TOKEN_HERE" 

# !!! REPLACE with your own Telegram User ID.
# This makes the bot private to you.
# To find your ID, message @userinfobot on Telegram.
OWNER_ID = 123456789 

# The file to store our file database
DB_FILE = "file_db.json"
# --- END CONFIGURATION ---


# Set up logging to see errors
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Helper function to load our file database
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {} # Return an empty dict if the file doesn't exist

# Helper function to save our file database
def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


# Command handler for /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if the user is the owner
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Sorry, this is a private bot.")
        return

    await update.message.reply_text(
        "Hello! I am your personal file storage bot.\n\n"
        "1. Send me any document (file).\n"
        "2. I will save a reference to it.\n"
        "3. Use /get <filename> to retrieve it.\n"
        "4. Use /list to see all saved files."
    )

# Command handler for /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    await update.message.reply_text(
        "Send me a document to save it.\n"
        "Use /get <filename> to retrieve a file.\n"
        "Use /list to see all saved files.\n"
        "Use /delete <filename> to remove a file reference."
    )

# Message handler for receiving documents
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    doc = update.message.document
    file_id = doc.file_id
    file_name = doc.file_name

    # Load the database, add the new file, and save
    db = load_db()
    db[file_name] = file_id
    save_db(db)
    
    await update.message.reply_text(
        f"✅ File saved!\n"
        f"Name: {file_name}\n"
        f"To retrieve it, send: /get {file_name}"
    )

# Command handler for /get
async def get_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    # Get the filename from the user's message (e.g., "/get my_file.txt")
    if not context.args:
        await update.message.reply_text("Please provide a filename. \nUsage: /get <filename>")
        return
    
    file_name = " ".join(context.args)
    
    # Load the database and find the file_id
    db = load_db()
    file_id = db.get(file_name)
    
    if file_id:
        try:
            # Send the document back to the user using its file_id
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file_id)
        except Exception as e:
            await update.message.reply_text(f"Sorry, I couldn't send the file. Error: {e}")
    else:
        await update.message.reply_text("File not found. Check the name or use /list.")

# Command handler for /list
async def list_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
        
    db = load_db()
    if not db:
        await update.message.reply_text("You have no files saved.")
        return

    # Format the list of files
    message = "📁 **Your saved files:**\n\n"
    for filename in db.keys():
        message += f"- `{filename}`\n"
        
    await update.message.reply_text(message, parse_mode="Markdown")

# Command handler for /delete
async def delete_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    if not context.args:
        await update.message.reply_text("Please provide a filename. \nUsage: /delete <filename>")
        return
    
    file_name = " ".join(context.args)
    
    db = load_db()
    if file_name in db:
        del db[file_name]
        save_db(db)
        await update.message.reply_text(f"🗑️ Reference to '{file_name}' has been deleted.")
    else:
        await update.message.reply_text("File not found.")


# Main function to start the bot
def main():
    # Create the Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add all the handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("get", get_file))
    application.add_handler(CommandHandler("list", list_files))
    application.add_handler(CommandHandler("delete", delete_file))
    
    # Add a handler for all non-command messages that are documents
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Start the bot
    print("Bot is running... Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == '__main__':
    main()
