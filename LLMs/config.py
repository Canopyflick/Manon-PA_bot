from utils.helpers import EC_OPENAI_API_KEY
from utils.session_avatar import PA
from LLMs.classes import (
    InitialClassification,
    GoalClassification,
    SetGoalAnalysis,
    GoalSetData,
    LanguageCorrection,
    LanguageCheck,
    Translation,
    Translations,
    DummyClass,
    Schedule,
    Planning,
    GoalAssessment,
    GoalInstanceAssessment,
    LanguageCheck,
    GoalID,
    UpdatedGoalData,
    DiaryHeader,
    Reminder,
    Response
)
from LLMs.prompts import (
    dummy_template,
    initial_classification_template,
    goal_classification_template,
    goal_valuation_template,
    recurring_goal_valuation_template,
    recurring_goal_split_template,
    translation_template,
    translations_template,
    goal_setting_analysis_template,
    language_correction_template,
    translation_template,
    recurring_schedule_template,
    one_time_schedule_template,
    language_check_template,
    find_goal_id_template,
    prepare_goal_changes_template,
    diary_header_template,
    reminder_setting_template,
    other_template
)

from langchain_openai import ChatOpenAI   


# Flag for sending debug logs in chat
shared_state = {"transparant_mode": False}


# Initialize LLMs and temperatures
LOW = 0.2
MID = 0.7
HIGH = 1.2

llms = {
    "gpt4o": ChatOpenAI(model_name="gpt-4o", temperature=LOW),
    "mini": ChatOpenAI(model_name="gpt-4o-mini", temperature=LOW),
    "gpt4o_high_temp": ChatOpenAI(model_name="gpt-4o", temperature=HIGH),
    "mini_high_temp": ChatOpenAI(model_name="gpt-4o-mini", temperature=HIGH),
    "o1": ChatOpenAI(model_name="o1"),
}

# Centralized Chain Configuration
chain_configs = {
    "dummy_chain_name": {
        "template": dummy_template,
        "class": DummyClass,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "initial_classification": {
        "template": initial_classification_template,
        "class": InitialClassification,
        "llm": llms["mini"], 
    },
    "goal_classification": {
        "template": goal_classification_template,
        "class": GoalClassification,
        "llm": llms["mini"],
    },
    "goal_classification_smart": {
        "template": goal_classification_template,
        "class": GoalClassification,
        "llm": llms["gpt4o"],
    },
    "goal_setting_analysis": {
        "template": goal_setting_analysis_template,
        "class": SetGoalAnalysis,
        "llm": llms["mini"],
    },
    "goal_setting_analysis_smart": {
        "template": goal_setting_analysis_template,
        "class": SetGoalAnalysis,
        "llm": llms["gpt4o"],
    },
    "goal_valuation": {
        "template": goal_valuation_template,
        "class": GoalAssessment,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "goal_valuation_smart": {
        "template": goal_valuation_template,
        "class": GoalAssessment,
        "llm": llms["gpt4o"], 
    },
    "recurring_goal_valuation": {
        "template": recurring_goal_valuation_template,
        "class": GoalInstanceAssessment,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "recurring_goal_valuation_smart": {
        "template": recurring_goal_valuation_template,
        "class": GoalInstanceAssessment,
        "llm": llms["gpt4o"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
     "schedule_goal": {
        "template": one_time_schedule_template,
        "class": Schedule,
        "llm": llms["mini"],
    },
     "schedule_goal_smart": {
        "template": one_time_schedule_template,
        "class": Schedule,
        "llm": llms["gpt4o"],
    },
     "schedule_goals": {
        "template": recurring_schedule_template,
        "class": Planning,
        "llm": llms["mini"],
    },
     "schedule_goals_smart": {
        "template": recurring_schedule_template,
        "class": Planning,
        "llm": llms["gpt4o"],
    },
    "language_correction": {
        "template": language_correction_template,
        "class": LanguageCorrection,
        "llm": llms["gpt4o"],
    },
    "translations": {
        "template": translations_template,
        "class": Translations,
        "llm": llms["gpt4o"],
    },
    "translation": {
        "template": translation_template,
        "class": Translation,
        "llm": llms["gpt4o"],
    },
    "language_check": {
        "template": language_check_template,
        "class": LanguageCheck,
        "llm": llms["mini"],
    },
    "find_goal_id": {
        "template": find_goal_id_template,
        "class": GoalID,
        "llm": llms["mini"],
    },
    "prepare_goal_changes": {
        "template": prepare_goal_changes_template,
        "class": UpdatedGoalData,
        "llm": llms["gpt4o"],
    },
    "diary_header": {
        "template": diary_header_template,
        "class": DiaryHeader,
        "llm": llms["gpt4o"],
    },
    "reminder_setting": {
        "template": reminder_setting_template,
        "class": Reminder,
        "llm": llms["mini"],
    },
    "other": {
        "template": other_template,
        "class": Response,
        "llm": llms["gpt4o_high_temp"],
    },
    "other_plus": {
        "template": other_template,
        "class": Response,
        "llm": llms["o1"],
    }
}


# Function to create chains
def create_chain(config):
    chain = {
        "template": config["template"],
        "chain": config["llm"].with_structured_output(config["class"]),
    }
    return chain

# Generate Chains Dynamically
chains = {name: create_chain(config) for name, config in chain_configs.items()}