# ATNALTIK DUBBING — Backend

O'zbek anime sayti uchun to'liq backend. Flask + SQLite + Telegram bot integration.

## 🚀 Ishga tushirish

```bash
python run.py
```

Hammasi avtomatik: paketlar o'rnatiladi, DB yaratiladi, server ishga tushadi.

- **Sayt:** http://localhost:5000
- **Admin:** http://localhost:5000/admin
- **Login:** admin@atnaltik.uz / **admin123**

## 📁 Tuzilma

```
atnaltik/
├── run.py              ← Ishga tushirish (SHU FAYLNI ISHLATGING!)
├── app.py              ← Flask server + barcha route'lar
├── requirements.txt    ← Python paketlari
├── .env.example        ← Sozlamalar namunasi
├── database/
│   └── db.py           ← SQLite bazasi
├── templates/
│   ├── index.html      ← Asosiy sahifa
│   ├── admin/          ← Admin panel shablonlari
│   └── 404.html
└── static/
    ├── css/main.css    ← Stillar
    └── js/main.js      ← Frontend JS (API bilan)
```

## ⚙️ Sozlash

`.env.example` faylini `.env` deb nusxalang:

```bash
cp .env.example .env
```

Telegram bot token'ini kiriting:
```
TELEGRAM_BOT_TOKEN=sizning_token
TELEGRAM_BOT_USERNAME=ATNALTIK
ADMIN_CHAT_ID=sizning_telegram_id
```

## 🎬 Video Stream — Qanday ishlaydi?

### 1-usul: Telegram File ID (to'g'ridan-to'g'ri stream)
Admin panelda episode qo'shayotganda **Telegram File ID** kiriting.
Video `https://api.telegram.org/file/bot{TOKEN}/{file_path}` orqali stream qilinadi.

### 2-usul: Telegram URL (link)
Episode uchun kanal post linkini kiriting (`https://t.me/KANAL/123`).
Foydalanuvchi Telegram'ga yo'naltiriladi.

### File ID olish:
1. Botga video yuboring
2. Bot `/getUpdates` orqali `file_id` qaytaradi
3. Shu ID ni admin panelga kiriting

## 🤖 Telegram Bot Webhook

Bot token bilan server webhook qabul qiladi:
```
POST /bot/webhook
Header: X-Telegram-Bot-Api-Secret-Token: atnaltik-webhook
```

Admin chat'ga video yuborganingizda avtomatik `pending_videos` jadvaliga saqlanadi.

## 🔑 API Endpoints

| Method | URL | Tavsif |
|--------|-----|--------|
| GET | `/api/animes` | Barcha animelar (filter: genre, search, page) |
| GET | `/api/animes/{id}` | Anime + fasllar + qismlar |
| GET | `/api/latest-episodes` | Oxirgi qismlar |
| GET | `/api/stream/{ep_id}` | Video stream URL |
| GET | `/api/genres` | Barcha janrlar |
| POST | `/auth/login` | Kirish |
| POST | `/auth/register` | Ro'yxatdan o'tish |
| POST | `/auth/telegram` | Telegram orqali kirish |

## 🛠️ Admin Panel

- `/admin` — Dashboard (statistika)
- `/admin/animes` — Animelar ro'yxati
- `/admin/animes/add` — Yangi anime
- `/admin/animes/{id}/edit` — Tahrirlash + Fasl/qism qo'shish
- `/admin/genres` — Janrlar
- `/admin/users` — Foydalanuvchilar
