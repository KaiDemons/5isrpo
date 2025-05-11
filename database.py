import sqlite3
from datetime import datetime

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('rental_system.db', check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Таблица инвентаря
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY,
            type TEXT NOT NULL,
            brand TEXT NOT NULL,
            size TEXT,
            status TEXT CHECK(status IN ('available', 'rented', 'maintenance', 'retired')),
            price_per_hour REAL NOT NULL,
            registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица клиентов
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT UNIQUE,
            reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')

        # Таблица пользователей с ролью
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            telegram_id INTEGER UNIQUE NOT NULL,
            role TEXT CHECK (role IN ('seller', 'buyer')) NOT NULL
        )
        ''')

        # Таблица прокатов
        self.cursor.execute('''
        CREATE TABLE IF NOT EXISTS rentals (
            id INTEGER PRIMARY KEY,
            client_id INTEGER,
            inventory_id INTEGER,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            total_cost REAL,
            FOREIGN KEY(client_id) REFERENCES clients(id),
            FOREIGN KEY(inventory_id) REFERENCES inventory(id)
        )
        ''')
        self.conn.commit()

    def add_inventory(self, item_type, brand, size, price):
        self.cursor.execute('''
        INSERT INTO inventory (type, brand, size, status, price_per_hour)
        VALUES (?, ?, ?, 'available', ?)
        ''', (item_type, brand, size, price))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_inventory_status(self, item_id, new_status):
        self.cursor.execute('''
        UPDATE inventory SET status = ? WHERE id = ?
        ''', (new_status, item_id))
        self.conn.commit()

    def add_client(self, name, phone):
        self.cursor.execute('''
        INSERT INTO clients (name, phone) VALUES (?, ?)
        ''', (name, phone))
        self.conn.commit()
        return self.cursor.lastrowid

    # Изменённый метод для создания аренды
    def create_rental_with_details(self, client_id, item_id, start_time, end_time, total_cost):
        self.cursor.execute('''
        INSERT INTO rentals (client_id, inventory_id, start_time, end_time, total_cost)
        VALUES (?, ?, ?, ?, ?)
        ''', (client_id, item_id, start_time, end_time, total_cost))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_popular_items(self):
        self.cursor.execute('''
        SELECT inventory_id, COUNT(*) as rentals 
        FROM rentals 
        GROUP BY inventory_id 
        ORDER BY rentals DESC 
        LIMIT 5
        ''')
        return self.cursor.fetchall()

    def get_financial_report(self, start_date, end_date):
        self.cursor.execute('''
        SELECT SUM(total_cost), COUNT(*) 
        FROM rentals 
        WHERE start_time BETWEEN ? AND ?
        ''', (start_date, end_date))
        return self.cursor.fetchone()

    def get_inventory_report(self):
        self.cursor.execute('''
        SELECT type, status, COUNT(*) 
        FROM inventory 
        GROUP BY type, status
        ''')
        return self.cursor.fetchall()

    def get_available_items(self):
        self.cursor.execute('''
        SELECT id, type, brand, size, price_per_hour 
        FROM inventory 
        WHERE status = 'available'
        ''')
        return self.cursor.fetchall()

    def get_user_role(self, telegram_id):
        self.cursor.execute('''
        SELECT role FROM users WHERE telegram_id = ?
        ''', (telegram_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    # Добавляем метод для получения цены за час
    def get_item_price_per_hour(self, item_id):
        self.cursor.execute('''
        SELECT price_per_hour FROM inventory WHERE id = ?
        ''', (item_id,))
        result = self.cursor.fetchone()
        return result[0] if result else None

    def add_user(self, telegram_id, role):
        try:
            self.cursor.execute('''
            INSERT INTO users (telegram_id, role) VALUES (?, ?)
            ''', (telegram_id, role))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Пользователь уже зарегистрирован