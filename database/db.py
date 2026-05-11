"""
ATNALTIK DUBBING — Database Layer (SQLite)
"""

import sqlite3
import hashlib
import os
from datetime import datetime
from contextlib import contextmanager


DB_PATH = os.path.join(os.path.dirname(__file__), 'atnaltik.db')


class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()
        self._seed_data()

    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self.get_conn() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                password_hash TEXT,
                first_name TEXT NOT NULL DEFAULT '',
                last_name TEXT DEFAULT '',
                username TEXT DEFAULT '',
                photo_url TEXT DEFAULT '',
                telegram_id TEXT UNIQUE,
                is_admin INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS animes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                original_title TEXT DEFAULT '',
                icon TEXT DEFAULT '🎬',
                score REAL DEFAULT 0,
                status TEXT DEFAULT 'Davom etmoqda',
                year INTEGER DEFAULT 2024,
                description TEXT DEFAULT '',
                cover_image TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS anime_genres (
                anime_id INTEGER,
                genre_name TEXT,
                PRIMARY KEY (anime_id, genre_name),
                FOREIGN KEY (anime_id) REFERENCES animes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS genres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                icon TEXT DEFAULT '🎭',
                color TEXT DEFAULT 'rgba(100,100,100,0.15)'
            );

            CREATE TABLE IF NOT EXISTS seasons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anime_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                year INTEGER DEFAULT 2024,
                order_num INTEGER DEFAULT 1,
                FOREIGN KEY (anime_id) REFERENCES animes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_id INTEGER NOT NULL,
                anime_id INTEGER NOT NULL,
                num INTEGER DEFAULT 1,
                title TEXT NOT NULL,
                duration TEXT DEFAULT '24 dq',
                telegram_url TEXT DEFAULT '',
                telegram_file_id TEXT DEFAULT '',
                telegram_file_path TEXT DEFAULT '',
                is_new INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (season_id) REFERENCES seasons(id) ON DELETE CASCADE,
                FOREIGN KEY (anime_id) REFERENCES animes(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS pending_videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                chat_id TEXT,
                message_id INTEGER,
                caption TEXT DEFAULT '',
                processed INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            try:
                conn.execute("ALTER TABLE animes ADD COLUMN cover_image TEXT DEFAULT ''")
            except: pass

            try:
                conn.execute("ALTER TABLE episodes ADD COLUMN telegram_chat_id TEXT")
                conn.execute("ALTER TABLE episodes ADD COLUMN telegram_msg_id INTEGER")
            except: pass

            try:
                conn.execute("ALTER TABLE pending_videos ADD COLUMN chat_id TEXT")
            except: pass

    # ─────────────────────────────────────────
    #  SEED DATA
    # ─────────────────────────────────────────

    def _seed_data(self):
        """Boshlang'ich ma'lumotlar — faqat bo'sh DB uchun"""
        with self.get_conn() as conn:
            # Admin mavjudmi?
            row = conn.execute("SELECT COUNT(*) as cnt FROM users WHERE is_admin=1").fetchone()
            if row['cnt'] > 0:
                return  # Allaqachon seed qilingan

            # Admin yaratish
            pwd_hash = hashlib.sha256('admin123'.encode()).hexdigest()
            conn.execute("""
                INSERT OR IGNORE INTO users (email, password_hash, first_name, is_admin)
                VALUES (?, ?, ?, 1)
            """, ('admin@atnaltik.uz', pwd_hash, 'Admin'))

            # Janrlar
            genres = [
                ('Aksiya', '⚔️', 'rgba(230,57,70,0.15)'),
                ('Fantastika', '✨', 'rgba(156,39,176,0.15)'),
                ('Drama', '💔', 'rgba(244,67,54,0.12)'),
                ('Komediya', '😂', 'rgba(255,193,7,0.15)'),
                ('Sarguzasht', '🌍', 'rgba(76,175,80,0.15)'),
                ('Sport', '🎾', 'rgba(33,150,243,0.15)'),
                ('Romantika', '🌹', 'rgba(233,30,99,0.15)'),
                ('Dahshat', '💀', 'rgba(121,85,72,0.15)'),
                ('Psixologik', '🧠', 'rgba(103,58,183,0.15)'),
                ('Tarix', '👑', 'rgba(121,85,72,0.15)'),
            ]
            conn.executemany(
                "INSERT OR IGNORE INTO genres (name, icon, color) VALUES (?,?,?)", genres
            )

            # Demo animelar
            demo_animes = [
                {
                    'title': 'Demon Slayer: Kimetsu no Yaiba', 'original_title': '鬼滅の刃',
                    'icon': '🏮', 'score': 8.7, 'status': 'Tugallangan', 'year': 2019,
                    'description': "Tanjiro Kamado oilasi jin tomonidan o'ldirilgandan so'ng, tiriq qolgan singlisini insonga qaytarish uchun Jin qiruvchilar safiga qo'shiladi.",
                    'genres': ['Aksiya', 'Fantastika', 'Drama'],
                    'seasons': [
                        {'title': '1-fasl', 'year': 2019, 'order_num': 1, 'episodes': [
                            {'num': 1, 'title': 'Yovuzlik uyg\'ondi', 'duration': '24 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': False},
                            {'num': 2, 'title': 'Qiyinchilik davri', 'duration': '24 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': False},
                        ]},
                        {'title': '2-fasl: Yoshiwara Kvartali', 'year': 2021, 'order_num': 2, 'episodes': [
                            {'num': 1, 'title': 'Yoshiwara tunlari', 'duration': '44 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': True},
                        ]},
                    ]
                },
                {
                    'title': 'Attack on Titan', 'original_title': '進撃の巨人',
                    'icon': '⚔️', 'score': 9.0, 'status': 'Tugallangan', 'year': 2013,
                    'description': "Gigant odamxo'rlar dunyosida, devol ichida yashayotgan odamlar qoldig'i. Eren Yaeger qasos yo'lida.",
                    'genres': ['Drama', 'Psixologik', 'Aksiya'],
                    'seasons': [
                        {'title': '1-fasl', 'year': 2013, 'order_num': 1, 'episodes': [
                            {'num': 1, 'title': "Devol ichidagi dunyo", 'duration': '24 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': False},
                        ]},
                        {'title': 'Final Fasl', 'year': 2022, 'order_num': 4, 'episodes': [
                            {'num': 1, 'title': 'Oxirigacha', 'duration': '87 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': True},
                        ]},
                    ]
                },
                {
                    'title': 'Jujutsu Kaisen', 'original_title': '呪術廻戦',
                    'icon': '🔥', 'score': 8.6, 'status': 'Davom etmoqda', 'year': 2020,
                    'description': "Yuji Itadori bir tasodifdan so'ng eng kuchli la'nat ruhining tashuvchisiga aylanadi.",
                    'genres': ['Aksiya', 'Fantastika', 'Dahshat'],
                    'seasons': [
                        {'title': '1-fasl', 'year': 2020, 'order_num': 1, 'episodes': [
                            {'num': 1, 'title': 'Ryomen Sukuna', 'duration': '24 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': False},
                        ]},
                        {'title': '2-fasl', 'year': 2023, 'order_num': 2, 'episodes': [
                            {'num': 1, 'title': "Gojoniyng o'tmishi", 'duration': '47 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': True},
                        ]},
                    ]
                },
                {
                    'title': 'One Piece', 'original_title': 'ワンピース',
                    'icon': '🐉', 'score': 8.9, 'status': 'Davom etmoqda', 'year': 1999,
                    'description': "Monkey D. Luffy va uning dengizchi do'stlari Grand Line bo'ylab Bir bo'lakni izlab sayohat qiladilar.",
                    'genres': ['Sarguzasht', 'Komediya', 'Aksiya'],
                    'seasons': [
                        {'title': 'East Blue Saga', 'year': 1999, 'order_num': 1, 'episodes': [
                            {'num': 1, 'title': "Men kaptanman!", 'duration': '22 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': False},
                        ]},
                    ]
                },
                {
                    'title': 'Haikyuu!!', 'original_title': 'ハイキュー!!',
                    'icon': '🎾', 'score': 8.5, 'status': 'Tugallangan', 'year': 2014,
                    'description': "Hinata Shoyo qisqa bo'lishiga qaramay professional voleybol o'yinchisi bo'lishni orzu qiladi.",
                    'genres': ['Sport', 'Drama', 'Komediya'],
                    'seasons': [
                        {'title': '1-fasl', 'year': 2014, 'order_num': 1, 'episodes': [
                            {'num': 1, 'title': "Gigantlarning to'qnashuvi", 'duration': '25 dq', 'telegram_url': 'https://t.me/ATNALTIK', 'is_new': False},
                        ]},
                    ]
                },
            ]

            for anime_data in demo_animes:
                genres_list = anime_data.pop('genres')
                seasons_data = anime_data.pop('seasons')
                cur = conn.execute("""
                    INSERT INTO animes (title, original_title, icon, score, status, year, description)
                    VALUES (:title, :original_title, :icon, :score, :status, :year, :description)
                """, anime_data)
                anime_id = cur.lastrowid

                for g in genres_list:
                    conn.execute("INSERT OR IGNORE INTO anime_genres VALUES (?,?)", (anime_id, g))

                for s in seasons_data:
                    eps = s.pop('episodes')
                    cur2 = conn.execute("""
                        INSERT INTO seasons (anime_id, title, year, order_num)
                        VALUES (?,?,?,?)
                    """, (anime_id, s['title'], s['year'], s['order_num']))
                    season_id = cur2.lastrowid

                    for e in eps:
                        conn.execute("""
                            INSERT INTO episodes (season_id, anime_id, num, title, duration, telegram_url, is_new)
                            VALUES (?,?,?,?,?,?,?)
                        """, (season_id, anime_id, e['num'], e['title'], e['duration'],
                              e['telegram_url'], 1 if e['is_new'] else 0))

    # ─────────────────────────────────────────
    #  USERS
    # ─────────────────────────────────────────

    def _hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def get_user(self, user_id):
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
            return dict(row) if row else None

    def user_exists(self, email):
        with self.get_conn() as conn:
            row = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            return row is not None

    def create_user(self, email, password, first_name):
        with self.get_conn() as conn:
            pwd_hash = self._hash_password(password)
            cur = conn.execute("""
                INSERT INTO users (email, password_hash, first_name) VALUES (?,?,?)
            """, (email, pwd_hash, first_name))
            return {'id': cur.lastrowid, 'first_name': first_name, 'is_admin': 0}

    def login_user(self, email, password):
        with self.get_conn() as conn:
            pwd_hash = self._hash_password(password)
            row = conn.execute(
                "SELECT * FROM users WHERE email=? AND password_hash=?", (email, pwd_hash)
            ).fetchone()
            return dict(row) if row else None

    def check_admin(self, username, password):
        with self.get_conn() as conn:
            pwd_hash = self._hash_password(password)
            row = conn.execute("""
                SELECT * FROM users WHERE (email=? OR username=?) AND password_hash=? AND is_admin=1
            """, (username, username, pwd_hash)).fetchone()
            return dict(row) if row else None

    def get_or_create_user_by_telegram(self, tg_id, first_name, last_name, username, photo_url):
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM users WHERE telegram_id=?", (tg_id,)).fetchone()
            if row:
                conn.execute("""
                    UPDATE users SET first_name=?, last_name=?, username=?, photo_url=? WHERE telegram_id=?
                """, (first_name, last_name, username, photo_url, tg_id))
                return dict(row)
            cur = conn.execute("""
                INSERT INTO users (telegram_id, first_name, last_name, username, photo_url)
                VALUES (?,?,?,?,?)
            """, (tg_id, first_name, last_name, username, photo_url))
            return {'id': cur.lastrowid, 'first_name': first_name, 'is_admin': 0}

    def get_all_users(self):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
            return [dict(r) for r in rows]

    def toggle_admin(self, user_id):
        with self.get_conn() as conn:
            conn.execute("UPDATE users SET is_admin = 1 - is_admin WHERE id=?", (user_id,))

    # ─────────────────────────────────────────
    #  ANIMES
    # ─────────────────────────────────────────

    def _row_to_anime(self, row, conn):
        a = dict(row)
        genres = conn.execute(
            "SELECT genre_name FROM anime_genres WHERE anime_id=?", (a['id'],)
        ).fetchall()
        a['genres'] = [g['genre_name'] for g in genres]
        return a

    def get_all_animes(self):
        with self.get_conn() as conn:
            rows = conn.execute("SELECT * FROM animes ORDER BY created_at DESC").fetchall()
            result = []
            for r in rows:
                a = self._row_to_anime(r, conn)
                # Season va episode count
                a['season_count'] = conn.execute(
                    "SELECT COUNT(*) as cnt FROM seasons WHERE anime_id=?", (a['id'],)
                ).fetchone()['cnt']
                result.append(a)
            return result

    def get_animes_filtered(self, genre='', search='', page=1, per_page=20):
        with self.get_conn() as conn:
            offset = (page - 1) * per_page
            if genre and search:
                rows = conn.execute("""
                    SELECT DISTINCT a.* FROM animes a
                    JOIN anime_genres ag ON a.id=ag.anime_id
                    WHERE ag.genre_name=? AND (a.title LIKE ? OR a.original_title LIKE ?)
                    ORDER BY a.created_at DESC LIMIT ? OFFSET ?
                """, (genre, f'%{search}%', f'%{search}%', per_page, offset)).fetchall()
            elif genre:
                rows = conn.execute("""
                    SELECT a.* FROM animes a
                    JOIN anime_genres ag ON a.id=ag.anime_id
                    WHERE ag.genre_name=? ORDER BY a.created_at DESC LIMIT ? OFFSET ?
                """, (genre, per_page, offset)).fetchall()
            elif search:
                rows = conn.execute("""
                    SELECT * FROM animes
                    WHERE title LIKE ? OR original_title LIKE ?
                    ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, (f'%{search}%', f'%{search}%', per_page, offset)).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM animes ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (per_page, offset)
                ).fetchall()
            return [self._row_to_anime(r, conn) for r in rows]

    def get_anime_with_seasons(self, anime_id):
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM animes WHERE id=?", (anime_id,)).fetchone()
            if not row:
                return None
            anime = self._row_to_anime(row, conn)
            seasons = conn.execute(
                "SELECT * FROM seasons WHERE anime_id=? ORDER BY order_num", (anime_id,)
            ).fetchall()
            anime['seasons'] = []
            for s in seasons:
                season = dict(s)
                eps = conn.execute(
                    "SELECT * FROM episodes WHERE season_id=? ORDER BY num", (s['id'],)
                ).fetchall()
                season['episodes'] = [dict(e) for e in eps]
                anime['seasons'].append(season)
            return anime

    def add_anime(self, data):
        with self.get_conn() as conn:
            cur = conn.execute("""
                INSERT INTO animes (title, original_title, icon, score, status, year, description, cover_image)
                VALUES (:title, :original_title, :icon, :score, :status, :year, :description, :cover_image)
            """, data)
            anime_id = cur.lastrowid
            for g in data.get('genres', []):
                conn.execute("INSERT OR IGNORE INTO anime_genres VALUES (?,?)", (anime_id, g))
            return anime_id

    def update_anime(self, data):
        with self.get_conn() as conn:
            conn.execute("""
                UPDATE animes SET title=:title, original_title=:original_title, icon=:icon,
                score=:score, status=:status, year=:year, description=:description, cover_image=:cover_image
                WHERE id=:id
            """, data)
            conn.execute("DELETE FROM anime_genres WHERE anime_id=?", (data['id'],))
            for g in data.get('genres', []):
                conn.execute("INSERT OR IGNORE INTO anime_genres VALUES (?,?)", (data['id'], g))

    def delete_anime(self, anime_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM animes WHERE id=?", (anime_id,))

    # ─────────────────────────────────────────
    #  SEASONS
    # ─────────────────────────────────────────

    def get_season(self, season_id):
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM seasons WHERE id=?", (season_id,)).fetchone()
            return dict(row) if row else None

    def add_season(self, data):
        with self.get_conn() as conn:
            cur = conn.execute("""
                INSERT INTO seasons (anime_id, title, year, order_num)
                VALUES (:anime_id, :title, :year, :order_num)
            """, data)
            return cur.lastrowid

    def delete_season(self, season_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM seasons WHERE id=?", (season_id,))

    # ─────────────────────────────────────────
    #  EPISODES
    # ─────────────────────────────────────────

    def get_episode(self, ep_id):
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM episodes WHERE id=?", (ep_id,)).fetchone()
            return dict(row) if row else None

    def add_episode(self, data):
        with self.get_conn() as conn:
            cur = conn.execute("""
                INSERT INTO episodes (season_id, anime_id, num, title, duration, telegram_url, telegram_file_id, telegram_chat_id, telegram_msg_id, telegram_file_path, is_new)
                VALUES (:season_id, :anime_id, :num, :title, :duration, :telegram_url, :telegram_file_id, :telegram_chat_id, :telegram_msg_id, :telegram_file_path, :is_new)
            """, data)
            return cur.lastrowid

    def delete_episode(self, ep_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM episodes WHERE id=?", (ep_id,))

    def toggle_episode_new(self, ep_id):
        with self.get_conn() as conn:
            conn.execute("UPDATE episodes SET is_new = 1 - is_new WHERE id=?", (ep_id,))

    def get_latest_episodes(self, limit=12):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT e.*, a.title as anime_title, a.icon as anime_icon, s.title as season_title
                FROM episodes e
                JOIN animes a ON e.anime_id = a.id
                JOIN seasons s ON e.season_id = s.id
                ORDER BY e.is_new DESC, e.created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    # ─────────────────────────────────────────
    #  GENRES
    # ─────────────────────────────────────────

    def get_all_genres(self):
        with self.get_conn() as conn:
            rows = conn.execute("""
                SELECT g.*, COUNT(ag.anime_id) as count
                FROM genres g
                LEFT JOIN anime_genres ag ON g.name = ag.genre_name
                GROUP BY g.id ORDER BY g.name
            """).fetchall()
            return [dict(r) for r in rows]

    def add_genre(self, data):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO genres (name, icon, color) VALUES (:name, :icon, :color)", data
            )

    def delete_genre(self, genre_id):
        with self.get_conn() as conn:
            conn.execute("DELETE FROM genres WHERE id=?", (genre_id,))

    # ─────────────────────────────────────────
    #  STATS
    # ─────────────────────────────────────────

    def get_stats(self):
        with self.get_conn() as conn:
            anime_count = conn.execute("SELECT COUNT(*) as cnt FROM animes").fetchone()['cnt']
            ep_count = conn.execute("SELECT COUNT(*) as cnt FROM episodes").fetchone()['cnt']
            user_count = conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()['cnt']
            season_count = conn.execute("SELECT COUNT(*) as cnt FROM seasons").fetchone()['cnt']
            return {
                'animes': anime_count,
                'episodes': ep_count,
                'users': user_count,
                'seasons': season_count,
            }

    def save_pending_video(self, file_id, caption, chat_id, message_id):
        with self.get_conn() as conn:
            conn.execute("""
                INSERT INTO pending_videos (file_id, caption, chat_id, message_id)
                VALUES (?,?,?,?)
            """, (file_id, caption, str(chat_id) if chat_id else None, message_id))
