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

    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_points (
            chat_at INTEGER NOT NULL,
            username TEXT NOT NULL,
            points INTEGER DEFAULT 0,
            PRIMARY KEY (chat_id, username)
        )
    ''')

    conn.commit()
    conn.close()

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