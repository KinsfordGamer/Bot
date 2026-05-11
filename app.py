"""
ATNALTIK DUBBING — Backend Server
Flask + SQLite + Telegram Bot Integration
"""

import os
import sys
import json
import hashlib
import hmac
import threading
import time
from datetime import datetime, timedelta
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, send_from_directory,
    abort, Response, stream_with_context
)
from werkzeug.local import LocalProxy
from cachetools import TTLCache

# .env faylini yuklash
load_dotenv()

from telethon import TelegramClient, events
from telethon.tl.types import InputDocumentFileLocation
import asyncio

from database.db import Database

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'atnaltik-secret-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

db = Database()

# ─────────────────────────────────────────
#  TELETHON CLIENT INITIALIZATION
# ─────────────────────────────────────────
api_id = os.environ.get('TELEGRAM_API_ID')
api_hash = os.environ.get('TELEGRAM_API_HASH')
bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')

# Media cache (10 daqiqa davomida saqlaydi)
media_cache = TTLCache(maxsize=100, ttl=600)
loop = asyncio.new_event_loop()

def start_telethon():
    global client
    if not api_id or not api_hash or not bot_token or 'SIZNING' in api_id:
        print("⚠️ Telethon uchun API_ID yoki API_HASH sozlanmagan. Katta fayllar ishlamasligi mumkin.")
        return

    asyncio.set_event_loop(loop)
    client = TelegramClient('atnaltik_session', int(api_id), api_hash)
    # Tezlikni oshirish uchun parallel ulanishlar (MTProto)
    client.flood_sleep_threshold = 60
    client.start(bot_token=bot_token)
    print("🚀 Telethon Client (MTProto) ishga tushdi.")
    # Client global o'zgaruvchi sifatida initsializatsiya bo'lganini belgilaymiz
    app.config['TELETHON_READY'] = True
    loop.run_forever()

# Telethonni alohida threadda ishga tushiramiz
threading.Thread(target=start_telethon, daemon=True).start()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Tizimga kiring'}), 401
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        user = db.get_user(session['user_id'])
        if not user or not user['is_admin']:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def verify_telegram_auth(data: dict) -> bool:
    """Telegram Login Widget ma'lumotlarini tekshirish"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    if not bot_token:
        return True  # dev rejimida o'tkazib yuborish

    check_hash = data.pop('hash', '')
    data_check_arr = sorted([f"{k}={v}" for k, v in data.items()])
    data_check_string = '\n'.join(data_check_arr)

    secret_key = hashlib.sha256(bot_token.encode()).digest()
    hmac_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(hmac_hash, check_hash)

def send_telegram_message(chat_id, text, reply_to=None):
    """Telegramga xabar yuborish"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_to:
        payload['reply_to_message_id'] = reply_to
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram error: {e}")


# ─────────────────────────────────────────
#  FRONTEND ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    animes = db.get_all_animes()
    genres = db.get_all_genres()
    stats = db.get_stats()
    return render_template('index.html',
        animes=animes, genres=genres, stats=stats,
        tg_bot_username=os.environ.get('TELEGRAM_BOT_USERNAME', 'ATNALTIK')
    )

@app.route('/anime/<int:anime_id>')
def anime_detail(anime_id):
    anime = db.get_anime_with_seasons(anime_id)
    if not anime:
        abort(404)
    return render_template('anime_detail.html', 
        anime=anime,
        tg_bot_username=os.environ.get('TELEGRAM_BOT_USERNAME', 'ATNALTIK')
    )


# ─────────────────────────────────────────
#  API — ANIMES
# ─────────────────────────────────────────

@app.route('/api/animes')
def api_animes():
    genre = request.args.get('genre', '')
    search = request.args.get('search', '')
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    animes = db.get_animes_filtered(genre=genre, search=search, page=page, per_page=per_page)
    return jsonify(animes)

@app.route('/api/animes/<int:anime_id>')
def api_anime(anime_id):
    anime = db.get_anime_with_seasons(anime_id)
    if not anime:
        return jsonify({'error': 'Topilmadi'}), 404
    return jsonify(anime)

@app.route('/api/latest-episodes')
def api_latest_episodes():
    eps = db.get_latest_episodes(limit=12)
    return jsonify(eps)

@app.route('/api/stats')
def api_stats():
    return jsonify(db.get_stats())

@app.route('/api/genres')
def api_genres():
    return jsonify(db.get_all_genres())


# ─────────────────────────────────────────
#  API — VIDEO STREAM (Telegram proxy)
# ─────────────────────────────────────────

@app.route('/api/stream/<int:episode_id>')
def stream_episode(episode_id):
    """
    Katta fayllarni Telethon orqali, kichiklarini Bot API orqali stream qilish.
    """
    episode = db.get_episode(episode_id)
    if not episode:
        return jsonify({'error': 'Qism topilmadi'}), 404

    file_id = episode.get('telegram_file_id')
    chat_id = episode.get('telegram_chat_id')
    msg_id = episode.get('telegram_msg_id')
    
    if not file_id:
        if episode.get('telegram_url'):
            return jsonify({'type': 'link', 'url': episode['telegram_url']})
        return jsonify({'error': "Video mavjud emas"}), 404
    # 1. TELETHON ORQALI STREAM (400MB+ uchun)
    print(f"DEBUG: [{episode_id}] Telethon orqali stream qilishga urinish...")
    try:
        # Brauzerdan kelgan Range header'ni olish
        range_header = request.headers.get('Range', None)
        
        if not 'client' in globals() or not client.is_connected():
            print("⚠️ Telethon client hali tayyor emas.")
            raise Exception("Client not ready")

        # Media ob'ektini keshdan qidirish
        media = media_cache.get(f"ep_{episode_id}")
        
        if not media:
            # A) Agar chat_id va msg_id bo'lsa, xabarni o'zini olish (Eng ishonchli usul)
            if chat_id and msg_id:
                try:
                    target_chat = int(chat_id)
                    print(f"DEBUG: [{episode_id}] Xabarni chat_id={target_chat}, msg_id={msg_id} orqali olish...")
                    fut_msg = asyncio.run_coroutine_threadsafe(client.get_messages(target_chat, ids=int(msg_id)), loop)
                    msg = fut_msg.result(timeout=10)
                    if msg and msg.media:
                        media = msg.media
                        media_cache[f"ep_{episode_id}"] = media
                except Exception as me:
                    print(f"DEBUG: Xabarni olishda xato: {me}")

            # B) Agar xabar orqali topilmasa, file_id orqali urinib ko'rish
            if not media:
                fut_ent = asyncio.run_coroutine_threadsafe(client.get_input_entity(file_id), loop)
                media = fut_ent.result(timeout=10)
                media_cache[f"ep_{episode_id}"] = media
        
        file_size = getattr(media, 'size', 0)
        if hasattr(media, 'document'): # Agar media MessageMediaDocument bo'lsa
            file_size = media.document.size
            mime_type = media.document.mime_type
        else:
            mime_type = getattr(media, 'mime_type', 'video/mp4')
        
        print(f"DEBUG: [{episode_id}] Fayl topildi. Hajmi: {file_size} bytes, Mime: {mime_type}")

        start_byte = 0
        end_byte = file_size - 1
        status_code = 200
        
        if range_header:
            import re
            match = re.search(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                start_byte = int(match.group(1))
                if match.group(2):
                    end_byte = int(match.group(2))
                status_code = 206

        content_length = end_byte - start_byte + 1
        
        def generate_telethon():
            try:
                # Request_size ni 1MB ga oshiramiz (Tezroq yuklanishi uchun)
                # MTProto parallel yuklashni iter_download ichida o'zi boshqaradi (v1.24+)
                gen = client.iter_download(
                    media, 
                    offset=start_byte, 
                    request_size=1024*1024, # 1MB chunks
                    limit=content_length
                )
                while True:
                    fut_chunk = asyncio.run_coroutine_threadsafe(gen.__anext__(), loop)
                    try:
                        chunk = fut_chunk.result(timeout=20)
                        if chunk:
                            yield chunk
                    except StopAsyncIteration:
                        break
            except Exception as e:
                print(f"STREAM ERROR: {e}")

        headers = {
            'Content-Type': 'video/mp4', # Brauzerlar uchun MP4 deb majburlaymiz
            'Content-Length': str(content_length),
            'Accept-Ranges': 'bytes',
            'Access-Control-Allow-Origin': '*',
            'Content-Disposition': 'inline',
        }
        if range_header:
            headers['Content-Range'] = f'bytes {start_byte}-{end_byte}/{file_size}'

        return Response(
            generate_telethon(), 
            status=status_code, 
            headers=headers
        )
        
    except Exception as e:
        print(f"⚠️ Telethon Error: {e}")
        # Bot API ga o'tadi

    # 2. BOT API FALLBACK (Faqat <20MB uchun)
    print(f"DEBUG: [{episode_id}] Bot API (fallback) ishlatilmoqda...")
    bot_token_api = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    try:
        get_file_url = f"https://api.telegram.org/bot{bot_token_api}/getFile?file_id={file_id}"
        file_info = requests.get(get_file_url).json()
        
        if file_info.get('ok'):
            file_path = file_info['result']['file_path']
            f_size = file_info['result'].get('file_size', 0)
            
            if f_size > 20*1024*1024:
                print(f"❌ XATO: Fayl hajmi {f_size} bytes. Bot API 20MB dan kattasini bera olmaydi!")
                return jsonify({'error': 'Fayl juda katta. Telethon sozlanishi shart.', 'size': f_size}), 400

            download_url = f"https://api.telegram.org/file/bot{bot_token_api}/{file_path}"
            resp = requests.get(download_url, stream=True)
            
            def generate_bot():
                for chunk in resp.iter_content(chunk_size=16384):
                    yield chunk
            
            return Response(
                stream_with_context(generate_bot()),
                status=resp.status_code,
                headers={k: v for k, v in resp.headers.items() if k in ['Content-Type', 'Content-Length', 'Accept-Ranges', 'Content-Range']}
            )
    except: pass

    return jsonify({'type': 'link', 'url': episode.get('telegram_url', 'https://t.me/ATNALTIK')})


# ─────────────────────────────────────────
#  AUTH — Telegram Login Widget
# ─────────────────────────────────────────

@app.route('/auth/telegram', methods=['POST'])
def auth_telegram():
    data = request.json or {}
    if not verify_telegram_auth(dict(data)):
        return jsonify({'error': 'Autentifikatsiya xatosi'}), 403

    tg_id = str(data.get('id', ''))
    user = db.get_or_create_user_by_telegram(
        tg_id=tg_id,
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        username=data.get('username', ''),
        photo_url=data.get('photo_url', ''),
    )
    session['user_id'] = user['id']
    session.permanent = True
    return jsonify({'success': True, 'user': {'name': user['first_name'], 'id': user['id']}})

@app.route('/auth/login', methods=['POST'])
def auth_login():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    user = db.login_user(email, password)
    if not user:
        return jsonify({'error': 'Email yoki parol xato'}), 401
    session['user_id'] = user['id']
    session.permanent = True
    return jsonify({'success': True, 'user': {'name': user['first_name'], 'id': user['id']}})

@app.route('/auth/register', methods=['POST'])
def auth_register():
    data = request.json or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    name = data.get('name', '').strip()
    if not email or not password or not name:
        return jsonify({'error': "Barcha maydonlarni to'ldiring"}), 400
    if db.user_exists(email):
        return jsonify({'error': 'Bu email allaqachon ro\'yxatdan o\'tgan'}), 409
    user = db.create_user(email=email, password=password, first_name=name)
    session['user_id'] = user['id']
    session.permanent = True
    return jsonify({'success': True, 'user': {'name': user['first_name'], 'id': user['id']}})

@app.route('/auth/logout')
def auth_logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/auth/me')
def auth_me():
    if 'user_id' not in session:
        return jsonify({'logged_in': False})
    user = db.get_user(session['user_id'])
    if not user:
        session.clear()
        return jsonify({'logged_in': False})
    return jsonify({
        'logged_in': True,
        'user': {'name': user['first_name'], 'id': user['id'], 'is_admin': user['is_admin']}
    })


# ─────────────────────────────────────────
#  ADMIN PANEL
# ─────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = db.get_stats()
    recent_animes = db.get_all_animes()[:5]
    return render_template('admin/dashboard.html', stats=stats, recent_animes=recent_animes)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        admin_user = db.check_admin(username, password)
        if admin_user:
            session['user_id'] = admin_user['id']
            session.permanent = True
            return redirect(url_for('admin_dashboard'))
        return render_template('admin/login.html', error="Noto'g'ri ma'lumotlar")
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))

# ── ADMIN: ANIMES ──

@app.route('/admin/animes')
@admin_required
def admin_animes():
    animes = db.get_all_animes()
    return render_template('admin/animes.html', animes=animes)

@app.route('/admin/animes/add', methods=['GET', 'POST'])
@admin_required
def admin_add_anime():
    genres = db.get_all_genres()
    if request.method == 'POST':
        data = {
            'title': request.form.get('title', ''),
            'original_title': request.form.get('original_title', ''),
            'icon': request.form.get('icon', '🎬'),
            'score': float(request.form.get('score') or 0),
            'status': request.form.get('status', 'Davom etmoqda'),
            'year': int(request.form.get('year') or datetime.now().year),
            'description': request.form.get('description', ''),
            'genres': request.form.getlist('genres'),
            'cover_image': request.form.get('cover_image', ''),
        }
        anime_id = db.add_anime(data)
        return redirect(url_for('admin_anime_edit', anime_id=anime_id))
    return render_template('admin/anime_form.html', anime=None, genres=genres, action='add')

@app.route('/admin/animes/<int:anime_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_anime_edit(anime_id):
    anime = db.get_anime_with_seasons(anime_id)
    if not anime:
        abort(404)
    all_genres = db.get_all_genres()
    if request.method == 'POST':
        data = {
            'id': anime_id,
            'title': request.form.get('title', ''),
            'original_title': request.form.get('original_title', ''),
            'icon': request.form.get('icon', '🎬'),
            'score': float(request.form.get('score') or 0),
            'status': request.form.get('status', 'Davom etmoqda'),
            'year': int(request.form.get('year') or 2024),
            'description': request.form.get('description', ''),
            'genres': request.form.getlist('genres'),
            'cover_image': request.form.get('cover_image', ''),
        }
        db.update_anime(data)
        return redirect(url_for('admin_anime_edit', anime_id=anime_id))
    return render_template('admin/anime_form.html', anime=anime, genres=all_genres, action='edit')

@app.route('/admin/animes/<int:anime_id>/delete', methods=['POST'])
@admin_required
def admin_delete_anime(anime_id):
    db.delete_anime(anime_id)
    return redirect(url_for('admin_animes'))

# ── ADMIN: SEASONS ──

@app.route('/admin/animes/<int:anime_id>/seasons/add', methods=['POST'])
@admin_required
def admin_add_season(anime_id):
    data = {
        'anime_id': anime_id,
        'title': request.form.get('title', ''),
        'year': int(request.form.get('year') or datetime.now().year),
        'order_num': int(request.form.get('order_num') or 1),
    }
    db.add_season(data)
    return redirect(url_for('admin_anime_edit', anime_id=anime_id))

@app.route('/admin/seasons/<int:season_id>/delete', methods=['POST'])
@admin_required
def admin_delete_season(season_id):
    season = db.get_season(season_id)
    db.delete_season(season_id)
    return redirect(url_for('admin_anime_edit', anime_id=season['anime_id']))

# ── ADMIN: EPISODES ──

@app.route('/admin/seasons/<int:season_id>/episodes/add', methods=['POST'])
@admin_required
def admin_add_episode(season_id):
    season = db.get_season(season_id)
    data = {
        'season_id': season_id,
        'anime_id': season['anime_id'],
        'num': int(request.form.get('num') or 1),
        'title': request.form.get('title', ''),
        'duration': request.form.get('duration', '24 dq'),
        'telegram_url': request.form.get('telegram_url', ''),
        'telegram_file_id': request.form.get('telegram_file_id', ''),
        'telegram_chat_id': request.form.get('telegram_chat_id', ''),
        'telegram_msg_id': request.form.get('telegram_msg_id') or None,
        'telegram_file_path': request.form.get('telegram_file_path', ''),
        'is_new': request.form.get('is_new') == 'on',
    }
    db.add_episode(data)
    return redirect(url_for('admin_anime_edit', anime_id=season['anime_id']))

@app.route('/admin/episodes/<int:ep_id>/delete', methods=['POST'])
@admin_required
def admin_delete_episode(ep_id):
    ep = db.get_episode(ep_id)
    season = db.get_season(ep['season_id'])
    db.delete_episode(ep_id)
    return redirect(url_for('admin_anime_edit', anime_id=season['anime_id']))

@app.route('/admin/episodes/<int:ep_id>/toggle-new', methods=['POST'])
@admin_required
def admin_toggle_new(ep_id):
    db.toggle_episode_new(ep_id)
    ep = db.get_episode(ep_id)
    season = db.get_season(ep['season_id'])
    return redirect(url_for('admin_anime_edit', anime_id=season['anime_id']))

# ── ADMIN: GENRES ──

@app.route('/admin/genres')
@admin_required
def admin_genres():
    genres = db.get_all_genres()
    return render_template('admin/genres.html', genres=genres)

@app.route('/admin/genres/add', methods=['POST'])
@admin_required
def admin_add_genre():
    data = {
        'name': request.form.get('name', ''),
        'icon': request.form.get('icon', '🎭'),
        'color': request.form.get('color', 'rgba(100,100,100,0.15)'),
    }
    db.add_genre(data)
    return redirect(url_for('admin_genres'))

@app.route('/admin/genres/<int:genre_id>/delete', methods=['POST'])
@admin_required
def admin_delete_genre(genre_id):
    db.delete_genre(genre_id)
    return redirect(url_for('admin_genres'))

# ── ADMIN: USERS ──

@app.route('/admin/users')
@admin_required
def admin_users():
    users = db.get_all_users()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<int:user_id>/toggle-admin', methods=['POST'])
@admin_required
def admin_toggle_user_admin(user_id):
    db.toggle_admin(user_id)
    return redirect(url_for('admin_users'))


# ─────────────────────────────────────────
#  TELEGRAM BOT (inline mode)
# ─────────────────────────────────────────

def handle_bot_update(update):
    """Telegram bot xabarlarini qayta ishlash logikasi"""
    if 'message' in update:
        msg = update['message']
        chat_id = msg['chat']['id']
        text = msg.get('text', '').strip()
        admin_id = os.environ.get('ADMIN_CHAT_ID', '')

        # 1. /start buyrug'i
        if text.startswith('/start'):
            welcome_text = (
                "<b>Salom! ATNALTIK DUBBING botiga xush kelibsiz!</b>\n\n"
                "Ushbu bot orqali saytga video yuklash uchun videoni yuboring.\n"
                "Sizga videoning <code>file_id</code> sini qaytaraman."
            )
            send_telegram_message(chat_id, welcome_text)
            print(f"DEBUG: /start command handled for {chat_id}")
            return

        # 2. Video yoki Document yuborilganda
        video_obj = msg.get('video') or msg.get('document')
        
        # Agar document bo'lsa, u video ekanligini tekshirish
        if msg.get('document') and not msg['document'].get('mime_type', '').startswith('video/'):
            # Faqat video fayllarni qabul qilamiz
            if not msg.get('video'):
                return

        if video_obj:
            file_id = video_obj['file_id']
            file_name = video_obj.get('file_name', 'video.mp4')
            
            # Admin bo'lsa avtomatik saqlash
            if str(chat_id) == admin_id:
                caption = msg.get('caption', '')
                db.save_pending_video(file_id=file_id, caption=caption, chat_id=chat_id, message_id=msg['message_id'])
                resp_text = (
                    f"✅ <b>Video/Fayl qabul qilindi!</b>\n\n"
                    f"📂 Fayl nomi: <code>{file_name}</code>\n"
                    f"🆔 File ID: <code>{file_id}</code>\n"
                    f"🆔 Chat ID: <code>{chat_id}</code>\n"
                    f"🆔 Msg ID: <code>{msg['message_id']}</code>\n\n"
                    "Ushbu ma'lumotlarni sayt admin panelida ishlating."
                )
            else:
                resp_text = (
                    f"📂 <b>Video ma'lumotlari:</b>\n\n"
                    f"🆔 File ID: <code>{file_id}</code>\n"
                    f"🆔 Chat ID: <code>{chat_id}</code>\n"
                    f"🆔 Msg ID: <code>{msg['message_id']}</code>\n\n"
                    "Ushbu ma'lumotlarni saytda ishlatishingiz mumkin."
                )
            
            send_telegram_message(chat_id, resp_text, reply_to=msg['message_id'])
            print(f"DEBUG: Video/Doc handled for {chat_id}, file_id: {file_id}")

@app.route('/bot/webhook', methods=['POST'])
def bot_webhook():
    """Telegram bot webhook — yangi videolar qo'shilganda"""
    # Xavfsizlik tekshiruvi (agar WEBHOOK_SECRET sozlangan bo'lsa)
    secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token', '')
    webhook_secret = os.environ.get('WEBHOOK_SECRET', 'atnaltik-webhook')
    if secret and secret != webhook_secret:
        return 'Forbidden', 403

    update = request.json
    if update:
        handle_bot_update(update)

    return 'OK'

def run_bot_polling():
    """Webhooksiz ishlash uchun background polling"""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        print("⚠️ BOT_TOKEN topilmadi, polling ishga tushmadi.")
        return

    # Webhookni o'chirish (getUpdates ishlashi uchun shart)
    try:
        requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
        print("🗑️ Telegram Webhook o'chirildi (Polling rejimida ishlash uchun)")
    except: pass

    print("🚀 Telegram Bot polling rejimida ishga tushdi...")
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{token}/getUpdates?offset={offset}&timeout=30"
            resp = requests.get(url, timeout=35).json()
            if resp.get('ok'):
                for update in resp.get('result', []):
                    handle_bot_update(update)
                    offset = update['update_id'] + 1
        except Exception as e:
            print(f"⚠️ Polling error: {e}")
            time.sleep(5)
        time.sleep(0.5)


# ─────────────────────────────────────────
#  ERROR HANDLERS
# ─────────────────────────────────────────

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'true').lower() == 'true'
    
    # Bot pollingni alohida threadda ishga tushirish
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()
    
    print(f"\n{'='*50}")
    print(f"  ATNALTIK DUBBING — Server ishga tushdi")
    print(f"  URL: http://localhost:{port}")
    print(f"  Admin: http://localhost:{port}/admin")
    print(f"  Bot rejim: Polling (Background)")
    print(f"{'='*50}\n")
    
    app.run(host='0.0.0.0', port=port, debug=debug, use_reloader=False)
