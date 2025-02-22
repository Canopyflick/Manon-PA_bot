import logging

logger = logging.getLogger(__name__)

async def add_user_context_to_goals(context, goal_id, **kwargs):
    """
    Adds or updates fields for a specific goal_id in user_data, flattening dictionaries and removing parent key names, such that only the deepest child keys remain (preserving all types).

    Args:
        context: The context object from the Telegram bot.
        goal_id: The unique ID of the goal to update.
        **kwargs: Key-value pairs to add or update in the goal's context.
    """
    # Ensure the goals dictionary exists
    if "goals" not in context.user_data:
        context.user_data["goals"] = {}

    # Ensure the specific goal_id dictionary exists
    if goal_id not in context.user_data["goals"]:
        context.user_data["goals"][goal_id] = {}

    # Flatten and store all input data
    for key, value in kwargs.items():
        if isinstance(value, dict):  # Flatten nested dictionaries
            for sub_key, sub_value in value.items():
                logger.info(f"Adding |{sub_key}| : |{sub_value}| to context")
                context.user_data["goals"][goal_id][sub_key] = sub_value
        elif hasattr(value, "__dict__"):  # Flatten custom objects
            for sub_key, sub_value in value.__dict__.items():
                logger.info(f"Adding |{sub_key}| : |{sub_value}| to context")
                context.user_data["goals"][goal_id][sub_key] = sub_value
        else:  # Directly store primitive types
            logger.info(f"Adding |{key}| : |{value}| to context")
            context.user_data["goals"][goal_id][key] = value
