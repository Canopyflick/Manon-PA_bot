from features.diceroll.roll import roll_dice
from leftovers.commands import logger
from utils.listener import logger


async def dice_command(update, context):
    if context.args:  # Input from a command like /stopwatch 10
        arg = context.args[0]
        if arg.isdigit() and 1 <= int(arg) <= 6:
            await roll_dice(update, context, user_guess=arg)
            logger.info(f"Dice roll {arg}")
            return
    else:
        await roll_dice(update, context, user_guess=None)
        logger.info("Dice roll numberless")
