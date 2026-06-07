from pydantic import BaseModel, Field
from typing import List, Optional


class GenerateQuestionRequest(BaseModel):
    role: str
    interviewType: str
    interviewerMode: str
    previousQuestion: Optional[str] = None
    previousAnswer: Optional[str] = None


class GenerateQuestionResponse(BaseModel):
    questionText: str


class AnalyzeAnswerRequest(BaseModel):
    role: str
    interviewType: str
    interviewerMode: str
    questionText: str
    answerText: str


class AnalyzeAnswerResponse(BaseModel):
    score: float = Field(ge=0, le=10)
    feedbackText: str


class QaItem(BaseModel):
    question: str
    answer: str


class GenerateFeedbackRequest(BaseModel):
    role: str
    interviewType: str
    interviewerMode: str
    qa: List[QaItem]


class GenerateFeedbackResponse(BaseModel):
    overallScore: float
    communicationScore: float
    technicalScore: float
    confidenceScore: float
    strengths: str
    weaknesses: str
    suggestions: str


class ResumeAnalysisRequest(BaseModel):
    filename: str
    fileBase64: str


class ResumeAnalysisResponse(BaseModel):
    extractedText: str
    notes: str
