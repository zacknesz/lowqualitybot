import telebot
from telebot import types
from flask import Flask
import threading
import json
import os

BOT_TOKEN = "7745916264:AAFaxmVrQsqiEjq5yhq6BdDQ7wBKjjb4Gn8"
bot = telebot.TeleBot(BOT_TOKEN)
admin = -1001862368664
owner_id = 7967939255

# Archivos y almacenamiento
BLACKLIST_FILE = 'blacklist.json'
STATS_FILE = 'stats.json'
PREMIUM_FILE = 'premium.json'

# Cargar listas
blacklist = json.load(open(BLACKLIST_FILE)) if os.path.exists(BLACKLIST_FILE) else []
stats = json.load(open(STATS_FILE)) if os.path.exists(STATS_FILE) else {}
premium_users = json.load(open(PREMIUM_FILE)) if os.path.exists(PREMIUM_FILE) else []

# Guardar listas
def guardar_blacklist():
    json.dump(blacklist, open(BLACKLIST_FILE, 'w'))

def guardar_stats():
    json.dump(stats, open(STATS_FILE, 'w'))

def guardar_premium():
    json.dump(premium_users, open(PREMIUM_FILE, 'w'))

# Sesiones para edición de caption
user_sessions = {}

# Comandos básicos
@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome = "\nBienvenido a @LowQualityContentBot. Envía un meme y será enviado a los admins para posteriormente publicarlo en el canal."
    bot.reply_to(message, f"Hola, @{message.from_user.username}." + welcome)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_msg = "Información:\nOwner: @dicksonpussylover\nProgramado con python en 2h Lmao\n@dicksonpussylover\n@LowQualityFamily\n\nLista de comandos:\n/start - Bienvenida\n/help - Este mensaje"
    bot.reply_to(message, help_msg)

# Comandos premium
@bot.message_handler(commands=['addpremium'])
def add_premium(message):
    if message.from_user.id != owner_id: return
    try:
        uid = int(message.text.split()[1])
        if uid in premium_users:
            bot.reply_to(message, "Este usuario ya es premium.")
        else:
            premium_users.append(uid)
            guardar_premium()
            bot.reply_to(message, f"Usuario {uid} añadido como premium.")
    except:
        bot.reply_to(message, "Uso correcto: /addpremium ID")

@bot.message_handler(commands=['removepremium'])
def remove_premium(message):
    if message.from_user.id != owner_id: return
    try:
        uid = int(message.text.split()[1])
        if uid in premium_users:
            premium_users.remove(uid)
            guardar_premium()
            bot.reply_to(message, f"Usuario {uid} removido del premium.")
        else:
            bot.reply_to(message, "Ese usuario no es premium.")
    except:
        bot.reply_to(message, "Uso correcto: /removepremium ID")

@bot.message_handler(commands=['listpremium'])
def list_premium(message):
    if message.from_user.id != owner_id: return
    msg = "Usuarios Premium:\n" if premium_users else "No hay usuarios premium."
    for uid in premium_users:
        msg += f"[Usuario](tg://user?id={uid}) - {uid}\n"
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['premiumstatus'])
def check_premium(message):
    status = "Eres usuario premium." if message.from_user.id in premium_users else "No eres usuario premium."
    bot.reply_to(message, status)

# Comandos administración
@bot.message_handler(commands=['ban'])
def ban_user(message):
    if message.from_user.id != owner_id: return bot.reply_to(message, "No tienes permiso.")
    try:
        uid = int(message.text.split()[1])
        if uid not in blacklist:
            blacklist.append(uid)
            guardar_blacklist()
            bot.reply_to(message, f"Baneado {uid}")
            try: bot.send_message(uid, "Has sido baneado de @LowQualityContentBot.")
            except: pass
        else:
            bot.reply_to(message, "Ya estaba baneado.")
    except:
        bot.reply_to(message, "Uso correcto: /ban ID")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if message.from_user.id != owner_id: return bot.reply_to(message, "No tienes permiso.")
    try:
        uid = int(message.text.split()[1])
        if uid in blacklist:
            blacklist.remove(uid)
            guardar_blacklist()
            bot.reply_to(message, f"Desbaneado {uid}")
        else:
            bot.reply_to(message, "No estaba baneado.")
    except:
        bot.reply_to(message, "Uso correcto: /unban ID")

@bot.message_handler(commands=['blacklist'])
def show_blacklist(message):
    if message.from_user.id != owner_id: return
    msg = "Blacklist:\n" if blacklist else "Blacklist vacía."
    for uid in blacklist:
        msg += f"[Usuario](tg://user?id={uid}) - {uid}\n"
    bot.reply_to(message, msg, parse_mode="Markdown")

# Stats
@bot.message_handler(commands=['stats'])
def show_stats(message):
    if message.from_user.id != owner_id: return
    msg = "Estadísticas de aportes:\n" if stats else "Sin stats."
    for uid, count in stats.items():
        msg += f"[Usuario](tg://user?id={uid}) - {count} aportes\n"
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['sendstats'])
def send_stats_to_channel(message):
    if message.from_user.id != owner_id: return
    msg = "STATS\n" if stats else "Sin stats."
    for uid, count in stats.items():
        if int(uid) not in blacklist:
            msg += f"[Usuario](tg://user?id={uid}) - {count} aportes\n"
    bot.send_message(admin, msg, parse_mode="Markdown")

@bot.message_handler(commands=['mystats'])
def my_stats(message):
    uid = str(message.from_user.id)
    count = stats.get(uid, 0)
    username = message.from_user.username or message.from_user.first_name
    text = (
        f"**Tus estadísticas personales:**\n\n"
        f"• Usuario: [@{username}](tg://user?id={uid})\n"
        f"• Aportes enviados: `{count}`\n"
    )
    if int(uid) in premium_users:
        text += "\n**Estado:** Usuario Premium"
    else:
        text += "\n**Estado:** Usuario Normal"
    bot.reply_to(message, text, parse_mode="Markdown")

# Confirmaciones /empty, /default o caption personalizado
@bot.message_handler(commands=['empty'])
def confirm_empty(message):
    if message.from_user.id in user_sessions:
        user_sessions[message.from_user.id]['caption'] = ''
        user_sessions[message.from_user.id]['confirmed'] = True
        bot.send_message(message.chat.id, "Caption vacía confirmada. Aporte enviado.")
        reenviar_aporte(message.from_user.id)

@bot.message_handler(commands=['default'])
def confirm_default(message):
    if message.from_user.id in user_sessions:
        post_from = f"Aporte de [{message.from_user.first_name}](tg://user?id={message.from_user.id}):"
        user_sessions[message.from_user.id]['caption'] = post_from
        user_sessions[message.from_user.id]['confirmed'] = True
        bot.send_message(message.chat.id, "Caption por defecto confirmada. Aporte enviado.")
        reenviar_aporte(message.from_user.id)

@bot.message_handler(func=lambda m: m.from_user.id in user_sessions and not user_sessions[m.from_user.id].get('confirmed'))
def caption_custom(message):
    user_sessions[message.from_user.id]['caption'] = message.text
    user_sessions[message.from_user.id]['confirmed'] = True
    bot.send_message(message.chat.id, "Caption personalizada confirmada. Aporte enviado.")
    reenviar_aporte(message.from_user.id)

# Enviar aporte al canal luego de confirmación
def reenviar_aporte(uid):
    session = user_sessions.pop(uid, None)
    if not session: return
    try:
        caption = session['caption']
        content_type = session['type']
        file_id = session['file_id']

        send_func = {
            'photo': bot.send_photo,
            'video': bot.send_video,
            'document': bot.send_document,
            'audio': bot.send_audio,
            'voice': bot.send_voice,
            'animation': bot.send_animation,
        }.get(content_type, None)

        if send_func:
            send_func(admin, file_id, caption=caption, parse_mode="Markdown")
        elif content_type == 'video_note':
            bot.send_message(admin, caption, parse_mode="Markdown")
            bot.send_video_note(admin, file_id)

        bot.send_message(uid, "Post enviado, verifica @LowQualityFamily")

    except Exception as e:
        bot.send_message(uid, f"Error al reenviar: {e}")

# Manejo general
@bot.message_handler(content_types=['text','photo','video','document','audio','voice','sticker','video_note','animation'])
def handle_media(message):
    user = message.from_user
    if user.id in blacklist:
        return

    uid = str(user.id)
    stats[uid] = stats.get(uid, 0) + 1
    guardar_stats()

    media_type = message.content_type

    if user.id in premium_users:
        try:
            file_id = None
            if media_type == 'photo':
                file_id = message.photo[-1].file_id
            elif media_type == 'video':
                file_id = message.video.file_id
            elif media_type == 'document':
                file_id = message.document.file_id
            elif media_type == 'audio':
                file_id = message.audio.file_id
            elif media_type == 'voice':
                file_id = message.voice.file_id
            elif media_type == 'animation':
                file_id = message.animation.file_id
            elif media_type == 'video_note':
                file_id = message.video_note.file_id

            if file_id:
                user_sessions[user.id] = {
                    'file_id': file_id,
                    'type': media_type,
                    'caption': '',
                    'confirmed': False
                }
                bot.send_message(message.chat.id,
                    "Como usuario premium puedes personalizar el mensaje del aporte. Responde con el mensaje que quieras usar como caption, o usa:\n/empty para enviar sin caption\n/default para usar la por defecto.")
            else:
                bot.send_message(message.chat.id, "Ese tipo de archivo no es permitido.")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ocurrió un error: {e}")
    else:
        try:
            post_from = f"Aporte de [{user.first_name}](tg://user?id={user.id}):"
            if media_type == 'photo':
                bot.send_photo(admin, message.photo[-1].file_id, caption=post_from, parse_mode="Markdown")
            elif media_type == 'video':
                bot.send_video(admin, message.video.file_id, caption=post_from, parse_mode="Markdown")
            elif media_type == 'document':
                bot.send_document(admin, message.document.file_id, caption=post_from, parse_mode="Markdown")
            elif media_type == 'audio':
                bot.send_audio(admin, message.audio.file_id, caption=post_from, parse_mode="Markdown")
            elif media_type == 'voice':
                bot.send_voice(admin, message.voice.file_id, caption=post_from, parse_mode="Markdown")
            elif media_type == 'video_note':
                bot.send_message(admin, post_from, parse_mode="Markdown")
                bot.send_video_note(admin, message.video_note.file_id)
            elif media_type == 'animation':
                bot.send_animation(admin, message.animation.file_id, caption=post_from, parse_mode="Markdown")
            else:
                bot.send_message(message.chat.id, "Tipo de contenido no permitido.")
                return
            bot.send_message(message.chat.id, "Post enviado, verifica @LowQualityFamily")
        except Exception as e:
            bot.send_message(message.chat.id, f"Ocurrió un error: {e}")

# Ejecutar
print("Bot corriendo...")

app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot corriendo'

def run_flask():
    app.run(host='0.0.0.0', port=8000)

# Inicia el servidor Flask en un hilo separado
threading.Thread(target=run_flask).start()
bot.polling()
