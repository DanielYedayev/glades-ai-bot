import logging
import requests
import schedule
import time
import threading
from telegram import Bot
from telegram.ext import Updater, CommandHandler
from datetime import datetime
from bs4 import BeautifulSoup

# === CONFIGURATION ===
TELEGRAM_BOT_TOKEN = "7532088481:AAHJdxqh15pSST4BxtoIXtvrYmrR18Ex8pg"
TELEGRAM_CHAT_ID = None  # Will be auto-filled on first /start
TIMEZONE_OFFSET = 3  # Israel = UTC+3

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# === LOGGING ===
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# === PRICE FUNCTION ===
def fetch_price():
    url = "https://api.coingecko.com/api/v3/coins/glades"
    try:
        res = requests.get(url)
        data = res.json()
        price = data["market_data"]["current_price"]["usd"]
        market_cap = data["market_data"]["market_cap"]["usd"]
        return price, market_cap
    except Exception as e:
        print("Error fetching price:", e)
        return None, None

def send_price():
    price, market_cap = fetch_price()
    if price:
        now = datetime.utcnow().hour + TIMEZONE_OFFSET
        time_of_day = "Morning" if now < 15 else "Evening"
        msg = f"📊 *{time_of_day} GLDS Update:*\n\n💰 Price: ${price:.5f}\n📈 Market Cap: ${market_cap:,.0f}"
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg, parse_mode="Markdown")

# === TWITTER CHECK ===
last_tweet = None
def check_twitter():
    global last_tweet
    try:
        res = requests.get("https://nitter.net/GladesAI/rss")  # Nitter RSS (no API needed)
        soup = BeautifulSoup(res.text, 'xml')
        tweet = soup.find('item')
        link = tweet.find('link').text
        title = tweet.find('title').text
        if link != last_tweet:
            last_tweet = link
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"🐦 New Tweet from GladesAI:\n{title}\n{link}")
    except Exception as e:
        print("Twitter check failed:", e)

# === GITHUB CHECK ===
last_commit = None
def check_github():
    global last_commit
    try:
        res = requests.get("https://api.github.com/repos/rcarneiro/glades-ml/commits")
        data = res.json()
        latest = data[0]["html_url"]
        msg = data[0]["commit"]["message"]
        if latest != last_commit:
            last_commit = latest
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"💻 New GitHub Commit:\n{msg}\n{latest}")
    except Exception as e:
        print("GitHub check failed:", e)

# === NEWS CHECK ===
last_news = None
def check_news():
    global last_news
    try:
        url = "https://www.coingecko.com/en/coins/glades/rss"
        res = requests.get(url)
        soup = BeautifulSoup(res.text, 'xml')
        item = soup.find('item')
        title = item.find('title').text
        link = item.find('link').text
        if link != last_news:
            last_news = link
            bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=f"📰 Glades AI News:\n{title}\n{link}")
    except Exception as e:
        print("News check failed:", e)

# === TELEGRAM BOT COMMANDS ===
def start(update, context):
    global TELEGRAM_CHAT_ID
    TELEGRAM_CHAT_ID = update.message.chat_id
    update.message.reply_text("✅ Glades AI Bot activated.\nYou’ll now receive live news, tweets, commits + price twice a day.")

def news(update, context):
    price, market_cap = fetch_price()
    if price:
        msg = f"📊 *Current GLDS Stats:*\n💰 Price: ${price:.5f}\n📈 Market Cap: ${market_cap:,.0f}"
        update.message.reply_text(msg, parse_mode="Markdown")

# === SCHEDULING ===
def run_scheduled():
    schedule.every().day.at("06:00").do(send_price)  # 9:00 Israel (UTC+3)
    schedule.every().day.at("17:00").do(send_price)  # 20:00 Israel (UTC+3)
    while True:
        schedule.run_pending()
        time.sleep(30)

def run_checks():
    while True:
        if TELEGRAM_CHAT_ID:
            check_twitter()
            check_github()
            check_news()
        time.sleep(60)

# === MAIN ===
def main():
    updater = Updater(TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("news", news))
    threading.Thread(target=run_scheduled).start()
    threading.Thread(target=run_checks).start()
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()