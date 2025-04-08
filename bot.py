from telegram.ext import ApplicationBuilder, CommandHandler
import os

async def start(update, context):
    await update.message.reply_text("Hola! Soy un bot.")

app = ApplicationBuilder().token(os.environ["7745916264:AAFaxmVrQsqiEjq5yhq6BdDQ7wBKjjb4Gn8"]).build()
app.add_handler(CommandHandler("start", start))
app.run_polling()
