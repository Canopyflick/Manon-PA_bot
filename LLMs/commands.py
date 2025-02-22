from telegram import Update
from telegram.ext import CallbackContext

from LLMs.orchestration import other_message_o1, handle_goal_classification
from leftovers.commands import logger


async def o1_command(update: Update, context: CallbackContext):
    logger.warning("triggered /o1")
    await other_message_o1(update, context)


async def smarter_command(update: Update, context: CallbackContext):
    """
    For complex goal setting, where you want to avoid mini
    """
    logger.warning("triggered /smarter")
    await handle_goal_classification(update, context, smarter=True)
