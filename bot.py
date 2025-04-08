from telegram.ext import ApplicationBuilder, CommandHandler
import os

async def start(update, context):
    await update.message.reply_text("Hola! Soy un bot.")

app = ApplicationBuilder().token(os.environ["7760745441:AAHuqxfBvskKyvA3gzflIe8tUYuU_fCXiKg"]).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
