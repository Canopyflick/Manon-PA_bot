

# Initialize LLMs
llms = {
    "gpt4o": ChatOpenAI(model_name="gpt-4o", temperature=0.3),
    "mini": ChatOpenAI(model_name="gpt-4o-mini", temperature=0.3),
    "gpt4o_high_temp": ChatOpenAI(model_name="gpt-4o", temperature=1.2),
    "mini_high_temp": ChatOpenAI(model_name="gpt-4o-mini", temperature=1.2),
}

def create_structured_outputs(llm, bindings):
    return {key: llm.with_structured_output(binding) for key, binding in bindings.items()}


# Define ChatPromptTemplate(aka 'chain')-to-Class bindings, per LLM
mini_bindings = {
    "initial_classification": InitialClassification,
    "goal_classification": GoalsClassification,
    "goal_setting_analysis": GoalAnalysis,
    "goal_setting_onetime": GoalSetData,
    "goal_setting_recurring": RecurringGoalSetData,
    "language_check": LanguageCheck,
}

gpt4o_bindings = {
    "language_correction": LanguageCorrection,
    "goal_setting_analysis": GoalAnalysis,      # for /smarter_command
    "translation": Translation,    
}

async def run_chain(chain, input_variables: dict):
    """
    A generic async function to run a given structured chain.
    This handles prompt formatting, invoking, and returning results.
    """
    try:
        prompt_value = chain["template"].invoke(input_variables)
        result = await chain["chain"].ainvoke(prompt_value.to_messages())
        return result
    except Exception as e:
        logging.error(f"Error running chain: {e}")
        raise


# Chains
initial_classification_chain = {
    "template": dummy_template,
    "chain": structured_mini["initial_classification"]
}

goal_classification_chain = {
    "template": goals_classification_template,
    "chain": structured_mini["goal_classification"]
}

goal_setting_analysis_chain = {
    "template": goal_durability_template,
    "chain": structured_mini["goal_setting_analysis"]
}

goal_setting_onetime_chain = {
    "template": goal_durability_template,  
    "chain": structured_mini["goal_setting_onetime"]
}

goal_setting_recurring_chain = {
    "template": recurring_goal_split_template,
    "chain": structured_mini["goal_setting_recurring"]
}

language_correction_chain = {
    "template": correction_template,  
    "chain": structured_gpt4o["language_correction"]
}

language_check_chain = {
    "template": language_template,
    "chain": structured_mini["language_check"]
}

translate_chain = {
    "template": translate_template,
    "chain": structured_gpt4o["translation"]
}



# Define schemas < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <
class InitialClassification(BaseModel):
    user_message_language: Literal['English', 'German', 'Dutch', 'other']
    classification: Literal['Goals', 'Reminders', 'Meta', 'Other']
    emoji_reaction: Literal[
        '??', '??', '??', '??', '??', '??', '??', '??', '??',
        '??', '??', '??', '??', '??', '??', '??', '??'
    ]

class GoalsClassification(BaseModel):
    classification: Literal['Set', 'Report_done', 'Report_failed', 'Postpone', 'Cancel', 'Pause', 'None']

# Goal setting #1
class GoalAnalysis(BaseModel):
    description: str
    durability: Literal['one-time', 'recurring']
    timeframe: Literal['today', 'by_date', 'open-ended']
    category: List[Literal['productivity', 'work', 'chores', 'relationships', 'self-development', 'money', 'impact', 'health', 'fun', 'other']]

# Goal setting #2.1 (one-time goals)
class GoalSetData(BaseModel):
    deadline: str  # Use string instead of datetime for compatibility
    schedule_reminder: bool
    reminder_time: Union[str, None] = Field(
        default=None,
        description="The timestamp for the reminder in ISO 8601 format, or null if no reminder is scheduled."
    )
    time_investment_value: float
    difficulty_multiplier: float
    impact_multiplier: float
    failure_penalty: Literal['no', 'small', 'big']
        
# Goal setting #2.2 (recurring goals)
class RecurringGoalSetData(BaseModel):
    penalty: int
    deadline: List[str]  
    interval: str
    schedule_reminder: bool
    reminder_time: Union[List[str], None] = Field(
        default=None,
        description="A list of one or more timestamps for reminders in ISO 8601 format, or null if no reminders should be scheduled."
    )
    time_investment_value: float
    difficulty_multiplier: float
    impact_multiplier: float
    penalty: int

                
# For language correction
class LanguageCorrection(BaseModel):
    corrected_text: str = Field(description="correction")
    changes: str = Field(description="succinct list of changes made")
    proficiency_score: int = Field(description="language level of source text")

# for /translate
class LanguageCheck(BaseModel):
    user_message_language: Literal['English', 'German', 'Dutch', 'other']
    
class Translation(BaseModel):
    translation: str
    

class DummyClass(BaseModel):
    dummy_field: str
    


# Helpers < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < < <



# Create structured outputs
structured_mini = create_structured_outputs(ChatOpenAI(model_name="gpt-4o-mini", temperature=0.3), mini_bindings)
structured_gpt4o = create_structured_outputs(ChatOpenAI(model_name="gpt-4o", temperature=0.3), gpt4o_bindings)

# Usage example
structured_mini_initial_classification = structured_mini["initial_classification"]


