# LLMs/prompts_messages.py

initial_classification_template_text = """
# Assignment
You are {{bot_name}}, personal assistant of {{first_name}} in a Telegram group.
You classify a user's message into one of the following categories:
'Goals', 'Reminders', 'Other'.

## Goals
Any message where the user is setting an intention to do something,
wants to report about something they already have done, or is otherwise goal-related, no matter the timeframe.
A 'Goals' message might also discuss wanting to declare finished, declare failed, cancel, pause,
update the deadline of or otherwise edit a goal.

## Reminders
Only messages that solely explicitly ask you to remind the user or talk about not forgetting should be classified as reminders. If a message could be a goal but also discusses reminders, pick Goal.

## Other
Everything else: questions about the bot, questions about the user's data, general knowledge,
conversation, or anything that doesn't fit 'Goals' or 'Reminders'. Examples:
"Who was the last president of Argentina?", "Give me some words that rhyme with 'Pineapple'",
"Can you give me a recap of my pending goals?", "How many goals have I set this week?",
"What are some of the things you can do for me?", etc.

# Answer structure
1. First pick the user_message_language: the main language the user message is written in: Literal['English', 'German', 'Dutch', 'other'].
   Look only at the user message itself. When the user mixes languages, pick the main one. For example: 'I want to contact the Arbeitsamt' = English. 'Das finde ich awesome' = 'German'.
2. Then, state your classification: 'Goals', 'Reminders', or 'Other'.
"""

goal_classification_template_text = """ 
# Task
You are {{bot_name}}, personal assistant of {{first_name}} in a Telegram group. It is currently: {{weekday}}, {{now}}
Please judge {{first_name}}'s intention with their goals-related message. Pick one of the following classifications:
'Set', 'Report_done', 'Report_failed', 'Edit', 'Cancel', 'Pause', 'None'.

## Set
Any message where the user says they want or plan to do something, regardless of timeframe. 

## Report_done
Any message reporting that an activity or goal is finished, done.

## Report_failed
Any message reporting that an activity or goal was failed, not (quite) succesful.

## Edit
Any message about wanting to postpone a goal to a later date and/or time, add reminders to a goal, change phrasing or otherwise edit a goal.
    
## Cancel
Any message about wanting to cancel or delete an existing goal.
    
## Pause
Any message about wanting to put off a goal for now, indefinitely.
    
## None
Any message that doesn't fit any of the other categories.
    
# Answer structure
Classify the goals message with the exact term that is most fitting: 'Set', 'Report_done', 'Report_failed', 'Edit', 'Cancel', or 'Pause'.
"""

goal_setting_analysis_template_text = """

"""

goal_valuation_template_text = """

"""

recurring_goal_valuation_template_text = """

"""

one_time_schedule_template_text = """

"""

recurring_schedule_template_text = """

"""

recurring_goal_split_template_text = """

"""

language_correction_template_text = """

"""

translations_template_text = """

"""

translation_template_text = """

"""

language_check_template_text = """

"""

find_goal_id_template_text = """

"""

prepare_goal_changes_template_text = """

"""

diary_header_template_text = """

"""

reminder_setting_template_text = """

"""

other_template_text = """

"""
