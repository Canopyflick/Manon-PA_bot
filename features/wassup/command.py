# features/wassup/command.py

from telegram import Update
from telegram.ext import ContextTypes
from features.bitcoin.monitoring import get_btc_price


async def wassup_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Starts a multi-branch flow of semi-randomized actions for the user.
    1. If they have open-ended goals, the llm picks 1 to do + a random other one, otherwise 1 or 2 are shown by default
        1.1 option to accept either or both -> moves it to user-specified deadline
        1.2 IF user has >2, option to click "More" button, showing a further random max 7 open-ended goals to choose from
    2. If they don't have open-ended goals, LLM gives like a summary of ... everything they know about the user
    3. SOMETIMES, the LLM also tells a joke
    """



