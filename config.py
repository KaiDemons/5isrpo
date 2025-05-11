import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN', '7882001510:AAFBIM3yBGwDPXs20tD4Vq7Ji6Q-U_Z6ymw')
DB_NAME = 'rental_system.db'
INVENTORY_TYPES = ['Велосипед', 'Самокат', 'Лыжи']
INVENTORY_STATUSES = ['available', 'rented', 'maintenance', 'retired']
USER_ROLES = {
    'seller': 'Продавец',
    'buyer': 'Покупатель'
}  # Обновленные роли
RENTAL_STATUSES = ['active', 'completed']
PENALTY_LEVELS = ['Низкий', 'Средний', 'Высокий']