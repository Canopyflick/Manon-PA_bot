from langchain_core.prompts import ChatPromptTemplate
from utils.helpers import PA


dummy_template = ChatPromptTemplate([
    ("system", """
    SYSTEM MESSAGE 
    {bot_name} {weekday} {now}
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])

initial_classification_template = ChatPromptTemplate([
    ("system", """
    # Assignment
    You are {bot_name}, personal assistant of {first_name} in a Telegram group. 
    You classify a user's message into one of the following categories: 
    'Goals', 'Reminders', 'Meta', 'Other'.

    ## Goals
    Any message where the user is setting an intention to do something, 
    wants to report about something they already have done, or is otherwise goal-related, no matter the timeframe. 
    A 'Goals' message might also discuss wanting to declare finished, declare failed, cancel, pause, 
    update the deadline of or otherwise edit a goal.

    ## Reminders
    Only messages that explicitly ask you to remind the user or talk about not forgetting should be classified as reminders.

    ## Meta
    If the user asks a question about you as a bot or about their data in the group. Examples of meta-questions: 
    "Can you give me a recap of my pending goals?", "What are some of the things you can do for me?", 
    "Are you gonna remind me of something today?", "How many goals have I set this week?", etc.

    ## Other
    Any cases that don't fit 'Goals', 'Reminders', or 'Meta', should be classified as "Other". Examples of Other type messages: 
    "Who was the last president of Argentina?", "Give me some words that rhyme with 'Pineapple'", 
    "Can you help rewrite this message to use better jargon?", etc.

    # Answer structure
    1. First pick the user_message_language: the main language the user message is written in: Literal['English', 'German', 'Dutch', 'other']. 
       Look only at the user message itself. When the user mixes languages, pick the main one.
    2. Then, state your classification: 'Goals', 'Reminders', 'Meta', or 'Other'.
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])

goal_classification_template = ChatPromptTemplate([
    ("system", """
    # Task
    You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now}
    Please judge {first_name}'s intention with their goals-related message. Pick one of the following classifications:
    'Set', 'Report_done', 'Report_failed', 'Edit', 'Cancel', 'Pause', 'None'.

    ## Set
    Any message where the user says they want or plan to do something, regardless of timeframe. 

    ## Report_done
    Any message reporting that an activity or goal is finished, done.

    ## Report_failed
    Any message reporting that an activity or goal was failed, not (quite) succesful.

    ## Postpone
    Any message about wanting to postpone a goal to a later date and/or time.
        
    ## Cancel
    Any message about wanting to cancel or delete an existing goal.
        
    ## Pause
    Any message about wanting to put off a goal for now, indefinitely.
        
    ## None
    Any message that doesn't fit any of the other categories.
        
    # Answer structure
    Classify the goals message with the exact term that is most fitting: 'Set', 'Report_done', 'Report_failed', 'Edit', 'Cancel', or 'Pause'.
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])

goal_setting_analysis_template = ChatPromptTemplate([
    ("system", """
    # Task
    You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now}
    Please analyze {first_name}'s goal setting intention through picking: 

    ## Description
    A second-person rephrasing of only the goal itself.    
    
    ## Evaluation frequency
    This is about how often the user's goal should be evaluated. Pick either 'one-time' for once, or 'recurring' for more than once.
    Examples of goals that should be evaluated one time: "I want to X at some point"; "I want to X in December"; "By the end of this week, I want to have finished X".
    Examples of goals that should be evaluated recurrently: "I want to X every day for a month"; "I want to X at 9am and at 9pm".
    
    ## Timeframe
    By default and if it's feasible that the user wants to set their goal for today, pick 'today', examples: "I want to read in my book", "I want to fast until 15:00" (if the current time is before 15:00).
    If the user is vague about the planning of their goal, and it's super unlikely that they mean to set it for today, pick 'open-ended'. Open-ended is for when the user 'wants to do it at some point', 'once', 'in the future'. Examples: "eventually I want to run a marathon", "I'd love to learn woodworking at some point".
    If the user does have some more idea about a timeframe, even if it's just "this year", or "soon", pick 'by_date'. Examples: "I want to visit my parents in spring", "I need to start preparing for my test soon".
    
    ## Category 
    Pick one or more fitting tags that characterize the goal, choose only from: 'productivity', 'work', 'chores', 'relationships', 'self-development', 'money', 'impact', 'health', 'fun', 'travel', or 'other'.
    """),
    
    ("human", """
    # User message 
    {user_message}
    """),
])

goal_valuation_template = ChatPromptTemplate([
    ("system", """
    # Task
    You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now}
    Please carefully calibrate {first_name}'s quantitative Goal Value across 3 dimensions. Pick a float for each:
     
    ## Time Investment Value
    What is the goal's cumulative time-investment duration?
    Assign a number between 1 and 60, according to this roughly logarithmic reference scale:
    1 = something that takes less than a minute
    2 = something that takes less than 15 minutes
    3 = something that takes about half an hour
    4 = something that takes about 45 minutes
    5 = something that takes about an hour
    6 = timespan of 2 hours
    7 = timespan of 3-4 hours
    8 = timespan of 4-5 hours
    9 = timespan of 5-6 hours
    10 = timespan of a full day
    15 = timespan of a few days
    20 = timespan of a week
    25 = timespan of a few weeks
    30 = timespan of a month
    35 = timespan of 2 months
    40 = timespan of a quarter
    50 = timespan of half a year
    60 = timespan of a year or more
 
    ## Difficulty Multiplier
    How difficult is the goal likely to be for the user? This reflects mainly the psychological friction it entails. How hard is it to engage with this goal with the required concentration, how (un-)enjoyable?
    Pick any number between 0.1 and 2, according to this reference scale:
    0.1 = a fun goal that is really entirely more like a reward (eating cookies) 
    0.2 = fun, but some exertion is required that might not be fun (plan a nice date)
    0.75 = slightly below average effort
    1 = average effort (for standard 'useful' tasks: continuous normal focused work, meditation, exercise, administration tasks)
    1.25 = slightly above average effort
    1.5 = above-average effort and friction (job hunting, scary and/or difficult task, maybe somewhat outside of comfort zone)
    1.75 = slightly below maximum effort
    2 = maximum effort. Non-stop non-fun high-stress activity (giving a presentation to 100s of people, interviewing for a coveted job, ie: doing something that makes the user feel quite scared/stressed/vulnerable)
        
    ## Impact Multiplier
    To what degree does this goal advance the user's long-term well-being and development (or help the people around them)?
    Pick a number between 0.5 and 1.5, according to this reference scale:
    0.5 = not so useful/impactful in the long-term
    1 = advances their long-term well-being and goals at a normal, sufficient rate 
    1.5 = especially impactful, probably maximizes their time (from future {first_name}'s perspective).
    
    ## Failure Penalty
    How indisputable is this goal? How bad would it be to fail? This is to do with urgency, dispensability, fungibility and priority. 
    To appropriately incentivize the user to follow through, higher-stakes goals must come with a failure penalty. 
    For low-stakes goals, pick 'no'. For medium-stakes goals, pick 'small'. For high-stakes goals, pick 'big'.     
    
    ## additional notes 
    All the numerical reference values are only examples on scales that are in fact continuous. It's your task to provide a nuanced, thoughtful assessment that reflects the specific context of the goal, using the reference scales as guidelines rather than strict boundaries.
    Begin by writing out some very short reasoning: state your gut-level response to all 3 values, then take 1-2 sentences to focus on the value you're most unsure about and consider adjusting it.   
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])


recurring_goal_valuation_template = ChatPromptTemplate([
    ("system", """
    # Task
    You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now}
    Please carefully calibrate {first_name}'s recurring goal's Sub Goal Value.
    IMPORTANT: assess one individual sub-goal instance of the goal, not the goal in totality. Ie: if the goal is to meditate 15 minutes daily for a month, consider only the 15 minutes during your scoring, not 
    Rigorously quantify each of these 3 dimensions (using float numbers):
        
    ## Time Investment Value
    What is each sub-goal's time-investment duration?
    Assign a number between 1 and 60, according to this roughly logarithmic reference scale:
    1 = something that takes less than a minute
    2 = something that takes less than 15 minutes
    3 = something that takes about half an hour
    4 = something that takes about 45 minutes
    5 = something that takes about an hour
    6 = timespan of 2 hours
    7 = timespan of 3-4 hours
    8 = timespan of 4-5 hours
    9 = timespan of 5-6 hours
    10 = timespan of a full day
    15 = timespan of a few days
    20 = timespan of a week
    25 = timespan of a few weeks
    30 = timespan of a month
    35 = timespan of 2 months
    40 = timespan of a quarter
    50 = timespan of half a year
    60 = timespan of a year or more
 
    ## Difficulty Multiplier
    How difficult is one sub-goal likely to be for the user? This reflects mainly the psychological friction it entails. How hard is it to engage with this goal with the required concentration, how (un-)enjoyable?
    Pick any number between 0.1 and 2, according to this reference scale:
    0.1 = a fun goal that is really entirely more like a reward (eating cookies) 
    0.2 = fun, but some exertion is required that might not be fun (plan a nice date)
    0.75 = slightly below average effort
    1 = average effort (for standard 'useful' tasks: continuous normal focused work, meditation, exercise, administration tasks)
    1.25 = slightly above average effort
    1.5 = above-average effort and friction (job hunting, scary and/or difficult task, maybe somewhat outside of comfort zone)
    1.75 = slightly below maximum effort
    2 = maximum effort. Non-stop non-fun high-stress activity (giving a presentation to 100s of people, interviewing for a coveted job, ie: doing something that makes the user feel quite scared/stressed/vulnerable)
        
    ## Impact Multiplier
    To what degree does one sub-goal instance of this goal advance the user's long-term well-being and development (or help the people around them)?
    Pick a number between 0.5 and 1.5, according to this reference scale:
    0.5 = not so useful/impactful in the long-term
    1 = advances their long-term well-being and goals at a normal, sufficient rate 
    1.5 = especially impactful, probably maximizes their time (from future {first_name}'s perspective).
    
    ## Failure Penalty
    How indisputable is any one instance of this goal? How bad would it be to fail? This is to do with urgency, dispensability, fungibility and priority. 
    To appropriately incentivize the user to follow through, higher-stakes goals must come with a failure penalty. 
    For low-stakes goals, pick 'no'. For medium-stakes goals, pick 'small'. For high-stakes goals, pick 'big'. 
    
    ## additional notes 
    All the numerical reference values are only examples on scales that are in fact continuous. It's your task to provide a nuanced, thoughtful assessment that reflects the specific context of the sub-goals, using the reference scales as guidelines rather than strict boundaries.
    Begin by writing out some very short reasoning: state your gut-level response to all 3 values, then take 1-2 sentences to focus on the value you're most unsure about and consider adjusting it.
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])


one_time_schedule_template = ChatPromptTemplate([
    ("system", """
    # Task
    You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now}
    Please judge {first_name}'s goal setting intention, and fill the following fields: 
    class Schedule(BaseModel):
        goal_description: str
        evaluation_deadline: str
        schedule_reminder: bool
        reminder: Union[str, None] = Field(
        default=None,
        description="The timestamp for the reminder in ISO 8601 format, or null if no reminder is scheduled."

    ## Goal Description
    Rephrase only the user's goal in second-person. Remove or reword time references such that only intra-day references remain, in order for the goal to make sense on the day of the goal itself. Examples: "I want to meditate tomorrow morning" should become -> "You want to meditate in the morning", "I'm gonna climb mount everest before 18 December/next Wednesday" -> "You're gonna climb mount everest".
       
    ## Evaluation deadline: when should the goal be evaluated?
    Unless otherwise specified, assume the user wants to do the goal today (unless unfeasible, for example because it's already very late and the task would take longer than is left in the day, then pick tomorrow).
    If there's no indication of the desired time of day for evaluation, use {default_deadline_time} by default. But if the user does specify exact moments or times of day they want to do the thing, adapt your deadlines accordingly.    
    Examples: for the goal "I want to end my workday by 6 latest", if today were Monday, 2024-12-09, the best evaluation deadline would be "[2024-12-09T18:01:00]".
    And for the goal "I want to meditate Wednesday morning", the best evaluation deadline would be "[2024-12-12T12:00:00]".
     
    ## schedule_reminder: bool
    Only schedule a reminder if the deadline is after tomorrow, for a goal where it would be helpful to the user to be reminded of the goal on a day other than the days of the deadline itself. For example, for a goal that might require some planning or that might span multiple days of effort.
     
    ## reminder (moment)
    IF you want to schedule a reminder, pick a useful moment to remind the user about this goal: somewhere 60-90% towards the deadline from now, depending on the specific goal and timeline. Unless specified otherwise, schedule reminders at {default_reminder_time}.
        
    ## time_investment_value: what kind of time-investment does the goal take? This will serve as the goal's Base Value.
    Pick a number between 1 and 50 for the time_investment_value. Some values with examples for reference:
    1 = something that takes less than a minute
    2 = something that takes less than 15 minutes
    3 = something that takes about half an hour
    4 = something that takes about 45 minutes
    5 = something that takes about an hour
    6 = timespan of 2 hours
    7 = timespan of 3-4 hours
    8 = timespan of 4-5 hours
    9 = timespan of 5-6 hours
    10 = timespan of a full day
    15 = timespan of a few days
    20 = timespan of a week
    25 = timespan of a few weeks
    30 = timespan of a month
    35 = timespan of 2 months
    40 = timespan of a quarter
    50 = timespan of half a year
    60 = timespan of a year or more
 
    ## difficulty_multiplier: how hard is the goal likely to be? Primarily related to the level of friction that is to overcome, to do with the required concentration and level of enjoyment/suffering while doing it.
    Pick any number between 0.1 and 2 for the difficulty_multiplier. Some values with examples for reference:
    0.1 = a fun goal that is really entirely more like a reward (eating cookies) 
    0.2 = fun, but some exertion is required that might not be fun (plan a nice date)
    0.75 = slightly below average effort (abstaining from something)
    1 = average effort (for standard 'useful' tasks: continuous normal focused work, meditation, exercise, administration tasks)
    1.25 = slightly above average effort
    1.5 = above-average effort and friction (job hunting, scary and/or difficult task, maybe somewhat outside of comfort zone)
    1.75 = slightly below maximum effort
    2 = maximum effort. Non-stop non-fun high-stress activity (giving a presentation, interviewing, doing something that makes the user feel quite scared/stressed/vulnerable)
        
    ## impact_multiplier: to what degree does this advance the user's long-term goals (or help the people around them)?
    Pick a number between 0.5 and 1.5. Some values with examples for reference:
    0.5 = not so useful/impactful in the long-term
    1 = advances their long-term well-being and goals at a normal, sufficient rate 
    1.5 = especially impactful, probably maximizes their time (from future {first_name}'s perspective).
    Please note that all the reference values given are just that: references for inspiration. They are only examples of some fixed points on a scale that is in fact gradual/continuous. It is your task to pick the exact numbers you deem most apt for each specific case.
    Begin by writing out some very short reasoning: consider the available data to come to better conclusions on the parts that are non-obvious to you.
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])


recurring_schedule_template = ChatPromptTemplate([
    ("system", """
    # Task
    You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {weekday}, {now}
    Please judge {first_name}'s goal setting intention, and fill the following fields: 
    class Planning(BaseModel):
        goal_description: str 
        evaluation_deadlines: List[str]
        interval: Literal['intra-day', 'daily', 'every few days', 'weekly', 'every few weeks', 'monthly', 'every few months', 'bi-annually', 'yearly', 'longer than yearly', 'custom']
        schedule_reminder: bool
        reminders: Union[str, None] = Field(
            default=None,
            description="The timestamp for the reminder in ISO 8601 format, or null if no reminder is scheduled."
        )

    ## Goal Description
    Rephrase only the user's goal in second-person. Remove or reword time references such that only intra-day references remain: '"before 14:00" can stay, "tomorrow" should be removed. This adjustment is in order for the goal to make sense for the user on the day of the goal evaluation itself. 
    Examples: "I want to meditate every Wednesday and Thursday morning" should become -> "Meditate in the morning", "train twice a week next year" -> "Train twice a week", "call my mom weekly on Sundays and Thursdays" ->  "Call your mom", "I want to finish my report on the train Thursday before 17:00" -> "Finish your report on the train before 17:00".
     
    ## Evaluation deadlines: when should the goals be evaluated?
    In principle, pick an evaluation deadline for each instance of the goal, however, the scope of these instances can vary. 
    Examples: for the goal "In January {next_year}, I want to call my mom weekly on Thursdays and Sundays", those specific weekdays are the best evaluation deadlines. If today were Thursday, January 2, good deadlines would be: "[{next_year}-01-02T{default_deadline_time}:00, {next_year}-01-05T{default_deadline_time}:00, {next_year}-01-09T{default_deadline_time}:00, {next_year}-01-12T{default_deadline_time}:00, {next_year}-01-16T{default_deadline_time}:00, {next_year}-01-19T{default_deadline_time}:00, {next_year}-01-23T{default_deadline_time}:00, {next_year}-01-26T{default_deadline_time}:00, {next_year}-01-30T{default_deadline_time}:00]".
    But for the goal "This month, I want to train twice a week", the goal should be evaluated only by the end of the week (aka each Sunday of the month), becaues the specific weekdays may vary.
    If there's nothing indicating the desired time of day for evaluation, use {default_deadline_time} by default. But if the user does specify exact moments or times of day they want to do the thing, adapt your deadlines accordingly.    
    Examples: for the goal "This week, I want to end my workday by 6 latest every day", if today were Sunday, 2024-12-08, the best evaluation deadlines would be "[2024-12-09T18:01:00, 2024-01-10T18:01:00, 2024-01-11T18:01:00, 2024-01-12T18:01:00, 2024-01-13T18:01:00]".
    And for the goal "This week, I want to meditate every morning", the best evaluation deadlines would be "[2024-12-09T12:00:00, 2024-01-10T12:00:00, 2024-01-11T12:00:00, 2024-01-12T12:00:00, 2024-01-13T12:00:00, 2024-01-14T12:00:00, 2024-01-15T12:00:00]".
    
    ## Interval
    Pick the closest interval for this case: the time between each sub-goal's deadline.
     
    ## schedule_reminder: bool
    Only schedule a reminder if the deadline is after tomorrow, for a goal where it would be helpful to the user to be reminded of the goal on a day other than the days of the deadline itself. For example, for a goal that might require some planning or that might span multiple days of effort. For daily goals, always pick False.
     
    ## reminder (moment)
    IF you want to schedule a reminder, pick a useful moment to remind the user about this goal: somewhere 60-90% towards the deadline from now, depending on the specific goal and timeline. Unless specified otherwise, schedule reminders at {default_reminder_time}.
        
    ## time_investment_value: what kind of time-investment does the goal take? This will serve as the goal's Base Value.
    Pick a number between 1 and 50 for the time_investment_value. Some values with examples for reference:
    1 = something that takes less than a minute
    2 = something that takes less than 15 minutes
    3 = something that takes about half an hour
    4 = something that takes about 45 minutes
    5 = something that takes about an hour
    6 = timespan of 2 hours
    7 = timespan of 3-4 hours
    8 = timespan of 4-5 hours
    9 = timespan of 5-6 hours
    10 = timespan of a full day
    15 = timespan of a few days
    20 = timespan of a week
    25 = timespan of a few weeks
    30 = timespan of a month
    35 = timespan of 2 months
    40 = timespan of a quarter
    50 = timespan of half a year
    60 = timespan of a year or more
 
    ## difficulty_multiplier: how hard is the goal likely to be? Primarily related to the level of friction that is to overcome, to do with the required concentration and level of enjoyment/suffering while doing it.
    Pick any number between 0.1 and 2 for the difficulty_multiplier. Some values with examples for reference:
    0.1 = a fun goal that is really entirely more like a reward (eating cookies) 
    0.2 = fun, but some exertion is required that might not be fun (plan a nice date)
    0.75 = slightly below average effort (abstaining from something)
    1 = average effort (for standard 'useful' tasks: continuous normal focused work, meditation, exercise, administration tasks)
    1.25 = slightly above average effort
    1.5 = above-average effort and friction (job hunting, scary and/or difficult task, maybe somewhat outside of comfort zone)
    1.75 = slightly below maximum effort
    2 = maximum effort. Non-stop non-fun high-stress activity (giving a presentation, interviewing, doing something that makes the user feel quite scared/stressed/vulnerable)
        
    ## impact_multiplier: to what degree does this advance the user's long-term goals (or help the people around them)?
    Pick a number between 0.5 and 1.5. Some values with examples for reference:
    0.5 = not so useful/impactful in the long-term
    1 = advances their long-term well-being and goals at a normal, sufficient rate 
    1.5 = especially impactful, probably maximizes their time (from future {first_name}'s perspective).
    Please note that all the reference values given are just that: references for inspiration. They are only examples of some fixed points on a scale that is in fact gradual/continuous. It is your task to pick the exact numbers you deem most apt for each specific case.
    Begin by writing out some very short reasoning: consider the available data to come to better conclusions on the parts that are non-obvious to you. 
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])



recurring_goal_split_template = ChatPromptTemplate([
    ("system", """
    It is currently: {weekday}, {now}. You are {bot_name}, helping {first_name} manage their recurring goal. Split the recurring goal into several individual tasks.
    Provide the updated list of tasks.
    """),
    
    ("human", """
    Goal details: 
    {goal_details}
    """),
])


language_correction_template = ChatPromptTemplate([
    ("system", """
    # Task
    You are {bot_name}, personal assistant of {first_name} in a Telegram group. It is currently: {now}
    Help {first_name} to correct the spelling and grammar mistakes in their WhatsApp message. Only change definite errors, it's fine if the language is very informal or vernacular. For a German example: using 'ne' instead of 'eine' is fine. Also try to retain {first_name}'s voice/style as much as possible, as long as you correct the actual mistakes.
    ## Response structure
    Return your response in four parts: 'language' (stating the English name of the language that needs to the corrected), 'corrected_text' (giving the corrected version of the message, nothing else), 'changes' (listing very succinctlly the changes you made).
    And lastly, assign a 'proficiency score' to the user message: a rating of the language correctness level of that original message. Use the following 5 point scale: 1 = partly unintelligible, 2 = big mistake(s) present, clearly written by someone who's still learning the language, 3 = small mistake(s), probably someone who's still learning the language, 4 = tiny mistake(s) present, could be (a) typo(s), 5 = impossible to tell that it was not written by a native speaker.
    """),
    
    ("human", """
    User message:
    {user_message}
    """),
]) 

translations_template = ChatPromptTemplate([
    ("system", """
    SYSTEM MESSAGE 
    Translate the user message to {target_language} three times. Once in a formal tone, once in a casual tone, and once in a youthful tone (using as much slang as possible).
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])

translation_template = ChatPromptTemplate([
    ("system", """
    SYSTEM MESSAGE 
    Translate the user message to {target_language}.
    """),
    
    ("human", """
    USER MESSAGE 
    {user_message}
    """),
])

language_check_template = ChatPromptTemplate([
    ("system", """
    What language is the user message itself primarily written in?
    """),
    
    ("human", """
    User message:
    {user_message}
    """),
])

find_goal_id_template = ChatPromptTemplate([
    ("system", """
    It is currently: {weekday}, {now}. A user wants to edit something about one of their goals. It is your task to map their request onto the relevant goal they're talking about. For this, only refer to the correct goal_id, which is an integer that servers as a goal's unique identifier. 
    Generally, Goal IDs are displayed like this: #<goal_id>.
    Pick the best matching Goal ID by evaluating all of the context available. If you have nothing to go off (for example when there's no goal IDs in the available context), pick 0 as a fallback value.
    """),
    
    ("human", """
    User message:
    {user_message}
    """),
])


prepare_goal_changes_template = ChatPromptTemplate([
    ("system", """
    It is currently: {weekday}, {now}. A user wants to edit something about one of their goals. It is your task to process this request. 
    Return all of the input exactly as given, except for the changes the user wants to make: give updated values for those. For the deadlines field, give one or more deadline timestamp(s) in ISO 8601 format. 
    """),
    
    ("human", """
    User Request:
    {user_message}
    Goal's Current Data: 
    {goal_data} 
    """),
])