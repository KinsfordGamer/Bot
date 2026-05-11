#!/usr/bin/env python3
"""
ATNALTIK DUBBING — Ishga tushirish skripti
Barcha paketlarni o'rnatib, serverni avtomatik ishga tushiradi.
"""

import sys
import os
import subprocess
from dotenv import load_dotenv

# .env faylini yuklash
load_dotenv()

def install_requirements():
    print("📦 Paketlar tekshirilmoqda...")
    req_file = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    try:
        import flask
        import telethon
        import dotenv
        print("✅ Barcha paketlar allaqachon o'rnatilgan")
    except ImportError:
        print("⬇️  Zarur paketlar o'rnatilmoqda (bu bir oz vaqt olishi mumkin)...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', req_file, '-q'])
        print("✅ Paketlar muvaffaqiyatli o'rnatildi")

def main():
    print("=" * 50)
    print("  ATNALTIK DUBBING — O'zbek anime sayti")
    print("=" * 50)

    install_requirements()

    # Working directory ni loyiha papkasiga o'zgartirish
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # Flask app'ni import qilish va ishga tushirish
    sys.path.insert(0, script_dir)

    from app import app, db

    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '0.0.0.0')
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'

    import threading
    from app import run_bot_polling

    # Bot pollingni alohida threadda ishga tushirish
    bot_thread = threading.Thread(target=run_bot_polling, daemon=True)
    bot_thread.start()

    print(f"\n✅ Ma'lumotlar bazasi tayyor")
    print(f"🌐 Sayt: http://localhost:{port}")
    print(f"🔧 Admin: http://localhost:{port}/admin")
    print(f"🤖 Bot rejim: Polling (Background)")
    print(f"🛑 To'xtatish: Ctrl+C\n")
    print("=" * 50)

    app.run(host=host, port=port, debug=debug, use_reloader=False)

if __name__ == '__main__':
    main()
