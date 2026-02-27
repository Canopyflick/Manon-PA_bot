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
    CompactSchedule,
    CompactPlanning,
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
    compact_one_time_template,
    compact_recurring_template,
)

from langchain_openai import ChatOpenAI
from utils.environment_vars import ENV_VARS


# Flag for sending debug logger in chat
shared_state = {"transparant_mode": False}


# Initialize LLMs and temperatures
LOW = 0.2
MID = 0.7
HIGH = 1.2

llms = {
    "smart": ChatOpenAI(model_name="gpt-5.2", temperature=1),
    "mini": ChatOpenAI(model_name="gpt-5-mini", temperature=1),
    "gpt4o_high_temp": ChatOpenAI(model_name="gpt-5.2", temperature=1),
    "mini_high_temp": ChatOpenAI(model_name="gpt-5-mini", temperature=1),
    "o3-mini": ChatOpenAI(model_name="o3-mini", temperature=1),
    "smartest": ChatOpenAI(model_name="gpt-5.2-pro", temperature=1),
}

# OpenRouter: model-switching without code changes (configure preset at openrouter.ai)
if ENV_VARS.OPENROUTER_API_KEY:
    llms["openrouter_fast"] = ChatOpenAI(
        model_name="@preset/manon-fast",
        base_url="https://openrouter.ai/api/v1",
        api_key=ENV_VARS.OPENROUTER_API_KEY,
        temperature=1,
    )

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
        "llm": llms["smart"],
    },
    "goal_setting_analysis": {
        "template": goal_setting_analysis_template,
        "schema": SetGoalAnalysis,
        "llm": llms["mini"],
    },
    "goal_setting_analysis_smart": {
        "template": goal_setting_analysis_template,
        "schema": SetGoalAnalysis,
        "llm": llms["smart"],
    },
    "goal_valuation": {
        "template": goal_valuation_template,
        "schema": GoalAssessment,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "goal_valuation_smart": {
        "template": goal_valuation_template,
        "schema": GoalAssessment,
        "llm": llms["smart"],
    },
    "recurring_goal_valuation": {
        "template": recurring_goal_valuation_template,
        "schema": GoalInstanceAssessment,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "recurring_goal_valuation_smart": {
        "template": recurring_goal_valuation_template,
        "schema": GoalInstanceAssessment,
        "llm": llms["smart"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
     "schedule_goal": {
        "template": one_time_schedule_template,
        "schema": Schedule,
        "llm": llms["mini"],
    },
     "schedule_goal_smart": {
        "template": one_time_schedule_template,
        "schema": Schedule,
        "llm": llms["smart"],
    },
     "schedule_goals": {
        "template": recurring_schedule_template,
        "schema": Planning,
        "llm": llms["mini"],
    },
     "schedule_goals_smart": {
        "template": recurring_schedule_template,
        "schema": Planning,
        "llm": llms["smart"],
    },
    "language_correction": {
        "template": language_correction_template,
        "schema": LanguageCorrection,
        "llm": llms["smart"],
    },
    "translations": {
        "template": translations_template,
        "schema": Translations,
        "llm": llms["smart"],
    },
    "translation": {
        "template": translation_template,
        "schema": Translation,
        "llm": llms["smart"],
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
        "llm": llms["smart"],
    },
    "diary_header": {
        "template": diary_header_template,
        "schema": DiaryHeader,
        "llm": llms["smart"],
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
        "template": wassup_flow_template,
        "schema": WassupSchema,
        "llm": llms["mini"]
    },
    # Compact pipeline: combined valuation + scheduling in one call
    # Uses OpenRouter preset when available, falls back to OpenAI mini/smart
    "compact_schedule": {
        "template": compact_one_time_template,
        "schema": CompactSchedule,
        "llm": llms.get("openrouter_fast", llms["mini"]),
    },
    "compact_schedule_smart": {
        "template": compact_one_time_template,
        "schema": CompactSchedule,
        "llm": llms["smart"],
    },
    "compact_planning": {
        "template": compact_recurring_template,
        "schema": CompactPlanning,
        "llm": llms.get("openrouter_fast", llms["mini"]),
    },
    "compact_planning_smart": {
        "template": compact_recurring_template,
        "schema": CompactPlanning,
        "llm": llms["smart"],
    },

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