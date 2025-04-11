import telebot
from telebot import types
from flask import Flask
from threading import Thread
import threading
import json
import os
import time
import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "7745916264:AAFaxmVrQsqiEjq5yhq6BdDQ7wBKjjb4Gn8"
bot = telebot.TeleBot(BOT_TOKEN)
admin = -1001862368664
owner_id = 7967939255

# Archivos y almacenamiento
BLACKLIST_FILE = 'blacklist.json'
STATS_FILE = 'stats.json'
PREMIUM_FILE = 'premium.json'
REFERRALS_FILE = 'referrals.json'
ACCUMULATED_FILE = 'accumulated_days.json'
PREMIUM_DAYS_FILE = 'premium_days.json'
USERS_FILE = 'users.json'

# Cargar listas
blacklist = json.load(open(BLACKLIST_FILE)) if os.path.exists(BLACKLIST_FILE) else []
stats = json.load(open(STATS_FILE)) if os.path.exists(STATS_FILE) else {}
premium_users = json.load(open(PREMIUM_FILE)) if os.path.exists(PREMIUM_FILE) else []
referrals = json.load(open(REFERRALS_FILE)) if os.path.exists(REFERRALS_FILE) else {}
accumulated = json.load(open(ACCUMULATED_FILE)) if os.path.exists(ACCUMULATED_FILE) else {}
premium_days = json.load(open(PREMIUM_DAYS_FILE)) if os.path.exists(PREMIUM_DAYS_FILE) else {}
users = json.load(open(USERS_FILE)) if os.path.exists(USERS_FILE) else []

# Guardar listas
def guardar_blacklist(): json.dump(blacklist, open(BLACKLIST_FILE, 'w'))
def guardar_stats(): json.dump(stats, open(STATS_FILE, 'w'))
def guardar_premium(): json.dump(premium_users, open(PREMIUM_FILE, 'w'))
def guardar_referrals(): json.dump(referrals, open(REFERRALS_FILE, 'w'))
def guardar_accumulated(): json.dump(accumulated, open(ACCUMULATED_FILE, 'w'))
def guardar_premium_days(): json.dump(premium_days, open(PREMIUM_DAYS_FILE, 'w'))
def guardar_users(): json.dump(users, open(USERS_FILE, 'w'))

# Verificación de expiraciones
def verificar_expiraciones():
    while True:
        for uid in list(premium_days.keys()):
            if premium_days[uid] <= int(time.time()):
                if int(uid) in premium_users:
                    premium_users.remove(int(uid))
                    guardar_premium()
                premium_days.pop(uid)
                guardar_premium_days()
                try:
                    bot.send_message(int(uid), "Tu suscripción premium ha expirado.")
                except: pass
        time.sleep(3600)
Thread(target=verificar_expiraciones).start()

# Sesiones para edición de caption
user_sessions = {}

# Comando /panel (solo admin)
@bot.message_handler(commands=['panel'])
def admin_panel(message):
    if message.from_user.id != owner_id:
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📄 Ver listas", callback_data='ver_listas'))
    markup.add(types.InlineKeyboardButton("📢 Enviar broadcast", callback_data='broadcast_inicio'))
    bot.send_message(message.chat.id, "Panel de administrador:", reply_markup=markup)

# Callback para el panel
@bot.callback_query_handler(func=lambda call: True)
def panel_callbacks(call):
    if call.from_user.id != owner_id:
        return

    if call.data == 'ver_listas':
        datos = {
            'Premium': premium_users,
            'PremiumDays': premium_days,
            'Blacklist': blacklist,
            'Stats': stats,
            'Referrals': referrals,
            'Accumulated': accumulated
        }

        texto = "**Listas del bot:**\n\n"
        for nombre, data in datos.items():
            if not data:
                texto += f"• {nombre}: Vacía\n"
            else:
                texto += f"• {nombre}: {len(data)} elementos\n"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅ Volver", callback_data='volver_panel'))
        bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                              text=texto, reply_markup=markup, parse_mode="Markdown")

    elif call.data == 'broadcast_inicio':
        broadcast_state[call.from_user.id] = True
        bot.send_message(call.message.chat.id, "Envía el mensaje que deseas reenviar a todos los usuarios registrados.")

    elif call.data == 'volver_panel':
        admin_panel(call.message)

# Broadcast: espera mensaje
broadcast_state = {}

@bot.message_handler(func=lambda m: m.chat.id == owner_id and m.reply_to_message and m.reply_to_message.text == "Escribe el mensaje que quieres enviar a todos los usuarios:")
def handle_broadcast(m):
    if not users:
        return bot.reply_to(m, "No hay usuarios registrados para enviar el mensaje.")
    if m.from_user.id != owner_id:
        return

    del broadcast_state[m.from_user.id]
    bloqueados = 0
    enviados = 0
    for uid in users:
        try:
            if m.content_type == "text":
                bot.send_message(uid, m.text, parse_mode="Markdown")
            elif m.content_type in ["photo", "video", "document", "audio", "animation", "voice"]:
                file_id = getattr(m, m.content_type).file_id
                send_func = getattr(bot, f"send_{m.content_type}")
                send_func(uid, file_id, caption=m.caption or "", parse_mode="Markdown")
            else:
                continue
            enviados += 1
        except:
            bloqueados += 1

    bot.send_message(m.chat.id, f"✅ Mensaje reenviado a {enviados} usuarios.\n❌ Usuarios bloqueados: {bloqueados}")

@bot.message_handler(commands=['start'])
def registrar_usuario(message):
    uid = message.from_user.id
    if uid not in users:
        users.append(uid)
        guardar_users()

    argumentos = message.text.split()
    if len(argumentos) > 1:
        referidor = argumentos[1]
        if str(uid) == referidor:
            bot.reply_to(message, "No puedes referirte a ti mismo.")
            return
        if str(uid) in referrals:
            bot.reply_to(message, "Ya fuiste referido por alguien.")
            return
        if int(referidor) in blacklist:
            bot.reply_to(message, "Este referidor no es válido.")
            return

        referrals[str(uid)] = referidor
        guardar_referrals()

        # Sumar al referidor
        accumulated[referidor] = accumulated.get(referidor, 0) + 1
        guardar_accumulated()

        total = accumulated.get(referidor, 0)
        if total % 5 == 0:
            premium_users.append(int(referidor))
            guardar_premium()
            premium_days[referidor] = int(time.time()) + 86400
            guardar_premium_days()
            try:
                bot.send_message(int(referidor), "¡Has recibido 1 día de premium por tus referidos!")
            except: pass

        # Dar al nuevo usuario 1 día de premium como prueba
        if int(uid) not in premium_users:
        	premium_users.append(int(uid))
        	guardar_premium()
        guardar_premium()
        premium_days[str(uid)] = int(time.time()) + 86400
        guardar_premium_days()
        try:
            bot.send_message(uid, "¡Has recibido 1 día de premium como regalo por registrarte con un referido!")
        except: pass

    bot.reply_to(message, f"Bienvenido @{message.from_user.username}\nEnvia un meme y será enviado al canal\n@LowQualityFamily")

# /referrals
@bot.message_handler(commands=['referrals'])
def mostrar_referrals(message):
    uid = str(message.from_user.id)
    cantidad = sum(1 for v in referrals.values() if v == uid)
    dias = accumulated.get(uid, 0)
    link = f"https://t.me/LowQualityContentBot?start={uid}"
    texto = f"Has referido a {cantidad} usuarios.\nDías premium acumulados: {dias}\nComparte este link para conseguir más: {link}"
    bot.reply_to(message, texto)

# /canjear [n]
@bot.message_handler(commands=['canjear'])
def canjear_dias(message):
    uid = str(message.from_user.id)
    args = message.text.split()
    dias = accumulated.get(uid, 0)

    if len(args) == 1:
        if dias == 0:
            bot.reply_to(message, "No tienes días premium acumulados.")
            return
        if int(uid) not in premium_users:
        	premium_users.append(int(uid))
        	guardar_premium()
        guardar_premium()
        premium_days[uid] = int(time.time()) + dias * 86400
        accumulated.pop(uid)
        guardar_accumulated()
        guardar_premium_days()
        bot.reply_to(message, f"Has canjeado {dias} día(s) premium.")
    elif len(args) == 2:
        try:
            n = int(args[1])
            if n <= 0 or dias < n:
                return bot.reply_to(message, "No tienes suficientes días.")
            if int(uid) not in premium_users:
            	premium_users.append(int(uid))
            	guardar_premium()
            guardar_premium()
            premium_days[uid] = int(time.time()) + n * 86400
            accumulated[uid] -= n
            if accumulated[uid] == 0:
                accumulated.pop(uid)
            guardar_accumulated()
            guardar_premium_days()
            bot.reply_to(message, f"Has canjeado {n} día(s) premium.")
        except:
            bot.reply_to(message, "Uso: /canjear o /canjear 1")

# /premiumstatus
@bot.message_handler(commands=['premiumstatus'])
def estado_premium(message):
    user_id = str(message.from_user.id)
    if user_id in premium_users:
        dias = premium_days.get(user_id, 0)
        bot.reply_to(message, f"Eres usuario premium.\nDías restantes: {dias}")
    else:
        bot.reply_to(message, "No eres usuario premium.")

# /giftpremium @username X ó /giftpremium ID X
@bot.message_handler(commands=['giftpremium'])
def regalar_premium(message):
    args = message.text.split()
    if len(args) != 3:
        return bot.reply_to(message, "Uso: /giftpremium @username 1 o /giftpremium ID 1")

    destino = args[1]
    try:
        dias = int(args[2])
        if dias <= 0:
            raise ValueError()
    except:
        return bot.reply_to(message, "Días inválidos.")

    remitente = str(message.from_user.id)
    if accumulated.get(remitente, 0) < dias:
        return bot.reply_to(message, "No tienes suficientes días acumulados.")

    if destino.startswith("@"):
        try:
            usuario = bot.get_chat(destino)
            uid = str(usuario.id)
        except:
            return bot.reply_to(message, "No se pudo encontrar al usuario.")
    else:
        uid = destino

    accumulated[remitente] -= dias
    if accumulated[remitente] == 0:
        accumulated.pop(remitente)
    guardar_accumulated()

    if int(uid) not in premium_users:
    	premium_users.append(int(uid))
    	guardar_premium()
    guardar_premium()
    premium_days[uid] = int(time.time()) + dias * 86400
    guardar_premium_days()

    try:
        bot.send_message(int(uid), f"¡Has recibido {dias} día(s) premium de regalo!")
    except: pass
    bot.reply_to(message, f"Has enviado {dias} día(s) premium a {destino}.")

# Resto de tu código original va debajo (no se modifica)
# ...
# (omito el resto aquí para que sea más claro el bloque agregado)

@bot.message_handler(commands=['sugerencia'])
def recibir_sugerencia(message):
    texto = message.text.replace("/sugerencia", "").strip()
    if not texto:
        bot.reply_to(message, "Por favor, escribe tu sugerencia luego del comando.\nEjemplo: /sugerencia Podrían agregar más funciones divertidas.")
        return

    user = message.from_user
    uid = user.id
    username = user.username or "Sin username"
    nombre_link = f"[{user.first_name}](tg://user?id={uid})"
    mensaje = f"**Nueva sugerencia recibida:**\n\n"
    mensaje += f"• Usuario: {nombre_link}\n"
    mensaje += f"• ID: `{uid}`\n"
    mensaje += f"• Username: @{username if username != 'Sin username' else 'N/A'}\n"
    mensaje += f"• Mensaje:\n`{texto}`"

    try:
        bot.send_message(owner_id, mensaje, parse_mode="Markdown")
        bot.reply_to(message, "¡Gracias por tu sugerencia! Ha sido enviada al administrador.")
    except Exception as e:
        bot.reply_to(message, f"No se pudo enviar la sugerencia. {e}")
        bot.send_message(owner_id, f"Error: {e}\n Provocado por {message.from_user.id}")

@bot.message_handler(commands=['apelacion'])
def enviar_apelacion(message):
    uid = message.from_user.id
    args = message.text.split(maxsplit=1)
    if len(args) == 1:
        return bot.reply_to(message, "Por favor escribe tu apelación después del comando.\nEjemplo:\n`/apelacion Fui baneado injustamente.`", parse_mode="Markdown")

    apelacion = args[1]
    username = message.from_user.username
    nombre = f"[{message.from_user.first_name}](tg://user?id={uid})"

    texto = (
        f"**Nueva apelación recibida:**\n\n"
        f"• Usuario: @{username}\n"
        f"• Apelación:\n`{apelacion}`" if username else f"**Nueva apelación recibida:**\n\n"
        f"• Usuario: {nombre}"
        f"\n• ID: `{uid}`\n"
        f"• Apelación:\n`{apelacion}`"
        )
    
    try:
        bot.send_message(owner_id, texto, parse_mode="Markdown")
        bot.reply_to(message, "Tu apelación fue enviada al administrador.\nEn todo caso se recomienda contactar al administrador: @zacknezzz")
    except:
        bot.reply_to(message, "Ocurrió un error al enviar tu apelación.")
                   
@bot.message_handler(commands=['help'])
def send_help(message):
    help_msg = "Información:\nOwner: @LowQualityFamily\nLista de comandos:\n/start - Bienvenida\n/help - Este mensaje\n/premiumstatus - Tu estado actual\n/referrals - Tus referidos\n/canjear - Canjear tus días premium acumulados\n/giftpremium - Regalar tus días premium\n/sugerencia - Sugierenos algo!\n/apelacion - Apela alguna indiferencia experimentada con el bot"
    bot.reply_to(message, help_msg)

# Comandos premium

@bot.message_handler(commands=['addreferrals'])
def add_referrals(message):
    if message.from_user.id != owner_id: return
    try:
        uid = str(message.text.split()[1])
        cantidad = int(message.text.split()[2])
        accumulated[uid] = accumulated.get(uid, 0) + cantidad
        guardar_accumulated()
        bot.reply_to(message, f"{cantidad} referidos añadidos a {uid}.")
    except:
        bot.reply_to(message, "Uso: /addreferrals user_id cantidad")

@bot.message_handler(commands=['removereferrals'])
def admin_remove_referrals(message):
    if message.from_user.id != owner_id:
        return bot.reply_to(message, "No tienes permiso.")
    try:
        parts = message.text.split()
        uid = str(int(parts[1]))
        cantidad = int(parts[2])
        referrals[uid] = max(referrals.get(uid, 0) - cantidad, 0)
        guardar_referrals()
        bot.reply_to(message, f"{cantidad} referidos removidos de {uid}")
    except:
        bot.reply_to(message, "Uso correcto: /removereferrals user_id cantidad")

@bot.message_handler(commands=['adddays'])
def admin_add_days(message):
    if message.from_user.id != owner_id:
        return bot.reply_to(message, "No tienes permiso.")
    try:
        parts = message.text.split()
        uid = str(int(parts[1]))
        cantidad = int(parts[2])
        accumulated[uid] = accumulated.get(uid, 0) + cantidad
        guardar_accumulated()
        bot.reply_to(message, f"{cantidad} días añadidos a {uid}")
    except:
        bot.reply_to(message, "Uso correcto: /adddays user_id cantidad")

@bot.message_handler(commands=['removedays'])
def admin_remove_days(message):
    if message.from_user.id != owner_id:
        return bot.reply_to(message, "No tienes permiso.")
    try:
        parts = message.text.split()
        uid = str(int(parts[1]))
        cantidad = int(parts[2])
        accumulated[uid] = max(accumulated.get(uid, 0) - cantidad, 0)
        guardar_accumulated()
        bot.reply_to(message, f"{cantidad} días removidos de {uid}")
    except:
        bot.reply_to(message, "Uso correcto: /removedays user_id cantidad")

@bot.message_handler(commands=['addpremium'])
def add_premium(message):
    if message.from_user.id != owner_id: return
    try:
        uid = int(message.text.split()[1])
        if uid in premium_users:
            bot.reply_to(message, "Este usuario ya es premium.")
        else:
            if int(uid) not in premium_users:
            	premium_users.append(int(uid))
            	guardar_premium()
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
        text += f"\n**Estado:** Usuario Premium"
    else:
        text += f"\n**Estado:** Usuario Normal"

    # Mostrar días acumulados si existen
    dias = accumulated.get(uid, 0)
    if dias > 0:
        text += f"\n• Días premium acumulados: `{dias}`"

    # Mostrar progreso hacia nueva recompensa
    restante = 100 - (count % 100)
    if restante != 100:
        text += f"\n• Te faltan `{restante}` aportes para ganar +3 días premium"
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
        bot.send_message(owner_id, f"Error al reenviar: {e}\nUsuario que lo provocó: " + uid)

# Manejo general
@bot.message_handler(content_types=['text','photo','video','document','audio','voice','sticker','video_note','animation'])
def handle_media(message):
    user = message.from_user
    if user.id in blacklist:
        return

    uid = str(user.id)
    stats[uid] = stats.get(uid, 0) + 1
    guardar_stats()
    # Recompensa por cada 100 aportes
    if stats[uid] % 100 == 0:
        accumulated[uid] = accumulated.get(uid, 0) + 3
        guardar_accumulated()
        try:
            bot.send_message(user.id, "¡Felicidades! Has recibido 3 días premium por llegar a 100 aportes.")
        except: pass

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
            bot.send_message(owner_id, f"Ocurrió un error: {e}\nUsuario que lo provocó {message.from_user.id}")
            	
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
            bot.send_message(owner_id, f"Ocurrió un error: {e}\nUsuario que lo provocó {message.from_user.id}")

# Web obligatoria para Koyeb
app = Flask(__name__)
@app.route('/')
def home():
    return 'Bot corriendo'

def run_flask():
    app.run(host='0.0.0.0', port=8000)

threading.Thread(target=run_flask).start()
bot.polling()