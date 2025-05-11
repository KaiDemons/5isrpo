import telebot
from telebot import types
from datetime import datetime, timedelta
from database import Database
import keyboards as kb
from config import BOT_TOKEN, INVENTORY_TYPES, USER_ROLES

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

user_states = {}  # Для отслеживания состояния регистрации


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    role = db.get_user_role(user_id)

    if role:
        # Пользователь уже зарегистрирован, показываем меню в зависимости от роли
        markup = kb.main_menu_keyboard(role)
        bot.send_message(message.chat.id, f"С возвращением! Ваша роль: {USER_ROLES[role]}", reply_markup=markup)
    else:
        # Предлагаем выбрать роль
        user_states[user_id] = 'waiting_for_role'
        markup = kb.role_selection_keyboard()
        bot.send_message(message.chat.id, "Пожалуйста, выберите свою роль:", reply_markup=markup)


@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) == 'waiting_for_role')
def process_role_selection(message):
    user_id = message.from_user.id
    selected_role_name = message.text

    # Ищем роль по названию
    selected_role = None
    for role, role_name in USER_ROLES.items():
        if role_name == selected_role_name:
            selected_role = role
            break

    if selected_role:
        if db.add_user(message.from_user.id, selected_role):
            bot.send_message(message.chat.id, f"Вы успешно зарегистрированы как {selected_role_name}!",
                             reply_markup=kb.main_menu_keyboard(selected_role))
        else:
            bot.send_message(message.chat.id, "Ошибка регистрации. Возможно, вы уже зарегистрированы.",
                             reply_markup=kb.main_menu_keyboard())
        del user_states[user_id]  # Сбрасываем состояние
    else:
        bot.send_message(message.chat.id, "Некорректная роль. Пожалуйста, выберите из предложенных.")


@bot.message_handler(func=lambda m: m.text == '🔄 Арендовать')
def start_rental(message):
    try:
        markup = types.InlineKeyboardMarkup()
        available_items = db.get_available_items()
        if available_items:
            for item in available_items:
                markup.add(types.InlineKeyboardButton(
                    f"{item[1]} {item[2]}",
                    callback_data=f"rent_{item[0]}"
                ))
            bot.send_message(message.chat.id, "Выберите инвентарь:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Нет доступного инвентаря для аренды.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при получении списка инвентаря: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('rent_'))
def process_rental(call):
    item_id = call.data.split('_')[1]
    user_id = call.from_user.id
    user_states[user_id] = {'state': 'waiting_for_duration', 'item_id': item_id}
    msg = bot.send_message(call.message.chat.id, "На сколько часов вы хотите арендовать?")
    bot.register_next_step_handler(msg, process_rental_duration)


def process_rental_duration(message):
    user_id = message.from_user.id
    try:
        rental_duration = int(message.text)
        if rental_duration <= 0:
            raise ValueError("Продолжительность аренды должна быть положительным числом.")

        item_id = user_states[user_id]['item_id']
        # Получаем цену за час из БД
        item_price_per_hour = db.get_item_price_per_hour(item_id)

        # Рассчитываем стоимость аренды
        total_cost = rental_duration * item_price_per_hour

        user_states[user_id]['rental_duration'] = rental_duration
        user_states[user_id]['total_cost'] = total_cost

        msg = bot.send_message(message.chat.id, f"Ваш номер телефона:")
        bot.register_next_step_handler(msg, process_phone)

    except ValueError as e:
        bot.send_message(message.chat.id,
                         f"Некорректный ввод. Пожалуйста, введите целое число часов (больше нуля). Ошибка: {e}")
        del user_states[user_id]


def process_phone(message):
    user_id = message.from_user.id
    try:
        phone = message.text

        item_id = user_states[user_id]['item_id']
        rental_duration = user_states[user_id]['rental_duration']
        total_cost = user_states[user_id]['total_cost']

        client_id = db.add_client(message.from_user.first_name, phone)
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=rental_duration)

        rental_id = db.create_rental_with_details(client_id, item_id, start_time.strftime("%Y-%m-%d %H:%M:%S"),
                                                  end_time.strftime("%Y-%m-%d %H:%M:%S"), total_cost)
        db.update_inventory_status(item_id, 'rented')  # добавьте эту строчку после создания объекта

        bot.send_message(message.chat.id,
                         f"Аренда оформлена! ID: {rental_id}\nПродолжительность: {rental_duration} ч.\nСтоимость: {total_cost} руб.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при оформлении аренды: {e}")
    finally:
        del user_states[user_id]


@bot.message_handler(func=lambda m: m.text == '📊 Отчеты')
def show_reports(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('💰 Финансовый отчет', callback_data='report_finance'),
               types.InlineKeyboardButton('📦 Отчет по инвентарю', callback_data='report_inventory'),
               types.InlineKeyboardButton('🏆 Популярные позиции', callback_data='report_popular'))
    bot.send_message(message.chat.id, "Выберите тип отчета:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('report_'))
def handle_reports(call):
    report_type = call.data.split('_')[1]

    try:
        if report_type == 'finance':
            data = db.get_financial_report('2023-01-01', '2023-12-31')
            if data:
                text = f"Общий доход: {data[0]} руб.\nКоличество аренд: {data[1]}"
            else:
                text = "Нет данных для финансового отчета."
        elif report_type == 'inventory':
            text = "Состояние инвентаря:\n"
            for row in db.get_inventory_report():
                text += f"{row[0]}: {row[2]} шт. ({row[1]})\n"
        else:
            text = "Самые популярные:\n"
            for i, row in enumerate(db.get_popular_items(), 1):
                text += f"{i}. ID {row[0]} - {row[1]} аренд\n"

        bot.send_message(call.message.chat.id, text)
    except Exception as e:
        bot.send_message(call.message.chat.id, f"Произошла ошибка при формировании отчета: {e}")


# Добавляем функциональность добавления инвентаря (только для продавцов)
add_inventory_states = {}  # Для отслеживания состояния добавления инвентаря


@bot.message_handler(
    func=lambda message: db.get_user_role(message.from_user.id) == 'seller' and message.text == '➕ Добавить инвентарь')
def add_inventory_start(message):
    user_id = message.from_user.id
    add_inventory_states[user_id] = {'state': 'waiting_for_type'}

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for item_type in INVENTORY_TYPES:  # Используем типы из config.py
        markup.add(item_type)
    bot.send_message(message.chat.id, "Выберите тип инвентаря:", reply_markup=markup)
    bot.register_next_step_handler(message, process_inventory_type)


def process_inventory_type(message):
    user_id = message.from_user.id
    inventory_type = message.text

    if inventory_type not in INVENTORY_TYPES:
        bot.send_message(message.chat.id, "Некорректный тип инвентаря. Пожалуйста, выберите из предложенных.")
        del add_inventory_states[user_id]  # Сбрасываем состояние
        return

    add_inventory_states[user_id]['type'] = inventory_type
    add_inventory_states[user_id]['state'] = 'waiting_for_brand'

    bot.send_message(message.chat.id, "Введите марку инвентаря (например, Stels):",
                     reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, process_inventory_brand)


def process_inventory_brand(message):
    user_id = message.from_user.id
    inventory_brand = message.text
    add_inventory_states[user_id]['brand'] = inventory_brand
    add_inventory_states[user_id]['state'] = 'waiting_for_size'

    bot.send_message(message.chat.id, "Введите размер инвентаря (если есть, иначе введите '-'):")
    bot.register_next_step_handler(message, process_inventory_size)


def process_inventory_size(message):
    user_id = message.from_user.id
    inventory_size = message.text
    add_inventory_states[user_id]['size'] = inventory_size
    add_inventory_states[user_id]['state'] = 'waiting_for_price'

    bot.send_message(message.chat.id, "Введите цену за час проката (только число, например, 150.0):")
    bot.register_next_step_handler(message, process_inventory_price)


def process_inventory_price(message):
    user_id = message.from_user.id
    try:
        inventory_price = float(message.text)
        add_inventory_states[user_id]['price'] = inventory_price

        # Добавляем инвентарь в базу данных
        inventory_type = add_inventory_states[user_id]['type']
        inventory_brand = add_inventory_states[user_id]['brand']
        inventory_size = add_inventory_states[user_id]['size']
        inventory_price = add_inventory_states[user_id]['price']

        item_id = db.add_inventory(inventory_type, inventory_brand, inventory_size, inventory_price)

        bot.send_message(message.chat.id, f"Инвентарь успешно добавлен с ID: {item_id}")

    except ValueError:
        bot.send_message(message.chat.id, "Некорректная цена. Пожалуйста, введите число.")

    finally:
        del add_inventory_states[user_id]  # Сбрасываем состояние
        # Возвращаемся в главное меню
        role = db.get_user_role(user_id)  # Получаем роль пользователя
        markup = kb.main_menu_keyboard(role)
        bot.send_message(message.chat.id, "Возвращаюсь в главное меню.", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text == 'ℹ️ Помощь')
def show_help(message):
    help_text = """
    Доступные команды:
    /start - Начать работу с ботом
    🔄 Арендовать - Посмотреть доступный инвентарь и оформить аренду
    📊 Отчеты - Посмотреть отчеты по работе пункта проката
    ℹ️ Помощь - Показать это сообщение
    """
    bot.send_message(message.chat.id, help_text)


if __name__ == '__main__':
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"Бот упал с ошибкой: {e}")