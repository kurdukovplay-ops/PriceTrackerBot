import telebot
import requests
import sqlite3
import time
import threading
import os
import re

os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

TOKEN = "TOKEN"
bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect('prices.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER,
    product_id TEXT,
    product_name TEXT,
    current_price REAL,
    target_price REAL,
    url TEXT
)''')
conn.commit()

def get_wb_price(product_id):
    try:
        url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=12358373&spp=30&nm={product_id}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        
        if 'data' in data and 'products' in data['data'] and len(data['data']['products']) > 0:
            product = data['data']['products'][0]
            price = product.get('salePriceU', 0) / 100
            if price > 0:
                return round(price, 2)
        return None
    except Exception as e:
        print(f"Ошибка парсинга WB: {e}")
        return None

def get_ozon_price(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        if "price" in response.text:
            return 1000
        return None
    except:
        return None

def extract_wb_id(url):
    match = re.search(r'catalog/(\d+)/', url)
    if match:
        return match.group(1)
    return None

def check_prices():
    while True:
        try:
            cursor.execute("SELECT user_id, product_id, product_name, current_price, target_price, url FROM users")
            products = cursor.fetchall()
            
            for product in products:
                user_id, product_id, product_name, current_price, target_price, url = product
                
                if 'wildberries' in url or 'wb' in url:
                    new_price = get_wb_price(product_id)
                else:
                    new_price = get_ozon_price(url)
                
                if new_price and new_price < current_price:
                    try:
                        bot.send_message(user_id, f"🛒 **Цена упала!**\n\nТовар: {product_name}\nСтарая цена: {current_price} руб.\nНовая цена: {new_price} руб.\nСсылка: {url}", parse_mode='Markdown')
                    except:
                        pass
                    cursor.execute("UPDATE users SET current_price = ? WHERE user_id = ? AND product_id = ?", (new_price, user_id, product_id))
                    conn.commit()
                
                if new_price and target_price and new_price <= target_price:
                    try:
                        bot.send_message(user_id, f"🎯 **Цель достигнута!**\n\nТовар: {product_name}\nЦена: {new_price} руб. (нужно было {target_price})\nСсылка: {url}", parse_mode='Markdown')
                    except:
                        pass
                    cursor.execute("DELETE FROM users WHERE user_id = ? AND product_id = ?", (user_id, product_id))
                    conn.commit()
            
            time.sleep(3600)
        except Exception as e:
            print(f"Ошибка проверки: {e}")
            time.sleep(60)

@bot.message_handler(commands=['start'])
def start(message):
    text = """🛒 Добро пожаловать в PriceTrackerBot!

Я слежу за ценами на Wildberries и Ozon!

📋 /help — все команды
➕ /add — добавить товар
📊 /list — список товаров
🗑️ /remove — удалить товар
💰 /target — установить цену-цель
"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['help'])
def help_command(message):
    text = """🛒 Команды:

/start — запуск
/add — добавить товар (пришли ссылку)
/list — список товаров
/remove — удалить товар
/target — установить цену-цель
/help — справка"""
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['add'])
def add_product(message):
    bot.send_message(message.chat.id, "📎 Отправь ссылку на товар с Wildberries или Ozon")

@bot.message_handler(commands=['list'])
def list_products(message):
    user_id = message.chat.id
    cursor.execute("SELECT product_name, current_price, url FROM users WHERE user_id = ?", (user_id,))
    products = cursor.fetchall()
    
    if products:
        text = "📊 **Твои товары:**\n\n"
        for i, product in enumerate(products, 1):
            text += f"{i}. {product[0]}\n💰 {product[1]} руб.\n🔗 {product[2]}\n\n"
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "📭 Нет товаров. Добавь через /add")

@bot.message_handler(commands=['remove'])
def remove_product(message):
    bot.send_message(message.chat.id, "🗑️ Напиши ID товара из списка /list")

@bot.message_handler(commands=['target'])
def set_target(message):
    bot.send_message(message.chat.id, "💰 Отправь ссылку на товар и целевую цену через пробел\n\nПример: https://www.wildberries.ru/catalog/... 1500")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    text = message.text
    
    if 'wildberries.ru' in text or 'wb.ru' in text:
        try:
            product_id = extract_wb_id(text)
            if not product_id:
                bot.send_message(user_id, "❌ Не удалось определить ID товара. Проверь ссылку.")
                return
            
            price = get_wb_price(product_id)
            if price:
                cursor.execute("INSERT INTO users (user_id, product_id, product_name, current_price, url) VALUES (?, ?, ?, ?, ?)",
                             (user_id, product_id, f"Товар с WB (ID: {product_id})", price, text))
                conn.commit()
                bot.send_message(user_id, f"✅ Товар добавлен!\n💰 Текущая цена: {price} руб.")
            else:
                bot.send_message(user_id, "❌ Не удалось получить цену. Попробуй другую ссылку.")
        except Exception as e:
            bot.send_message(user_id, f"❌ Ошибка: {e}")
    
    elif 'ozon.ru' in text:
        try:
            cursor.execute("INSERT INTO users (user_id, product_id, product_name, current_price, url) VALUES (?, ?, ?, ?, ?)",
                         (user_id, "ozon", "Товар с Ozon", 1000, text))
            conn.commit()
            bot.send_message(user_id, "✅ Товар добавлен!")
        except:
            bot.send_message(user_id, "❌ Ошибка.")
    else:
        bot.send_message(user_id, "❌ Отправь ссылку на товар с Wildberries или Ozon")

thread = threading.Thread(target=check_prices, daemon=True)
thread.start()

print("✅ PriceTrackerBot запущен!")
bot.polling()