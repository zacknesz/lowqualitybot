import telebot
from telebot import types
import json
import os
import time
from flask import Flask
import threading
from threading import Thread

BOT_TOKEN = "7745916264:AAFaxmVrQsqiEjq5yhq6BdDQ7wBKjjb4Gn8"
bot = telebot.TeleBot(BOT_TOKEN)
admin = -1001862368664
owner_id = 7967939255

# Archivos
BLACKLIST_FILE = 'blacklist.json'
STATS_FILE = 'stats.json'
PREMIUM_FILE = 'premium.json'
PREMIUM_DAYS_FILE = 'premium_days.json'
REFERRALS_FILE = 'referrals.json'
ACCUMULATED_FILE = 'accumulated_days.json'
USERS_FILE = 'users.json'

# Cargar datos
blacklist = json.load(open(BLACKLIST_FILE)) if os.path.exists(BLACKLIST_FILE) else []
stats = json.load(open(STATS_FILE)) if os.path.exists(STATS_FILE) else {}
premium_users = json.load(open(PREMIUM_FILE)) if os.path.exists(PREMIUM_FILE) else []
premium_days = json.load(open(PREMIUM_DAYS_FILE)) if os.path.exists(PREMIUM_DAYS_FILE) else {}
referrals = json.load(open(REFERRALS_FILE)) if os.path.exists(REFERRALS_FILE) else {}
accumulated = json.load(open(ACCUMULATED_FILE)) if os.path.exists(ACCUMULATED_FILE) else {}
users = json.load(open(USERS_FILE)) if os.path.exists(USERS_FILE) else []

# Guardar funciones
def guardar_json(archivo, contenido):
    json.dump(contenido, open(archivo, 'w'))

def guardar_blacklist(): guardar_json(BLACKLIST_FILE, blacklist)
def guardar_stats(): guardar_json(STATS_FILE, stats)
def guardar_premium(): guardar_json(PREMIUM_FILE, premium_users)
def guardar_premium_days(): guardar_json(PREMIUM_DAYS_FILE, premium_days)
def guardar_referrals(): guardar_json(REFERRALS_FILE, referrals)
def guardar_accumulated(): guardar_json(ACCUMULATED_FILE, accumulated)
def guardar_users(): guardar_json(USERS_FILE, users)

# Expirar premium automáticamente
def verificar_expiraciones():
    while True:
        ahora = int(time.time())
        expirados = []
        for uid, ts in premium_days.items():
            if ahora >= ts:
                expirados.append(uid)
        for uid in expirados:
            if int(uid) in premium_users:
                premium_users.remove(int(uid))
                try:
                    bot.send_message(int(uid), "Tu suscripción premium ha expirado.")
                except:
                    pass
                guardar_premium()
        for uid in expirados:
            del premium_days[uid]
        guardar_premium_days()
        time.sleep(60)

Thread(target=verificar_expiraciones).start()

# Sesiones para edición de caption
user_sessions = {}

# Panel de administrador
@bot.message_handler(commands=['panel'])
def panel_admin(message):
    if message.from_user.id != owner_id: return
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("Ver listas", callback_data="ver_listas"),
        types.InlineKeyboardButton("Enviar broadcast", callback_data="broadcast")
    )
    bot.reply_to(message, "Panel de administración", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "ver_listas")
def ver_listas(call):
    if call.from_user.id != owner_id: return

    def mostrar(archivo, nombre):
        try:
            datos = json.load(open(archivo))
            if not datos:
                return f"• {nombre}: vacío"
            contenido = json.dumps(datos, indent=2)
            return f"• {nombre}:\n`{contenido}`"
        except:
            return f"• {nombre}: error al leer archivo"

    mensaje = (
        mostrar(ACCUMULATED_FILE, "Días acumulados") + "\n\n" +
        mostrar(BLACKLIST_FILE, "Blacklist") + "\n\n" +
        mostrar(PREMIUM_FILE, "Premium") + "\n\n" +
        mostrar(PREMIUM_DAYS_FILE, "Vencimientos") + "\n\n" +
        mostrar(REFERRALS_FILE, "Referidos") + "\n\n" +
        mostrar(STATS_FILE, "Estadísticas")
    )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("← Volver", callback_data="volver_panel"))
    bot.send_message(call.message.chat.id, mensaje, parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "volver_panel")
def volver_panel(call):
    panel_admin(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "broadcast")
def iniciar_broadcast(call):
    if call.from_user.id != owner_id: return
    msg = bot.send_message(call.message.chat.id, "Escribe el mensaje que deseas enviar a todos los usuarios:")
    bot.register_next_step_handler(msg, enviar_broadcast)

def enviar_broadcast(message):
    if message.from_user.id != owner_id: return
    texto = message.text
    bloqueados = 0
    for uid in users:
        try:
            bot.send_message(uid, texto)
        except:
            bloqueados += 1
    bot.reply_to(message, f"Broadcast enviado. Usuarios bloqueados: {bloqueados}")

# Registro de usuarios
@bot.message_handler(func=lambda m: True)
def registrar_usuario(message):
    if message.from_user.id not in users:
        users.append(message.from_user.id)
        guardar_users()

# Comando /start con sistema de referidos
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    text = message.text
    bienvenida = f"Hola, @{message.from_user.username or message.from_user.first_name}.\nBienvenido a @LowQualityContentBot. Envía un meme y será enviado a los admins para posteriormente publicarlo en el canal."

    # Procesar referido si viene con parámetro
    parts = text.split()
    if len(parts) > 1:
        ref_id = parts[1]
        if ref_id != user_id and user_id not in referrals:
            referrals.setdefault(ref_id, 0)
            referrals[ref_id] += 1
            guardar_referrals()

            # Acumular días
            accumulated_days.setdefault(ref_id, 0)
            if referrals[ref_id] % 5 == 0:
                accumulated_days[ref_id] += 1
                guardar_days()

    bot.reply_to(message, bienvenida)

# Comando para ver referidos y días acumulados
@bot.message_handler(commands=['referrals'])
def mostrar_referidos(message):
    uid = str(message.from_user.id)
    num_ref = referrals.get(uid, 0)
    dias = accumulated_days.get(uid, 0)
    enlace = f"https://t.me/LowQualityContentBot?start={uid}"
    msg = (
        f"**Sistema de Referidos**\n\n"
        f"• Referidos: `{num_ref}`\n"
        f"• Días acumulados: `{dias}`\n"
        f"• Enlace para invitar: [Click aquí]({enlace})"
    )
    bot.reply_to(message, msg, parse_mode="Markdown")

@bot.message_handler(commands=['canjear'])
def canjear_dias(message):
    uid = str(message.from_user.id)
    if uid not in accumulated_days:
        bot.reply_to(message, "No tienes días acumulados para canjear.")
        return

    partes = message.text.split()
    disponibles = accumulated_days.get(uid, 0)

    if len(partes) == 1:
        cantidad = disponibles
    else:
        try:
            cantidad = int(partes[1])
            if cantidad <= 0:
                raise ValueError()
        except:
            return bot.reply_to(message, "Uso: /canjear o /canjear [número de días]")

    if disponibles < cantidad:
        return bot.reply_to(message, f"No tienes suficientes días. Actualmente tienes `{disponibles}`.", parse_mode="Markdown")

    accumulated_days[uid] -= cantidad
    guardar_days()

    if message.from_user.id not in premium_users:
        premium_users.append(message.from_user.id)
        guardar_premium()

    bot.reply_to(message, f"¡Has canjeado `{cantidad}` día(s) premium!", parse_mode="Markdown")

@bot.message_handler(commands=['giftpremium'])
def gift_premium(message):
    partes = message.text.split()
    uid_emisor = str(message.from_user.id)

    if len(partes) < 3:
        return bot.reply_to(message,
            "Uso: `/giftpremium @usuario cantidad` o `/giftpremium user_id cantidad`\n\n"
            "Ejemplo: `/giftpremium @pepito 2`",
            parse_mode="Markdown"
        )

    objetivo = partes[1]
    try:
        cantidad = int(partes[2])
        if cantidad <= 0:
            raise ValueError
    except:
        return bot.reply_to(message, "La cantidad debe ser un número mayor a cero.")

    disponibles = accumulated_days.get(uid_emisor, 0)
    if disponibles < cantidad:
        return bot.reply_to(message, f"No tienes suficientes días. Disponibles: `{disponibles}`", parse_mode="Markdown")

    # Buscar por @username
    if objetivo.startswith('@'):
        found = False
        for user in bot.get_chat_administrators(admin):
            if user.user.username == objetivo[1:]:
                receptor_id = user.user.id
                found = True
                break
        if not found:
            return bot.reply_to(message, "No se encontró ese @username. Asegúrate de que el usuario haya iniciado el bot.")
    else:
        try:
            receptor_id = int(objetivo)
        except:
            return bot.reply_to(message, "ID inválido.")

    # Transferir días
    accumulated_days[uid_emisor] -= cantidad
    accumulated_days[str(receptor_id)] = accumulated_days.get(str(receptor_id), 0) + cantidad
    guardar_todo()

    bot.reply_to(message,
        f"Regalaste `{cantidad}` día(s) premium a [usuario](tg://user?id={receptor_id})",
        parse_mode="Markdown")
    try:
        bot.send_message(receptor_id,
            f"¡Has recibido `{cantidad}` día(s)` premium de [usuario](tg://user?id={message.from_user.id})!",
            parse_mode="Markdown")
    except:
        pass
# Resto de tu código original va debajo (no se modifica)
# ...
# (omito el resto aquí para que sea más claro el bloque agregado)

@bot.message_handler(commands=['help'])
def send_help(message):
    help_msg = "Información:\nOwner: @dicksonpussylover\nProgramado con python en 2h Lmao\n@dicksonpussylover\n@LowQualityFamily\n\nLista de comandos:\n/start - Bienvenida\n/help - Este mensaje\n/premiumstatus - Verificar si eres usuario premium y cuantos días tienes\n/mystats - Muestra cuantos aportes has hecho al canal\n/referrals - Panel de referidos (5 referidos = 1 día premium)\n/canjear - Canjeas tus días premium almacenados\n/giftpremium - Regala tus días premium"
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

# Comando premiumstatus actualizado
@bot.message_handler(commands=['premiumstatus'])
def check_premium(message):
    uid = str(message.from_user.id)
    if message.from_user.id in premium_users:
        if uid in premium_days:
            segundos_restantes = int(premium_days[uid]) - int(time.time())
            dias = max(1, segundos_restantes // 86400)
            bot.reply_to(message, f"Eres premium. Días restantes: {dias}")
        else:
            bot.reply_to(message, "Eres premium. (Días restantes no registrados)")
    else:
        bot.reply_to(message, "No eres usuario premium.")

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

# Web obligatoria para Koyeb
app = Flask(__name__)
@app.route('/')
def home():
    return 'Bot corriendo'

def run_flask():
    app.run(host='0.0.0.0', port=8000)

threading.Thread(target=run_flask).start()
bot.polling()
