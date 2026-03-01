# features/bitcoin/command.py
from telegram import Update
from telegram.ext import ContextTypes
from features.bitcoin.monitoring import get_btc_price, get_btc_thresholds, set_btc_anchor, _btc_state
from utils.environment_vars import ENV_VARS


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


async def btc_alert_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    View or set BTC price alert anchor. Approved users only.
    /btc_alert        — show current anchor, thresholds, and price
    /btc_alert <price> — set anchor to given price (thresholds auto-calculate as ±15%)
    """
    user_id = update.effective_user.id
    if user_id not in ENV_VARS.APPROVED_USER_IDS:
        await update.message.reply_text("🚫 This command is restricted.")
        return

    # Set new anchor
    if context.args:
        try:
            new_anchor = float(context.args[0].replace(",", ""))
            if new_anchor <= 0:
                raise ValueError
            set_btc_anchor(new_anchor)
            lower, upper = get_btc_thresholds()
            await update.message.reply_text(
                f"✅ Anchor set to ${new_anchor:,.0f}\n"
                f"📉 Lower alert: ${lower:,.0f}\n"
                f"🚀 Upper alert: ${upper:,.0f}"
            )
        except (ValueError, IndexError):
            await update.message.reply_text("Usage: /btc\\_alert <price>\nExample: /btc\\_alert 100000", parse_mode="Markdown")
        return

    # Show current state
    anchor = _btc_state["anchor_price"]
    if anchor is None:
        await update.message.reply_text("No anchor set yet — it will initialize on the next price fetch.")
        return

    lower, upper = get_btc_thresholds()
    bitcoin_price = await get_btc_price()
    price = bitcoin_price.raw_price

    await update.message.reply_text(
        f"⚓ Anchor: ${anchor:,.0f}\n"
        f"📉 Lower alert: ${lower:,.0f}\n"
        f"🚀 Upper alert: ${upper:,.0f}\n"
        f"💰 Current price: ${price:,.0f}"
    )
