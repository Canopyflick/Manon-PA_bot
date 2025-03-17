# features/bitcoin/monitoring.py
import asyncio
from models.bitcoin import BitcoinPrice
import requests
from telegram import Bot


async def monitor_btc_price(bot: Bot, chat_id: int):
    """
    Function to check Bitcoin price every ten minutes and send a message if it crosses a threshold
    """
    lower_threshold = 66666
    upper_threshold = 99999
    upper_threshold_alerted = False
    lower_threshold_alerted = False
    while True:
        bitcoin_price = await get_btc_price()
        price = bitcoin_price.raw_price
        if price is not None:
            print(f"Bitcoin price: ${price:,.2f}")  # Log the price
            if price > upper_threshold and not upper_threshold_alerted:
                message = (
                    f"*🚀 Bitcoin price alert!*\n1₿ is now ${price:,.2f} USD, "
                    f"exceeding the threshold of ${upper_threshold:,.2f}"
                )
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                upper_threshold_alerted = True
                lower_threshold_alerted = False  # Reset lower threshold flag

            elif price < lower_threshold and not lower_threshold_alerted:
                message = (
                    f"*📉 Bitcoin price alert!*\n1₿ is now ${price:,.2f} USD, "
                    f"dropping below the threshold of ${lower_threshold:,.2f}"
                )
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                lower_threshold_alerted = True
                upper_threshold_alerted = False  # Reset upper threshold flag

        await asyncio.sleep(600)  # Wait for 10 minutes before checking again


async def get_btc_price() -> BitcoinPrice:
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

        simple_message = f"${usd_price_formatted}"
        detailed_message = f"1₿ = ${usd_price_formatted}\n🍄 = €{mycelium_euros_formatted}"
        raw_float_price = usd_price

        return BitcoinPrice(
            simple_message=simple_message,
            detailed_message=detailed_message,
            raw_price=raw_float_price,
            usd_change=usd_change,
        )
    except requests.RequestException as e:
        simple_message = "Error"
        detailed_message = f"Error fetching Bitcoin price: {e}"
        return BitcoinPrice(
            simple_message=simple_message,
            detailed_message=detailed_message,
            raw_price=0.0,
            usd_change=0.0,
        )


async def get_btc_change_message() -> str:
    """
    Retrieves the Bitcoin price details and returns a formatted update message if the price
    change exceeds 5% over the last 24 hours; otherwise, returns an empty string.
    """
    try:
        bitcoin_price = await get_btc_price()
        if abs(bitcoin_price.usd_change) > 5:
            return (
                f"\n\n📈 _฿itcoin price changed by {bitcoin_price.usd_change:.2f}% "
                f"in the last 24 hours._\n{bitcoin_price.detailed_message}"
            )
        return ""
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in get_btc_change_message: {e}")
        return ""
