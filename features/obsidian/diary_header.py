import asyncio

from LLMs.config import shared_state
from LLMs.orchestration import logger, get_input_variables, run_chain
from LLMs.structured_output_schemas import DiaryHeader
from telegram_helpers.delete_message import delete_message, add_delete_button


async def diary_header(update, context):
    try:
        logger.info("Diary command triggered")
        input_vars = await get_input_variables(update, context)
        output = await run_chain("diary_header", input_vars)

        parsed_output = DiaryHeader.model_validate(output)
        dates_header = parsed_output.header

        header = f"{header_top}{dates_header}\n\n---"

        if shared_state["transparant_mode"]:
            debug_message = await update.message.reply_text(parsed_output)
            await add_delete_button(update, context, debug_message.message_id)
            asyncio.create_task(delete_message(update, context, debug_message.message_id, 120))

        await update.message.reply_text(header)

    except Exception as e:
        await update.message.reply_text(f"Error in diary_header():\n {e}")
        logger.error(f"\n\n🚨 Error in diary_header(): {e}\n\n")


header_top ="""
---
Heading: 
Wellbeing: 
Work: 
Comfort: 
Home (Leipzig): true
Walk >30mins.: 
Whereabouts:
Sports: 
Drugs: 
E: 
Purchases: 
Meditate: 
Interessant: 
Finished:
---
"""
