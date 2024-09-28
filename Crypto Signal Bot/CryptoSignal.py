from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import requests
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import tempfile
import numpy as np

TOKEN = '7384849148:AAFwvYuP0aaVD8NRBwxnQ6T8uRYXh5LzJvU' # Your Telegram Token



def get_crypto_data(crypto_id='bitcoin'):
    url = f'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'ids': crypto_id
    }
    response = requests.get(url, params=params)
    data = response.json()[0]
    return data

def get_crypto_graph(crypto_id='bitcoin'):
    url = f'https://api.coingecko.com/api/v3/coins/{crypto_id}/market_chart'
    params = {
        'vs_currency': 'usd',
        'days': '30'
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data['prices']

def calculate_sma(data, window):
    sma = data.rolling(window=window).mean()
    return sma

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)

    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(data, short_window=12, long_window=26, signal_window=9):
    exp1 = data.ewm(span=short_window, adjust=False).mean()
    exp2 = data.ewm(span=long_window, adjust=False).mean()
    macd = exp1 - exp2
    signal = macd.ewm(span=signal_window, adjust=False).mean()
    return macd, signal


def generate_advanced_signal(prices):
    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['price'] = df['price'].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)

    short_window = 40
    long_window = 100

    df['SMA40'] = calculate_sma(df['price'], short_window)
    df['SMA100'] = calculate_sma(df['price'], long_window)
    df['RSI'] = calculate_rsi(df['price'])
    df['MACD'], df['Signal'] = calculate_macd(df['price'])

    buy_signals = (df['SMA40'] > df['SMA100']) & (df['RSI'] < 30) & (df['MACD'] > df['Signal'])
    sell_signals = (df['SMA40'] < df['SMA100']) & (df['RSI'] > 70) & (df['MACD'] < df['Signal'])

    if buy_signals.iloc[-1]:
        return 'Buy'
    elif sell_signals.iloc[-1]:
        return 'Sell'
    else:
        return 'Wait'

def plot_crypto_graph(prices, crypto_id):
    dates = [datetime.datetime.fromtimestamp(price[0] / 1000) for price in prices]
    values = [price[1] for price in prices]

    plt.figure(figsize=(10, 5))
    plt.plot(dates, values)
    plt.title(f'{crypto_id.capitalize()} Price Chart (Last 30 Days)')
    plt.xlabel('Date')
    plt.ylabel('Price (USD)')
    plt.grid(True)
    
    # Geçici bir dosya oluşturma
    with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as tmpfile:
        filepath = tmpfile.name
        plt.savefig(filepath)
    plt.close()
    return filepath

def get_crypto_price(crypto_id='bitcoin'):
    url = f'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': crypto_id,
        'vs_currencies': 'usd'
    }
    response = requests.get(url, params=params)
    data = response.json()
    return data[crypto_id]['usd']

def get_filtered_crypto_list(min_market_cap=1000000):
    url = 'https://api.coingecko.com/api/v3/coins/markets'
    params = {
        'vs_currency': 'usd',
        'order': 'market_cap_desc',
        'per_page': 250,
        'page': 1
    }
    response = requests.get(url, params=params)
    data = response.json()
    
    filtered_data = [coin['id'] for coin in data if coin['market_cap'] >= min_market_cap]
    return filtered_data



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello! Welcome to the crypto signal bot.')

async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    crypto_id = context.args[0] if context.args else 'bitcoin'
    try:
        prices = get_crypto_graph(crypto_id)
        signal = generate_advanced_signal(prices)
        await update.message.reply_text(f"{crypto_id.capitalize()}  signal: {signal}")
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid cryptocurrency ID.")

async def coins(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    crypto_list = get_filtered_crypto_list()
    await update.message.reply_text("Available cryptocurrencies:\n" + "\n".join(crypto_list[:50]))

async def graphic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    crypto_id = context.args[0] if context.args else 'bitcoin'
    try:
        prices = get_crypto_graph(crypto_id)
        filepath = plot_crypto_graph(prices, crypto_id)
        await update.message.reply_photo(photo=open(filepath, 'rb'))
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid cryptocurrency ID.")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    crypto_id = context.args[0] if context.args else 'bitcoin'
    try:
        price = get_crypto_price(crypto_id)
        await update.message.reply_text(f"{crypto_id.capitalize()} current price: ${price}")
    except (IndexError, ValueError):
        await update.message.reply_text("Invalid cryptocurrency ID.")

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("signal", signal))
    application.add_handler(CommandHandler("coins", coins))
    application.add_handler(CommandHandler("graphic", graphic))
    application.add_handler(CommandHandler("price", price))

    application.run_polling()

if __name__ == '__main__':
    
    main()
