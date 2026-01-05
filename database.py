import sqlite3
from datetime import datetime
import json
import os
from dotenv import load_dotenv

load_dotenv()
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", 0))

def init_db():
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()

    # --- 1. Создаём таблицы, если их нет ---
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            chat_id INTEGER,
            username TEXT NOT NULL,
            PRIMARY KEY (user_id, chat_id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            format TEXT NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            winner_team_id INTEGER,
            bracket TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            members TEXT NOT NULL,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            round_name TEXT NOT NULL,
            team1_id INTEGER,
            team2_id INTEGER,
            score1 INTEGER DEFAULT -1,
            score2 INTEGER DEFAULT -1,
            winner_team_id INTEGER,
            FOREIGN KEY (tournament_id) REFERENCES tournaments(id) ON DELETE CASCADE,
            FOREIGN KEY (team1_id) REFERENCES teams(id),
            FOREIGN KEY (team2_id) REFERENCES teams(id)
        )
    ''')

    # --- 2. Проверяем и обновляем таблицу user_points ---
    # Шаг 2.1: Проверяем, существует ли таблица user_points
    cur.execute("SELECT count(*) FROM sqlite_master WHERE type='table' AND name='user_points'")
    user_points_exists = cur.fetchone()[0] > 0

    if not user_points_exists:
        # Таблица не создана — создаём новую
        cur.execute('''
            CREATE TABLE user_points (
                chat_id INTEGER NOT NULL,
                username TEXT NOT NULL,
                points INTEGER DEFAULT 0,
                PRIMARY KEY (chat_id, username)
            )
        ''')
    else:
        # Таблица существует — проверяем наличие колонки chat_id
        cur.execute("PRAGMA table_info(user_points)")
        columns = [col[1] for col in cur.fetchall()]

        if "chat_id" not in columns:
            # Старая структура: только username и points
            print("Обнаружена старая таблица user_points. Выполняется миграция...")

            # Шаг 2.2: Переименовываем старую таблицу
            cur.execute("ALTER TABLE user_points RENAME TO user_points_old")

            # Шаг 2.3: Создаём новую таблицу
            cur.execute('''
                CREATE TABLE user_points (
                    chat_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    points INTEGER DEFAULT 0,
                    PRIMARY KEY (chat_id, username)
                )
            ''')

            # Шаг 2.4: Восстанавливаем очки, привязывая их к чатам
            # Собираем все уникальные чаты, в которых есть турниры
            cur.execute("SELECT DISTINCT chat_id FROM tournaments")
            chat_ids = [row[0] for row in cur.fetchall()]

            if not chat_ids:
                # Если турниров нет, просто создаём пустую таблицу
                print("Нет турниров — миграция очков пропущена.")
            else:
                # Для каждого чата — переносим очки
                for chat_id in chat_ids:
                    # Получаем всех игроков, которые участвовали в турнирах этого чата
                    cur.execute('''
                        SELECT DISTINCT member
                        FROM (
                            SELECT trim(substr(members, start, end - start)) AS member
                            FROM teams t
                            JOIN tournaments tr ON t.tournament_id = tr.id
                            CROSS JOIN (
                                SELECT 1 AS start, instr(members || ',', ',') AS end
                                UNION ALL SELECT instr(members || ',', ',') + 1, instr(substr(members || ',', instr(members || ',', ',') + 1), ',') + instr(members || ',', ',')
                                UNION ALL SELECT instr(substr(members || ',', instr(members || ',', ',') + 1), ',') + instr(members || ',', ',') + 1, length(members) + 1
                            ) pos
                            WHERE tr.chat_id = ?
                        )
                    ''', (chat_id,))

                    players = [row[0] for row in cur.fetchall()]
                    if players:
                        # Ищем их очки в старой таблице
                        placeholders = ','.join(['?'] * len(players))
                        cur.execute(f"SELECT username, points FROM user_points_old WHERE username IN ({placeholders})", players)
                        old_points = cur.fetchall()
                        # Вставляем с chat_id
                        for username, points in old_points:
                            cur.execute('''
                                INSERT INTO user_points (chat_id, username, points)
                                VALUES (?, ?, ?)
                                ON CONFLICT(chat_id, username) DO UPDATE SET points = excluded.points
                            ''', (chat_id, username, points))

                # Удаляем старую таблицу
                cur.execute("DROP TABLE user_points_old")
                print("Миграция user_points завершена.")

    conn.commit()
    conn.close()

# --- Остальные функции без изменений ---
def add_user(user_id, chat_id, username):
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    cur.execute('INSERT OR IGNORE INTO users (user_id, chat_id, username) VALUES (?, ?, ?)',
                (user_id, chat_id, username))
    conn.commit()
    conn.close()

def get_user(user_id, chat_id):
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    cur.execute('SELECT username FROM users WHERE user_id = ? AND chat_id = ?', (user_id, chat_id))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def add_points(chat_id, usernames, points):
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    for uname in usernames:
        cur.execute('''
            INSERT INTO user_points (chat_id, username, points)
            VALUES (?, ?, ?)
            ON CONFLICT(chat_id, username) DO UPDATE SET points = points + excluded.points
        ''', (chat_id, uname, points))
    conn.commit()
    conn.close()

def is_admin(user_id):
    return user_id == ADMIN_USER_ID
