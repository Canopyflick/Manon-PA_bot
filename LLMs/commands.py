from telegram import Update
from telegram.ext import CallbackContext

from LLMs.orchestration import other_message_pro, handle_goal_classification
from leftovers.commands import logger


async def pro_command(update: Update, context: CallbackContext):
    logger.warning("triggered /pro")
    await other_message_pro(update, context)


async def smarter_command(update: Update, context: CallbackContext):
    """
    For complex goal setting, where you want to avoid mini
    """
    logger.warning("triggered /smarter")
    await handle_goal_classification(update, context, smarter=True)
