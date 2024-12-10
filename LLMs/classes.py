from typing import Literal, List, Union
from typing_extensions import Annotated, TypedDict
from pydantic import BaseModel, Field
import asyncio


class DummyClass(BaseModel):
    dummy_field: str
    
class InitialClassification(BaseModel):
    user_message_language: Literal['English', 'German', 'Dutch', 'other']
    classification: Literal['Goals', 'Reminders', 'Meta', 'Other'] 



class GoalClassification(BaseModel):
    classification: Literal['Set', 'Report_done', 'Report_failed', 'Postpone', 'Cancel', 'Pause', 'None']

# Goal setting #1
class SetGoalAnalysis(BaseModel):
    description: str        # not used, but keeping it in case it does help the llm
    evaluation_frequency: Literal['one-time', 'recurring']
    timeframe: Literal['today', 'by_date', 'open-ended']
    category: List[Literal['productivity', 'work', 'chores', 'relationships', 'self-development', 'money', 'impact', 'health', 'fun', 'other']]
    
# Goal setting #2.1    
class GoalAssessment(BaseModel):
    reasoning: str
    time_investment_value: float
    difficulty_multiplier: float
    impact_multiplier: float
    failure_penalty: Literal['no', 'small', 'big']
    
# Goal setting #2.2 (recurring goals branch)
class GoalInstanceAssessment(BaseModel):
    reasoning: str
    time_investment_value: float
    difficulty_multiplier: float
    impact_multiplier: float
    failure_penalty: Literal['no', 'small', 'big']

# Goal setting #3.1  
class Schedule(BaseModel):
    reasoning: str
    description: str
    evaluation_deadline: str
    schedule_reminder: bool
    reminder: Union[str, None] = Field(
        default=None,
        description="The timestamp for the reminder in ISO 8601 format, or null if no reminder is scheduled."
    )
    
# Goal setting #3.2 (recurring goals branch)      
class Planning(BaseModel):
    description: str
    evaluation_deadlines: List[str]
    interval: Literal['intra-day', 'daily', 'every few days', 'weekly', 'every few weeks', 'monthly', 'every few months', 'bi-annually', 'yearly', 'longer than yearly', 'custom']
    schedule_reminder: bool
    reminders: Union[str, None] = Field(
        default=None,
        description="The timestamp for the reminder in ISO 8601 format, or null if no reminder is scheduled."
    )
    
    
# Goal setting #2.1 (one-time goals)
class GoalSetData(BaseModel):
    deadline: str  # Use string instead of datetime for compatibility
    schedule_reminder: bool
    reminder_time: Union[str, None] = Field(
        default=None,
        description="The timestamp for the reminder in ISO 8601 format, or null if no reminder is scheduled."
    )
                
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

class Translations(BaseModel):
    formal: str
    casual: str
    degenerate: str
    