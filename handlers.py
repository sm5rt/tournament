from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import *
from keyboards import *
from utils import *
import json

router = Router()

class TournamentStates(StatesGroup):
    waiting_for_tournament_name = State()
    waiting_for_teams = State()
    waiting_for_player_count = State()
    waiting_for_players_list = State()
    waiting_for_match_result = State()

# --- /start ---
@router.message(F.text == "/start")
async def cmd_start(message: Message):
    await message.answer("Добро пожаловать! Используйте /reg для регистрации.", reply_markup=main_menu_kb())

# --- /help ---
@router.message(F.text == "/help")
async def cmd_help(message: Message):
    help_text = (
        "🎮 <b>Помощь по боту для турниров Brawl Stars</b>\n\n"
        
        "🔹 <b>1. Регистрация</b>\n"
        "Перед участием зарегистрируйте свой ник:\n"
        "<code>/reg ВашНик</code>\n\n"
        
        "🔹 <b>2. Создание турнира</b>\n"
        "Используйте команду:\n"
        "<code>/tournament Название турнира</code>\n"
        "Затем выберите формат (2/4/8/16 команд или рандом).\n\n"
        
        "🔹 <b>3. Ввод команд</b>\n"
        "Для ручного турнира введите данные в формате:\n"
        "<pre>Название команды\nИгрок1\nИгрок2\nИгрок3\n\n"
        "Название команды2\nИгрок4\nИгрок5\nИгрок6</pre>\n"
        "Команды разделяются <b>пустой строкой</b>.\n\n"
        
        "🔹 <b>4. Рандом-турнир</b>\n"
        "Выберите «Рандомные команды» → укажите 6/12/24/48 игроков → бот сам распределит их по командам и создаст сетку.\n\n"
        
        "🔹 <b>5. Проведение матчей</b>\n"
        "После создания турнира бот покажет пары матчей. Организаторы (или админ) нажимают кнопки под сообщением, чтобы указать победителя.\n"
        "Система автоматически создаёт следующие матчи, включая <b>матч за 3-е место</b> (в турнирах от 4+ команд).\n\n"
        
        "🔹 <b>6. История и рейтинг</b>\n"
        "• <code>/historytournament</code> — список завершённых турниров\n"
        "• <code>/list</code> — рейтинг игроков по очкам\n\n"
        
        "🏆 <b>Таблица очков</b>\n\n"
        
        "<b>Турнир на 2 команды:</b>\n"
        "• 1 место — 5 очков\n\n"
        
        "<b>Турнир на 4 команды:</b>\n"
        "• 1 место — 13 очков\n"
        "• 2 место — 7 очков\n\n"
        
        "<b>Турнир на 8 команд:</b>\n"
        "• 1 место — 30 очков\n"
        "• 2 место — 17 очков\n"
        "• 3 место — 9 очков\n\n"
        
        "<b>Турнир на 16 команд:</b>\n"
        "• 1 место — 70 очков\n"
        "• 2 место — 34 очков\n"
        "• 3 место — 19 очков\n"
        "• 4 место — 14 очков\n\n"
        
        "💡 Очки начисляются <b>всем игрокам</b> в команде.\n"
        "Данные разделены по чатам — турниры в одной группе не видны в другой."
    )
    await message.answer(help_text, disable_web_page_preview=True)

@router.callback_query(F.data == "help_command")
async def help_from_menu(callback: CallbackQuery):
    await cmd_help(callback.message)
    await callback.answer()

# --- /reg ---
@router.message(F.text.startswith("/reg"))
async def register_user(message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используйте: /reg [ваш ник]")
        return
    username = parts[1].strip()
    add_user(message.from_user.id, message.chat.id, username)
    await message.answer(f"✅ Вы зарегистрированы как: {username}")

# --- Создание турнира ---
@router.message(F.text.startswith("/tournament"))
async def start_tournament(message: Message, state: FSMContext):
    username = get_user(message.from_user.id, message.chat.id)
    if not username:
        await message.answer("Сначала зарегистрируйтесь через /reg [ваш ник]")
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используйте: /tournament [название]")
        return
    await state.update_data(tournament_name=parts[1].strip())
    await message.answer("Выберите формат турнира:", reply_markup=tournament_format_kb())

@router.callback_query(F.data.startswith("format_"))
async def handle_format(callback: CallbackQuery, state: FSMContext):
    fmt = callback.data.replace("format_", "")
    await state.update_data(format=fmt, chat_id=callback.message.chat.id)
    if fmt == "random":
        await callback.message.answer("Введите количество игроков (6, 12, 24 или 48):")
        await state.set_state(TournamentStates.waiting_for_player_count)
    else:
        count = int(fmt)
        await callback.message.answer(
            f"Введите данные для {count} команд в формате:\n\n"
            "Название\nИгрок1\nИгрок2\nИгрок3\n\n"
            "Разделите команды пустой строкой."
        )
        await state.set_state(TournamentStates.waiting_for_teams)
    await callback.answer()

@router.message(TournamentStates.waiting_for_player_count)
async def get_player_count(message: Message, state: FSMContext):
    try:
        count = int(message.text.strip())
        if count not in [6, 12, 24, 48]:
            raise ValueError
        await state.update_data(player_count=count)
        await message.answer(f"Введите {count} ников игроков, по одному в строке:")
        await state.set_state(TournamentStates.waiting_for_players_list)
    except:
        await message.answer("Введите 6, 12, 24 или 48.")

@router.message(TournamentStates.waiting_for_players_list)
async def process_random_players(message: Message, state: FSMContext):
    data = await state.get_data()
    players = [line.strip() for line in message.text.split('\n') if line.strip()]
    if len(players) != data['player_count']:
        await message.answer(f"Ожидалось {data['player_count']} игроков. Попробуйте снова.")
        return
    teams = assign_random_teams(players)
    if not teams:
        await message.answer("Не удалось сформировать полные команды.")
        return
    await create_tournament_from_teams(message, state, teams)

@router.message(TournamentStates.waiting_for_teams)
async def process_manual_teams(message: Message, state: FSMContext):
    data = await state.get_data()
    teams_data, error = parse_teams_input(message.text, int(data['format']))
    if error:
        await message.answer(f"Ошибка: {error}\nПопробуйте снова.")
        return
    await create_tournament_from_teams(message, state, teams_data)

async def create_tournament_from_teams(message: Message, state: FSMContext, teams):
    data = await state.get_data()
    chat_id = message.chat.id
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO tournaments (chat_id, name, format, created_at)
        VALUES (?, ?, ?, ?)
    ''', (chat_id, data['tournament_name'], data['format'], datetime.utcnow().isoformat()))
    tournament_id = cur.lastrowid

    team_ids = []
    for name, members in teams:
        members_str = ','.join(members)
        cur.execute('INSERT INTO teams (tournament_id, name, members) VALUES (?, ?, ?)',
                    (tournament_id, name, members_str))
        team_ids.append(cur.lastrowid)
        for m in members:
            add_user(message.from_user.id, chat_id, m)

    bracket = generate_bracket(team_ids, data['format'])
    cur.execute('UPDATE tournaments SET bracket = ? WHERE id = ?', (json.dumps(bracket), tournament_id))
    create_initial_matches(cur, tournament_id, bracket)

    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Турнир создан! Сетка сформирована.")
    await show_current_matches(message, tournament_id)

async def show_current_matches(message: Message, tournament_id: int):
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT m.id, r.round_name, t1.name, t2.name, m.score1, m.score2
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.id
        JOIN teams t2 ON m.team2_id = t2.id
        WHERE m.tournament_id = ? AND m.winner_team_id IS NULL
    ''', (tournament_id,))
    matches = cur.fetchall()
    conn.close()

    if not matches:
        await message.answer("Все матчи этого раунда завершены.")
        return

    for match_id, rnd, t1, t2, s1, s2 in matches:
        members1 = get_team_members(tournament_id, t1)
        members2 = get_team_members(tournament_id, t2)
        text = f"<b>{rnd.upper()}:</b>\n{t1} vs {t2}\n\n"
        text += f"Игроки {t1}: {', '.join(members1)}\n"
        text += f"Игроки {t2}: {', '.join(members2)}"
        await message.answer(text, reply_markup=match_result_kb(match_id))

def get_team_members(tournament_id, team_name):
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    cur.execute('SELECT members FROM teams WHERE tournament_id = ? AND name = ?', (tournament_id, team_name))
    row = cur.fetchone()
    conn.close()
    return row[0].split(',') if row else []

# --- Обработка результатов ---
@router.callback_query(F.data.startswith("result_"))
async def handle_match_result(callback: CallbackQuery):
    _, match_id, winner_index = callback.data.split("_")
    match_id = int(match_id)
    winner_index = int(winner_index)

    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    cur.execute('SELECT team1_id, team2_id, round_name, tournament_id FROM matches WHERE id = ?', (match_id,))
    team1_id, team2_id, round_name, tournament_id = cur.fetchone()
    winner_team_id = team1_id if winner_index == 1 else team2_id

    cur.execute('''
        UPDATE matches SET score1 = ?, score2 = ?, winner_team_id = ?
        WHERE id = ?
    ''', (3, 0, winner_team_id, match_id) if winner_index == 1 else (0, 3, winner_team_id, match_id))

    cur.execute('SELECT COUNT(*) FROM matches WHERE tournament_id = ? AND round_name = ? AND winner_team_id IS NULL', (tournament_id, round_name))
    if cur.fetchone()[0] == 0:
        advance_bracket(cur, tournament_id, round_name)

    conn.commit()
    conn.close()
    await callback.message.edit_text("✅ Матч завершён!")

# --- История ---
@router.message(F.text == "/historytournament")
@router.callback_query(F.data == "historytournament")
async def show_history(message_or_callback):
    chat_id = message_or_callback.chat.id if isinstance(message_or_callback, Message) else message_or_callback.message.chat.id
    is_admin_user = is_admin(message_or_callback.from_user.id if isinstance(message_or_callback, Message) else message_or_callback.from_user.id)

    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    if is_admin_user:
        cur.execute("SELECT id, name, format, created_at FROM tournaments WHERE status = 'finished'")
    else:
        cur.execute("SELECT id, name, format, created_at FROM tournaments WHERE chat_id = ? AND status = 'finished'", (chat_id,))
    tournaments = cur.fetchall()
    conn.close()

    if not tournaments:
        text = "Нет завершённых турниров."
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text)
        else:
            await message_or_callback.message.edit_text(text)
        return

    kb = tournament_history_kb(tournaments)
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer("История турниров:", reply_markup=kb)
    else:
        await message_or_callback.message.edit_text("История турниров:", reply_markup=kb)

@router.callback_query(F.data.startswith("view_tournament_"))
async def view_tournament_details(callback: CallbackQuery):
    tournament_id = int(callback.data.split("_")[-1])
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    cur.execute('SELECT chat_id FROM tournaments WHERE id = ?', (tournament_id,))
    row = cur.fetchone()
    if not row:
        await callback.answer("Турнир не найден.")
        return
    chat_id = row[0]
    if not (is_admin(callback.from_user.id) or chat_id == callback.message.chat.id):
        await callback.answer("Доступ запрещён.")
        return

    cur.execute('SELECT name, format, created_at, winner_team_id FROM tournaments WHERE id = ?', (tournament_id,))
    name, fmt, created, winner_id = cur.fetchone()

    cur.execute('SELECT name, members FROM teams WHERE tournament_id = ?', (tournament_id,))
    teams = cur.fetchall()

    cur.execute('''
        SELECT round_name, t1.name, t2.name, m.score1, m.score2
        FROM matches m
        JOIN teams t1 ON m.team1_id = t1.id
        JOIN teams t2 ON m.team2_id = t2.id
        WHERE m.tournament_id = ?
        ORDER BY m.id
    ''', (tournament_id,))
    matches = cur.fetchall()

    text = f"🏆 <b>{name}</b>\n📅 {created[:10]}\n\n"
    text += "<b>Команды:</b>\n"
    for team_name, members in teams:
        text += f"  • {team_name}: {members.replace(',', ', ')}\n"

    text += "\n<b>Матчи:</b>\n"
    for rnd, t1, t2, s1, s2 in matches:
        if s1 == -1:
            text += f"  • {t1} vs {t2} ({rnd}) — не сыгран\n"
        else:
            text += f"  • {t1} {s1}:{s2} {t2} ({rnd})\n"

    if winner_id:
        cur.execute('SELECT name FROM teams WHERE id = ?', (winner_id,))
        winner_name = cur.fetchone()[0]
        text += f"\n🎉 <b>Победитель: {winner_name}</b>"

    await callback.message.edit_text(text, reply_markup=tournament_action_kb(tournament_id))
    await callback.answer()

@router.callback_query(F.data.startswith("del_tournament_"))
async def delete_tournament(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Только админ может удалять турниры.", show_alert=True)
        return
    tournament_id = int(callback.data.split("_")[-1])
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    cur.execute('DELETE FROM tournaments WHERE id = ?', (tournament_id,))
    conn.commit()
    conn.close()
    await callback.message.edit_text("🗑️ Турнир удалён.")

# --- Рейтинг ---
@router.message(F.text == "/list")
@router.callback_query(F.data == "list_players")
async def show_leaderboard(message_or_callback):
    chat_id = message_or_callback.chat.id if isinstance(message_or_callback, Message) else message_or_callback.message.chat.id
    conn = sqlite3.connect('tournaments.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT username, points FROM user_points
        WHERE chat_id = ?
        ORDER BY points DESC LIMIT 20
    ''', (chat_id,))
    players = cur.fetchall()
    conn.close()

    if not players:
        text = "Нет данных о рейтинге."
    else:
        medals = ["🥇", "🥈", "🥉"]
        text = "🏆 <b>Рейтинг игроков:</b>\n\n"
        for i, (uname, pts) in enumerate(players):
            medal = medals[i] if i < 3 else ""
            text += f"{i+1}) {medal} {uname} — {pts} очков\n"

    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text)
    else:
        await message_or_callback.message.edit_text(text, reply_markup=main_menu_kb())
