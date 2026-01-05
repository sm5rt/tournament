from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def tournament_format_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 команды", callback_data="format_2")],
        [InlineKeyboardButton(text="4 команды", callback_data="format_4")],
        [InlineKeyboardButton(text="8 команд", callback_data="format_8")],
        [InlineKeyboardButton(text="16 команд", callback_data="format_16")],
        [InlineKeyboardButton(text="Рандомные команды", callback_data="format_random")]
    ])

def expand_or_start_kb(current_format: str):
    next_map = {"2": "4", "4": "8", "8": "16"}
    buttons = []
    if current_format in next_map:
        buttons.append([
            InlineKeyboardButton(
                text=f"➕ Расширить до {next_map[current_format]} команд",
                callback_data=f"expand_{next_map[current_format]}"
            )
        ])
    buttons.append([
        InlineKeyboardButton(text="✅ Начать турнир", callback_data="start_tournament")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def match_result_kb(match_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Команда 1 победила", callback_data=f"result_{match_id}_1")],
        [InlineKeyboardButton(text="Команда 2 победила", callback_data=f"result_{match_id}_2")]
    ])

def tournament_history_kb(tournaments):
    buttons = []
    for t in tournaments:
        buttons.append([InlineKeyboardButton(
            text=f"{t[1]} ({t[3][:10]})",
            callback_data=f"view_tournament_{t[0]}"
        )])
    buttons.append([InlineKeyboardButton(text="Назад", callback_data="back_to_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def tournament_action_kb(tournament_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Удалить", callback_data=f"del_tournament_{tournament_id}")],
        [InlineKeyboardButton(text="Назад", callback_data="historytournament")]
    ])

def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="История турниров", callback_data="historytournament")],
        [InlineKeyboardButton(text="Рейтинг игроков", callback_data="list_players")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help_command")]
    ])
