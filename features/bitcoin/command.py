# features/bitcoin/command.py
from telegram import Update
from telegram.ext import ContextTypes
from features.bitcoin.monitoring import get_btc_price


async def btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Replies with a short (simple) message.
    """
    bitcoin_price = await get_btc_price()
    await update.message.reply_text(bitcoin_price.simple_message)


async def bitcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Replies with a detailed message.
    """
    bitcoin_price = await get_btc_price()
    await update.message.reply_text(bitcoin_price.detailed_message)
