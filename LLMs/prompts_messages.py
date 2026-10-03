# LLMs/prompts_messages.py

initial_classification_template_text = """
# Assignment
You are {bot_name}, personal assistant of {first_name} in a Telegram group.
You classify a user's message into one of the following categories:
'Goals', 'Reminders', 'Other'.

## Goals
Any message where the user is setting an intention to do something,
wants to report about something they already have done, or is otherwise goal-related, no matter the timeframe.
A 'Goals' message might also discuss wanting to declare finished, declare failed, cancel, pause,
update the deadline of or otherwise edit a goal.
Wanting to cancel something in real life (a subscription, trial, membership, appointment, or order)
is still 'Goals': the user is setting an intention to do that cancellation.

## Reminders
Only messages that solely and explicitly ask you to remind the user or talk about not forgetting something time-sensitive should be classified as reminders.
Recurring intentions to do something on a schedule (e.g. "every month on the 15th check this website") are Goals, not Reminders — even without the word "goal".
If a message could be a goal but also discusses reminders, pick Goal.

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
You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now} (Europe/Berlin).
Split {first_name}'s goals-related message into one or more actions. Return at most 8 actions.

Each action has:
- classification: 'Set', 'Report_done', 'Report_failed', 'Edit', 'Cancel', or 'Pause'
- request: a self-contained restatement of only that action. Keep its time references ("tomorrow", "before Friday", clock times) and concrete details (names, URLs, amounts). A later step schedules from this text alone, so do not drop timing or specifics.

## Splitting
- Distinct tasks become separate actions. Copy any shared time context onto each one.
  "Tomorrow I want to call the dentist and buy groceries" -> two Set actions, and both requests mention tomorrow.
- The same task on a regular schedule stays one action. "Meditate every morning this month" -> one Set action.
- A message that is one intention stays one action.

## Set
The user wants or plans to do something, including cancelling, ending, or stopping something in real life that is not already a goal Manon tracks.
Real-life cancellations are Set, not Cancel. Examples:
- "Tomorrow I wanna cancel subscription X" -> Set. Request keeps "tomorrow" and the subscription name.
- "Cancel my trial for Y before Friday" -> Set.
- "I need to end my gym membership this week" -> Set.
- "Unsubscribe from the newsletter tomorrow" -> Set.
These are new intentions to perform a cancellation. They are not requests to delete a goal Manon is tracking.

## Report_done
The user reports that an existing tracked goal or activity is finished.

## Report_failed
The user reports that an existing tracked goal was failed or not successful.

## Edit
Postpone, reschedule, rephrase, or otherwise change an existing tracked goal. Adding a reminder to an existing goal is Edit.

## Cancel
Use Cancel only when the user wants to delete or drop a goal that Manon already tracks.
Examples: "cancel goal #123", "drop my gym goal", "I'm not doing the meditation series anymore", "delete that goal".
Never use Cancel for subscriptions, trials, memberships, appointments, orders, or other real-world cancellations the user still has to carry out. Those are Set.

## Pause
Put an existing tracked goal on hold indefinitely.

# Answer structure
Return the list of actions. If a part of the message does not clearly match Report_done, Report_failed, Edit, Cancel, or Pause, classify it as Set.
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
