"""
Data models for follow-up questions functionality.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class QuestionPriority(str, Enum):
    """Priority levels for follow-up questions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QuestionCategory(str, Enum):
    """Categories for follow-up questions."""
    CLARIFICATION = "clarification"
    RELATED_TOPIC = "related_topic"
    MORE_DETAILS = "more_details"
    NEXT_STEPS = "next_steps"
    ALTERNATIVE = "alternative"
    GENERAL = "general"


class FollowUpQuestion(BaseModel):
    """Individual follow-up question with metadata."""
    question: str = Field(
        description="The follow-up question text",
        min_length=1,
        max_length=500
    )
    
    category: QuestionCategory = Field(
        default=QuestionCategory.GENERAL,
        description="The category of the follow-up question"
    )
    
    priority: QuestionPriority = Field(
        default=QuestionPriority.MEDIUM,
        description="The priority level of the question"
    )
    
    confidence: Optional[float] = Field(
        default=None,
        description="Confidence score for question relevance (0.0 to 1.0)",
        ge=0.0,
        le=1.0
    )
    
    related_sources: List[str] = Field(
        default_factory=list,
        description="List of source IDs that are relevant to this question"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the fees for business registration?",
                "category": "more_details",
                "priority": "high",
                "confidence": 0.95,
                "related_sources": ["brs_guidelines", "fee_schedule"]
            }
        }


class FollowUpQuestions(BaseModel):
    """Container for multiple follow-up questions with metadata."""
    questions: List[FollowUpQuestion] = Field(
        default_factory=list,
        description="List of follow-up questions"
    )
    
    total_count: int = Field(
        default=0,
        description="Total number of questions",
        ge=0
    )
    
    generation_confidence: Optional[float] = Field(
        default=None,
        description="Overall confidence in the quality of generated questions",
        ge=0.0,
        le=1.0
    )
    
    def __init__(self, **data):
        super().__init__(**data)
        # Auto-calculate total_count if not provided
        if 'total_count' not in data or data['total_count'] == 0:
            self.total_count = len(self.questions)
    
    def add_question(self, question: FollowUpQuestion) -> None:
        """Add a question to the collection."""
        if len(self.questions) < 10:  # Respect max_items constraint
            self.questions.append(question)
            self.total_count = len(self.questions)
    
    def get_by_priority(self, priority: QuestionPriority) -> List[FollowUpQuestion]:
        """Get questions filtered by priority."""
        return [q for q in self.questions if q.priority == priority]
    
    def get_by_category(self, category: QuestionCategory) -> List[FollowUpQuestion]:
        """Get questions filtered by category."""
        return [q for q in self.questions if q.category == category]
    
    def to_simple_list(self) -> List[str]:
        """Convert to simple list of question strings for backward compatibility."""
        return [q.question for q in self.questions]
    
    class Config:
        json_schema_extra = {
            "example": {
                "questions": [
                    {
                        "question": "What are the fees for business registration?",
                        "category": "more_details",
                        "priority": "high",
                        "confidence": 0.95,
                        "related_sources": ["brs_guidelines"]
                    },
                    {
                        "question": "How long does the business registration process take?",
                        "category": "more_details",
                        "priority": "medium",
                        "confidence": 0.90,
                        "related_sources": ["process_timeline"]
                    },
                    {
                        "question": "What documents are required for business registration?",
                        "category": "next_steps",
                        "priority": "high",
                        "confidence": 0.92,
                        "related_sources": ["document_requirements"]
                    }
                ],
                "total_count": 3,
                "generation_confidence": 0.92
            }
        }


# Helper functions for creating follow-up questions
def create_simple_question(question_text: str, 
                          category: QuestionCategory = QuestionCategory.GENERAL,
                          priority: QuestionPriority = QuestionPriority.MEDIUM) -> FollowUpQuestion:
    """Create a simple follow-up question with minimal metadata."""
    return FollowUpQuestion(
        question=question_text,
        category=category,
        priority=priority
    )


def create_questions_from_list(question_list: List[str]) -> FollowUpQuestions:
    """Create FollowUpQuestions from a simple list of strings for backward compatibility."""
    questions = [create_simple_question(q) for q in question_list]
    return FollowUpQuestions(questions=questions)
