import random
import json
from typing import List, Dict, Any

POINTS_MAP = {
    '2': {1: 5},
    '4': {1: 13, 2: 7},
    '8': {1: 30, 2: 17, 3: 9},
    '16': {1: 70, 2: 34, 3: 19, 4: 14}
}

def parse_teams_input(text: str, expected_count: int):
    blocks = [block.strip() for block in text.strip().split('\n\n') if block.strip()]
    if len(blocks) != expected_count:
        return None, f"Ожидалось {expected_count} команд, получено {len(blocks)}."
    teams = []
    for block in blocks:
        lines = [line.strip() for line in block.split('\n') if line.strip()]
        if len(lines) != 4:
            return None, f"Каждая команда должна содержать: название + 3 игрока.\nНеверный блок:\n{block}"
        name = lines[0]
        members = lines[1:4]
        teams.append((name, members))
    return teams, None

def assign_random_teams(players: List[str], team_size=3):
    random.shuffle(players)
    teams = []
    for i in range(0, len(players), team_size):
        team = players[i:i+team_size]
        if len(team) == team_size:
            teams.append(team)
    return teams

def generate_bracket(team_ids: List[int], fmt: str):
    random.shuffle(team_ids)
    bracket = {"rounds": [], "matches": {}}
    n = len(team_ids)
    if n == 2:
        bracket["rounds"] = ["final"]
        bracket["matches"]["final"] = [(team_ids[0], team_ids[1])]
    elif n == 4:
        bracket["rounds"] = ["semi", "third_place", "final"]
        bracket["matches"]["semi"] = [(team_ids[0], team_ids[1]), (team_ids[2], team_ids[3])]
    elif n == 8:
        bracket["rounds"] = ["quarter", "semi", "third_place", "final"]
        bracket["matches"]["quarter"] = [(team_ids[i], team_ids[i+1]) for i in range(0, 8, 2)]
    elif n == 16:
        bracket["rounds"] = ["round16", "quarter", "semi", "third_place", "final"]
        bracket["matches"]["round16"] = [(team_ids[i], team_ids[i+1]) for i in range(0, 16, 2)]
    return bracket

def create_initial_matches(cur, tournament_id: int, bracket: Dict[str, Any]):
    first_round = bracket["rounds"][0]
    for team1_id, team2_id in bracket["matches"][first_round]:
        cur.execute('''
            INSERT INTO matches (tournament_id, round_name, team1_id, team2_id)
            VALUES (?, ?, ?, ?)
        ''', (tournament_id, first_round, team1_id, team2_id))

def advance_bracket(cur, tournament_id: int, finished_round: str):
    # Получаем все матчи турнира
    cur.execute('SELECT bracket FROM tournaments WHERE id = ?', (tournament_id,))
    bracket_json = cur.fetchone()[0]
    bracket = json.loads(bracket_json)

    cur.execute('SELECT round_name FROM matches WHERE tournament_id = ? AND winner_team_id IS NOT NULL GROUP BY round_name', (tournament_id,))
    completed_rounds = {r[0] for r in cur.fetchall()}

    current_round_index = bracket["rounds"].index(finished_round)
    if current_round_index + 1 >= len(bracket["rounds"]):
        # Турнир завершён
        # Определяем победителя и 2-3-4 места
        finalize_tournament(cur, tournament_id, bracket)
        return

    next_round = bracket["rounds"][current_round_index + 1]

    # Получаем победителей текущего раунда
    cur.execute('''
        SELECT winner_team_id FROM matches
        WHERE tournament_id = ? AND round_name = ?
        ORDER BY id
    ''', (tournament_id, finished_round))
    winners = [row[0] for row in cur.fetchall()]

    if next_round == "third_place" and finished_round == "semi":
        # Для 4/8/16: матч за 3-е место между проигравшими полуфиналов
        cur.execute('''
            SELECT team1_id, team2_id, winner_team_id FROM matches
            WHERE tournament_id = ? AND round_name = ?
        ''', (tournament_id, "semi"))
        losers = []
        for t1, t2, w in cur.fetchall():
            loser = t1 if w == t2 else t2
            losers.append(loser)
        if len(losers) == 2:
            cur.execute('''
                INSERT INTO matches (tournament_id, round_name, team1_id, team2_id)
                VALUES (?, ?, ?, ?)
            ''', (tournament_id, "third_place", losers[0], losers[1]))
        return

    # Обычный переход: пары победителей
    if len(winners) % 2 != 0:
        return  # ошибка

    new_pairs = [(winners[i], winners[i+1]) for i in range(0, len(winners), 2)]
    bracket["matches"][next_round] = new_pairs

    # Сохраняем обновлённую сетку
    cur.execute('UPDATE tournaments SET bracket = ? WHERE id = ?', (json.dumps(bracket), tournament_id))

    # Создаём матчи
    for t1, t2 in new_pairs:
        cur.execute('''
            INSERT INTO matches (tournament_id, round_name, team1_id, team2_id)
            VALUES (?, ?, ?, ?)
        ''', (tournament_id, next_round, t1, t2))

def finalize_tournament(cur, tournament_id: int, bracket: dict):
    # Победитель — победитель финала
    cur.execute('''
        SELECT winner_team_id FROM matches
        WHERE tournament_id = ? AND round_name = 'final'
    ''')
    winner_row = cur.fetchone()
    if winner_row:
        winner_id = winner_row[0]
        cur.execute('UPDATE tournaments SET winner_team_id = ?, status = "finished" WHERE id = ?',
                    (winner_id, tournament_id))

        # Начисляем очки
        cur.execute('SELECT chat_id, format FROM tournaments WHERE id = ?', (tournament_id,))
        chat_id, fmt = cur.fetchone()

        # 1 место
        cur.execute('SELECT members FROM teams WHERE id = ?', (winner_id,))
        members1 = cur.fetchone()[0].split(',')
        add_points(chat_id, members1, POINTS_MAP[fmt].get(1, 0))

        # 2 место
        if fmt in ['4', '8', '16']:
            cur.execute('''
                SELECT team1_id, team2_id FROM matches
                WHERE tournament_id = ? AND round_name = 'final'
            ''', (tournament_id,))
            t1, t2 = cur.fetchone()
            loser2 = t1 if t1 != winner_id else t2
            cur.execute('SELECT members FROM teams WHERE id = ?', (loser2,))
            members2 = cur.fetchone()[0].split(',')
            add_points(chat_id, members2, POINTS_MAP[fmt].get(2, 0))

        # 3 место
        if fmt in ['8', '16']:
            cur.execute('''
                SELECT winner_team_id FROM matches
                WHERE tournament_id = ? AND round_name = 'third_place'
            ''', (tournament_id,))
            third_row = cur.fetchone()
            if third_row:
                third_id = third_row[0]
                cur.execute('SELECT members FROM teams WHERE id = ?', (third_id,))
                members3 = cur.fetchone()[0].split(',')
                add_points(chat_id, members3, POINTS_MAP[fmt].get(3, 0))

        # 4 место (только 16)
        if fmt == '16':
            cur.execute('''
                SELECT team1_id, team2_id FROM matches
                WHERE tournament_id = ? AND round_name = 'third_place'
            ''', (tournament_id,))
            tt1, tt2 = cur.fetchone()
            loser4 = tt1 if tt1 != third_id else tt2
            cur.execute('SELECT members FROM teams WHERE id = ?', (loser4,))
            members4 = cur.fetchone()[0].split(',')
            add_points(chat_id, members4, POINTS_MAP[fmt].get(4, 0))