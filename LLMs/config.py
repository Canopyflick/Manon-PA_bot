from utils.helpers import PA
from LLMs.classes import (
    InitialClassification,
    GoalClassification,
    SetGoalAnalysis,
    GoalSetData,
    LanguageCorrection,
    LanguageCheck,
    Translation,
    DummyClass,
    Schedule,
    Planning,
    GoalAssessment,
    GoalInstanceAssessment,
)
from LLMs.prompts import (
    dummy_template,
    initial_classification_template,
    goal_classification_template,
    goal_valuation_template,
    recurring_goal_valuation_template,
    recurring_goal_split_template,
    translation_template,
    language_template,
    goal_setting_analysis_template,
    language_correction_template,
    translation_template,
    recurring_schedule_template,
    one_time_schedule_template,
)
from langchain_openai import ChatOpenAI

# Initialize LLMs and temperatures
LOW = 0.2
MID = 0.7
HIGH = 1.2

llms = {
    "gpt4o": ChatOpenAI(model_name="gpt-4o", temperature=LOW),
    "mini": ChatOpenAI(model_name="gpt-4o-mini", temperature=LOW),
    "gpt4o_high_temp": ChatOpenAI(model_name="gpt-4o", temperature=HIGH),
    "mini_high_temp": ChatOpenAI(model_name="gpt-4o-mini", temperature=HIGH),
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
    "goal_setting_analysis": {
        "template": goal_setting_analysis_template,
        "class": SetGoalAnalysis,
        "llm": llms["mini"],
    },
    "goal_valuation": {
        "template": goal_valuation_template,
        "class": GoalAssessment,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
    "recurring_goal_valuation": {
        "template": recurring_goal_valuation_template,
        "class": GoalInstanceAssessment,
        "llm": llms["mini"],  # or llms["gpt4o"], llms["mini_high_temp"] etc.
    },
     "schedule_goal": {
        "template": one_time_schedule_template,
        "class": Schedule,
        "llm": llms["mini"],
    },
     "schedule_goals": {
        "template": recurring_schedule_template,
        "class": Planning,
        "llm": llms["mini"],
    },
    "language_correction": {
        "template": language_correction_template,
        "class": LanguageCorrection,
        "llm": llms["gpt4o"],
    },
    "translation": {
        "template": translation_template,
        "class": Translation,
        "llm": llms["gpt4o"],
    },
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