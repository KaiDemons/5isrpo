from telebot import types
from config import USER_ROLES  # Импортируем роли пользователей

def main_menu_keyboard(role=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    item_rent = types.KeyboardButton('🔄 Арендовать')
    item_help = types.KeyboardButton('ℹ️ Помощь')
    markup.add(item_rent, item_help)

    if role == 'seller':  # Отчеты доступны только продавцам
        item_reports = types.KeyboardButton('📊 Отчеты')
        markup.add(item_reports)

    if role == 'seller':
        item_add_inventory = types.KeyboardButton('➕ Добавить инвентарь')
        markup.add(item_add_inventory)

    return markup


def role_selection_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for role, role_name in USER_ROLES.items():
        markup.add(role_name)
    return markup