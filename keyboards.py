from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def tournament_format_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2 команды", callback_data="format_2")],
        [InlineKeyboardButton(text="4 команды", callback_data="format_4")],
        [InlineKeyboardButton(text="8 команд", callback_data="format_8")],
        [InlineKeyboardButton(text="16 команд", callback_data="format_16")],
        [InlineKeyboardButton(text="Рандомные команды", callback_data="format_random")]
    ])

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
        [InlineKeyboardButton(text="Создать турнир", callback_data="create_tournament")],
        [InlineKeyboardButton(text="История турниров", callback_data="historytournament")],
        [InlineKeyboardButton(text="Рейтинг игроков", callback_data="list_players")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help_command")]
    ])