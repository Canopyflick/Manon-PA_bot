# features/bitcoin/monitoring.py
import asyncio
import logging
from models.bitcoin import BitcoinPrice
import requests
from telegram import Bot

logger = logging.getLogger(__name__)

STEP_PERCENT = 0.15  # 15% change triggers an alert

# Module-level state for threshold monitoring
_btc_state = {
    "anchor_price": None,   # Price that thresholds are based on; set on first fetch or via command
    "alerted_upper": False,
    "alerted_lower": False,
}


def get_btc_thresholds():
    """Return (lower, upper) thresholds based on current anchor, or (None, None) if no anchor."""
    anchor = _btc_state["anchor_price"]
    if anchor is None:
        return None, None
    return anchor * (1 - STEP_PERCENT), anchor * (1 + STEP_PERCENT)


def set_btc_anchor(price: float):
    """Set a new anchor price and reset alert flags."""
    _btc_state["anchor_price"] = price
    _btc_state["alerted_upper"] = False
    _btc_state["alerted_lower"] = False
    logger.info(f"BTC anchor set to ${price:,.0f} — thresholds: ${price * (1 - STEP_PERCENT):,.0f} / ${price * (1 + STEP_PERCENT):,.0f}")


async def monitor_btc_price(bot: Bot, chat_id: int):
    """
    Check Bitcoin price every ten minutes. Alert when price moves ±15% from anchor.
    On alert, anchor auto-steps to the new price.
    """
    while True:
        try:
            bitcoin_price = await get_btc_price()
            price = bitcoin_price.raw_price
            if price is None or price == 0.0:
                await asyncio.sleep(600)
                continue

            logger.info(f"Bitcoin price: ${price:,.0f}")

            # Initialize anchor on first successful fetch
            if _btc_state["anchor_price"] is None:
                set_btc_anchor(price)
                await asyncio.sleep(600)
                continue

            lower, upper = get_btc_thresholds()

            if price > upper and not _btc_state["alerted_upper"]:
                pct = ((price - _btc_state["anchor_price"]) / _btc_state["anchor_price"]) * 100
                message = (
                    f"*🚀 Bitcoin price alert!*\n1₿ is now ${price:,.0f} USD "
                    f"(+{pct:.1f}% from ${_btc_state['anchor_price']:,.0f})"
                )
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                set_btc_anchor(price)  # Auto-step: new anchor at current price

            elif price < lower and not _btc_state["alerted_lower"]:
                pct = ((_btc_state["anchor_price"] - price) / _btc_state["anchor_price"]) * 100
                message = (
                    f"*📉 Bitcoin price alert!*\n1₿ is now ${price:,.0f} USD "
                    f"(-{pct:.1f}% from ${_btc_state['anchor_price']:,.0f})"
                )
                await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
                set_btc_anchor(price)  # Auto-step: new anchor at current price

        except Exception as e:
            logger.error(f"Error in monitor_btc_price loop: {e}")

        await asyncio.sleep(600)  # 10 minutes


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
        logger.error(f"Error in get_btc_change_message: {e}")
        return ""
