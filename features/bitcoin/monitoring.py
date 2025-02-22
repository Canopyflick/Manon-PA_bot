# features/bitcoin/monitoring.py
import asyncio

import requests
from telegram import Bot


async def monitor_btc_price(bot: Bot, chat_id: int):
    """
    Function to check Bitcoin price every ten minutes and send a message if it crosses the thresholds
    """
    lower_threshold = 88888
    upper_threshold = 111111
    upper_threshold_alerted = False
    lower_threshold_alerted = False
    while True:
        _, _, price, _ = await get_btc_price()
        if price is not None:
            print(f"Bitcoin price: ${price:,.2f}")  # Log the price
            if price > upper_threshold and not upper_threshold_alerted:
                message = f"*🚀 Bitcoin price alert!*\n1₿ is now ${price:,.2f} USD, exceeding the threshold of ${upper_threshold:,.2f}"
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                upper_threshold_alerted = True
                lower_threshold_alerted = False  # Reset lower threshold flag

            elif price < lower_threshold and not lower_threshold_alerted:
                message = f"*📉 Bitcoin price alert!*\n1₿ is now ${price:,.2f} USD, dropping below the threshold of ${lower_threshold:,.2f}"
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                lower_threshold_alerted = True
                upper_threshold_alerted = False  # Reset upper threshold flag

        await asyncio.sleep(600)  # Wait for 10 minutes before checking again


async def get_btc_price() -> tuple[str, str, float, float]:
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur&include_24hr_change=true"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses
        data = response.json()
        usd_price = float(data["bitcoin"]["usd"])  # Convert to float for formatting
        eur_price = float(data["bitcoin"]["eur"])  # Convert to float for formatting
        usd_change = float(data["bitcoin"]["usd_24h_change"])  # 24-hour percentage change


        mycelium_balance = 0.01614903
        mycelium_euros = round(eur_price * mycelium_balance, 2)

        # Format the prices with a comma as the thousands separator
        usd_price_formatted = f"{usd_price:,.0f}"
        mycelium_euros_formatted = f"{mycelium_euros:,.0f}"

        # Return two different outputs
        simple_message = f"${usd_price_formatted}"
        detailed_message = f"1₿ = ${usd_price_formatted}\n🍄 = €{mycelium_euros_formatted}"
        raw_float_price = usd_price

        return simple_message, detailed_message, raw_float_price, usd_change
    except requests.RequestException as e:
        # Default values in case of error
        simple_message = "Error"
        detailed_message = f"Error fetching Bitcoin price: {e}"
        raw_float_price = 0.0
        usd_change = 0.0
        return simple_message, detailed_message, raw_float_price, usd_change


async def get_btc_change_message():
    """
    Retrieves the Bitcoin price details and returns a formatted update message if the price
    change exceeds 5% over the last 24 hours; otherwise, returns an empty string.
    """
    _, detailed_message, _, usd_change = await get_btc_price()
    if abs(usd_change) > 5:
        return f"\n\n📈 _฿itcoin price changed by {usd_change:.2f}% in the last 24 hours._\n{detailed_message}"
    return ""
