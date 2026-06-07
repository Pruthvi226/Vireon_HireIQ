import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas import (
    AnalyzeAnswerRequest,
    AnalyzeAnswerResponse,
    GenerateFeedbackRequest,
    GenerateFeedbackResponse,
    GenerateQuestionRequest,
    GenerateQuestionResponse,
    ResumeAnalysisRequest,
    ResumeAnalysisResponse,
)
from app.core.gemini_service import (
    analyze_answer as analyze_answer_service,
    generate_feedback as generate_feedback_service,
    generate_question as generate_question_service,
    resume_analysis as resume_analysis_service,
)

app = FastAPI(title="AI Interview Coach Service", version="1.1.0")

origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8080").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "provider": "gemini", "model": os.getenv("GEMINI_MODEL", "gemini-1.5-flash")}


@app.post("/generate-question", response_model=GenerateQuestionResponse)
def generate_question(payload: GenerateQuestionRequest) -> GenerateQuestionResponse:
    return generate_question_service(payload)


@app.post("/analyze-answer", response_model=AnalyzeAnswerResponse)
def analyze_answer(payload: AnalyzeAnswerRequest) -> AnalyzeAnswerResponse:
    return analyze_answer_service(payload)


@app.post("/generate-feedback", response_model=GenerateFeedbackResponse)
def generate_feedback(payload: GenerateFeedbackRequest) -> GenerateFeedbackResponse:
    return generate_feedback_service(payload)


@app.post("/resume-analysis", response_model=ResumeAnalysisResponse)
def resume_analysis(payload: ResumeAnalysisRequest) -> ResumeAnalysisResponse:
    try:
        return resume_analysis_service(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
