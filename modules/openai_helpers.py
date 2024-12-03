from utils.helpers import get_first_name, client
import logging, os
from openai import OpenAI



async def send_openai_request(messages, model="gpt-4o-mini", temperature=None, response_format=None):
    try:
        request_params = {
            "model": model,
            "messages": messages
            }
        # only add temperature if it's provided (not None)
        if temperature is not None:
            request_params["temperature"] = temperature
        if response_format is not None:
            request_params['response_format'] = response_format
        if response_format:
            response = client.beta.chat.completions.parse(**request_params)
            return response.choices[0].message.parsed
        else:
            response = client.chat.completions.create(**request_params)
            return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error calling OpenAI: {e}")
        return None
    


async def prepare_openai_messages(update, user_message, message_type, response=None):
    # Define system messages based on the message_type
    first_name = update.effective_user.first_name
    bot_name = update.get_bot().username
    if message_type == 'classification_initial':
        system_message = system_message = f"""
        # Assignment
        You are {bot_name}, personal assistant of {first_name} in a Telegram group. 
        You classify a user's message into one of the following categories: 
        'Goals', 'Reminders', 'Meta', 'Other'.

        ## Goals
        Any message that primarily indicates that the user wants to set a new intention to do something or wants to report about something they have done, no matter the timeframe.

        ## Reminders
        Any message that is a request to remind the user of something.

        ## Meta
        If the user asks a question about you as a bot or about their data in the group. Examples of meta-questions: 
        "Can you give me a recap of my pending goals?", "What are some of the things you can do for me?", "Are you gonna remind me of something today?", "How many goals have I set this week?", etc..

        ## Other
        Any cases that don't fit 'Goals', 'Reminders', or 'Meta', should be classified as "Other". Examples of Other type messages: 
        "Who was the last president of Argentinia?", "Give me some words that rhyme with 'Pineapple'", "Can you help rewrite this message to use better jargon?", etc. 

        # Response
        Respond first with a boolean which states whether the language the user message is written in is primarily English. Then, do some reasoning about the available data, to ponder the correct classification. Then, state your classification: 'Goals', 'Reminders', 'Meta', or 'Other'
        """
    elif message_type == 'classification_timeframe':
        system_message = system_message = f"""
        # Task
        You are {bot_name}, personal assistant of {first_name} in a telegram group. 
        Please judge {first_name}'s goal setting intention on timeframe: for which duration are they setting this goal? You do this by classifying the goal as one of the following timeframe types:
        'day', 'week', 'by_date', 'open-ended'.

        ## day
        This is the default timeframe for a goal, and it means that the user intents to finish their goal this very same day. Either by the day's end, or at a specific time today. If the user doesn't specify anything, and the goal is the kind of goal they might feasibly finish in a day, then pick this.

        ## week 
        This is for a goal the user sets for the current workweek + weekend.

        ## by_date
        For goals that should be finished by a specific custom date (that is not today). Use this when the user says: 'tomorrow', 'Saturday', 'End of July', 'Wednesday next week', '12 August', etc.

        ## open-ended
        For goals without a specified deadline. The user sets out to do this 'at some point', 'once in their life', 'eventually' etc. If the user says they want to do something 'soon', this is not open-ended. In cases like that, pick by_date. 
        """
    elif message_type == 'classification_goal_type':
        system_message = system_message = f"""
        # Task
        You are {bot_name}, personal assistant of {first_name} in a telegram group. 
        Please judge {first_name}'s goal setting intention on timeframe: for which duration are they setting this goal? You do this by classifying the goal as one of the following timeframe types:
        'day', 'week', 'by_date', 'open-ended'.

        ## day
        This is the default timeframe for a goal, and it means that the user intents to finish their goal this very same day. Either by the day's end, or at a specific time today. If the user doesn't specify anything, and the goal is the kind of goal they might feasibly finish in a day, then pick this.

        ## week 
        This is for a goal the user sets for the current workweek + weekend.

        ## by_date
        For goals that should be finished by a specific custom date (that is not today). Use this when the user says: 'tomorrow', 'Saturday', 'End of July', 'Wednesday next week', '12 August', etc.

        ## open-ended
        For goals without a specified deadline. The user sets out to do this 'at some point', 'once in their life', 'eventually' etc. If the user says they want to do something 'soon', this is not open-ended. In cases like that, pick by_date. 
        """
    elif message_type == 'other':
        logging.info("system prompt: other message")
        system_message = (
            "Jij bent @TakenTovenaar_bot, de enige bot in een accountability-Telegramgroep van vrienden. "
            "Gedraag je cheeky, mysterieus en wijs. Streef bovenal naar waarheid, als de gebruiker een feitelijke vraag heeft. "
            "Als de gebruiker een metavraag of -verzoek heeft over bijvoorbeeld een doel stellen in de appgroep, "
            "antwoord dan alleen dat ze het command /help kunnen gebruiken. "
            "Er zijn meer commando's, maar die ken jij allemaal niet. "
            "Je hebt nu alleen toegang tot dit bericht, niet tot volgende of vorige berichtjes. "
            "Een back-and-forth met de gebruike is dus niet mogelijk."
        )
    elif message_type == 'sleepy':
        logging.info("system prompt: sleepy message")
        system_message = ("Geef antwoord alsof je slaapdronken en verward bent, een beetje van het padje af misschien. Maximaal 3 zinnen.")

    elif message_type == 'meta':
        logging.info("system prompt: meta message")
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        group_name = update.effective_chat.title
        meta_data = await collect_meta_data(user_id, chat_id)
        logging.info(f"\n\n⏺️⏺️⏺️Dit is de metadata in de prompt-variabele: {meta_data}\n")
        system_message = f"""
        ...
        
        # Gebruikersgegevens

        Hier volgen alle gegevens die zojuist met database queries zijn opgehaald over de stand van zaken in deze appgroep, met name voor {first_name}:
    
        {meta_data}  
        
        ...

        # Je antwoord nu
        Houd het kort en to-the-point. Alleen de vraag of vragen van de gebruiker compact addresseren, zodat de chat opgeruimd blijft. Groet de gebruiker dus niet met een inleidend zinnetje, maar kom meteen ter zake. Verwerk altijd een 👩‍🦱-emoji in je antwoord.
        """
    messages = [{"role": "system", "content": system_message}]        
        
    user_content = f"# Het berichtje van de gebruiker\n{first_name} zegt: {user_message}"
    
    if response:
        user_content += f" (Reactie op: {response})"
    logging.info(f"user prompt: {user_content}")
    messages.append({"role": "user", "content": user_content})
    return messages


async def send_openai_request(messages, model="gpt-4o-mini", temperature=None, response_format=None):
    try:
        request_params = {
            "model": model,
            "messages": messages
            }
        # only add temperature if it's provided (not None)
        if temperature is not None:
            request_params["temperature"] = temperature
        if response_format is not None:
            request_params['response_format'] = response_format
        if response_format:
            response = client.beta.chat.completions.parse(**request_params)
            return response.choices[0].message.parsed
        else:
            response = client.chat.completions.create(**request_params)
            return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Error calling OpenAI: {e}")
        return None


