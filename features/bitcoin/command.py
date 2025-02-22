from telegram import Update
from telegram.ext import ContextTypes

from features.bitcoin.monitoring import get_btc_price


async def btc_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    simple_message, _, _, _ = await get_btc_price()
    await update.message.reply_text(simple_message)


async def bitcoin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _, detailed_message, _, _ = await get_btc_price()
    await update.message.reply_text(detailed_message)
