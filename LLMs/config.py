# LLMs/config.py
from LLMs.structured_output_schemas import (
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
    Response,
    WassupSchema,
)
from LLMs.prompts_templates import (
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
    other_template,
    wassup_flow_template,
)

from langchain_openai import ChatOpenAI   


# Flag for sending debug logger in chat
shared_state = {"transparant_mode": False}


# Initialize LLMs and temperatures
LOW = 0.2
MID = 0.7
HIGH = 1.2

llms = {
    "gpt4o": ChatOpenAI(model_name="gpt-4o", temperature=LOW),
    "mini": ChatOpenAI(model_name="gpt-4.1-mini", temperature=LOW),
    "gpt4o_high_temp": ChatOpenAI(model_name="gpt-4o", temperature=HIGH),
    "mini_high_temp": ChatOpenAI(model_name="gpt-4.1-mini", temperature=HIGH),
    "o3-mini": ChatOpenAI(model_name="o3-mini"),
    "smartest": ChatOpenAI(model_name="o3"),
}

# Centralized Chain Configuration
chain_configs = {
    "dummy_chain_name": {
        "template": dummy_template,
        "schema": DummyClass,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "initial_classification": {
        "template": initial_classification_template,
        "schema": InitialClassification,
        "llm": llms["mini"], 
    },
    "goal_classification": {
        "template": goal_classification_template,
        "schema": GoalClassification,
        "llm": llms["mini"],
    },
    "goal_classification_smart": {
        "template": goal_classification_template,
        "schema": GoalClassification,
        "llm": llms["gpt4o"],
    },
    "goal_setting_analysis": {
        "template": goal_setting_analysis_template,
        "schema": SetGoalAnalysis,
        "llm": llms["mini"],
    },
    "goal_setting_analysis_smart": {
        "template": goal_setting_analysis_template,
        "schema": SetGoalAnalysis,
        "llm": llms["gpt4o"],
    },
    "goal_valuation": {
        "template": goal_valuation_template,
        "schema": GoalAssessment,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "goal_valuation_smart": {
        "template": goal_valuation_template,
        "schema": GoalAssessment,
        "llm": llms["gpt4o"], 
    },
    "recurring_goal_valuation": {
        "template": recurring_goal_valuation_template,
        "schema": GoalInstanceAssessment,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "recurring_goal_valuation_smart": {
        "template": recurring_goal_valuation_template,
        "schema": GoalInstanceAssessment,
        "llm": llms["gpt4o"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
     "schedule_goal": {
        "template": one_time_schedule_template,
        "schema": Schedule,
        "llm": llms["mini"],
    },
     "schedule_goal_smart": {
        "template": one_time_schedule_template,
        "schema": Schedule,
        "llm": llms["gpt4o"],
    },
     "schedule_goals": {
        "template": recurring_schedule_template,
        "schema": Planning,
        "llm": llms["mini"],
    },
     "schedule_goals_smart": {
        "template": recurring_schedule_template,
        "schema": Planning,
        "llm": llms["gpt4o"],
    },
    "language_correction": {
        "template": language_correction_template,
        "schema": LanguageCorrection,
        "llm": llms["gpt4o"],
    },
    "translations": {
        "template": translations_template,
        "schema": Translations,
        "llm": llms["gpt4o"],
    },
    "translation": {
        "template": translation_template,
        "schema": Translation,
        "llm": llms["gpt4o"],
    },
    "language_check": {
        "template": language_check_template,
        "schema": LanguageCheck,
        "llm": llms["mini"],
    },
    "find_goal_id": {
        "template": find_goal_id_template,
        "schema": GoalID,
        "llm": llms["mini"],
    },
    "prepare_goal_changes": {
        "template": prepare_goal_changes_template,
        "schema": UpdatedGoalData,
        "llm": llms["gpt4o"],
    },
    "diary_header": {
        "template": diary_header_template,
        "schema": DiaryHeader,
        "llm": llms["gpt4o"],
    },
    "reminder_setting": {
        "template": reminder_setting_template,
        "schema": Reminder,
        "llm": llms["mini"],
    },
    "other": {
        "template": other_template,
        "schema": Response,
        "llm": llms["gpt4o_high_temp"],
    },
    "other_plus": {
        "template": other_template,
        "schema": Response,
        "llm": llms["smartest"],
    },
    "wassup_flow_1": {
        "template": wassup_flow_template,   # you'll define a prompt
        "schema": WassupSchema,
        "llm": llms["mini"]  # or whichever LLM
    }

}


# Function to create chains
def create_chain(config):
    chain = {
        "template": config["template"],
    }

    if "schema" in config and config["schema"] is not None:
        chain["chain"] = config["llm"].with_structured_output(config["schema"])
    else:
        chain["chain"] = config["llm"].ainvoke

    return chain


# Generate Chains Dynamically
chains = {name: create_chain(config) for name, config in chain_configs.items()}