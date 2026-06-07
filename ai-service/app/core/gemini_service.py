from __future__ import annotations

import base64
from collections import OrderedDict

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
from app.core.llm import generate_text, parse_json_strict

_RESUME_SUMMARY_CACHE: OrderedDict[str, str] = OrderedDict()
_RESUME_CACHE_MAX = 256


def _cache_resume(key: str, summary: str) -> None:
    if key in _RESUME_SUMMARY_CACHE:
        _RESUME_SUMMARY_CACHE.move_to_end(key)
    _RESUME_SUMMARY_CACHE[key] = summary
    if len(_RESUME_SUMMARY_CACHE) > _RESUME_CACHE_MAX:
        _RESUME_SUMMARY_CACHE.popitem(last=False)


def generate_question(payload: GenerateQuestionRequest) -> GenerateQuestionResponse:
    system_prompt = (
        "You are an interviewer. Keep output short. Return one question only, plain text, max 35 words."
    )
    user_prompt = (
        f"Role:{payload.role};Type:{payload.interviewType};Mode:{payload.interviewerMode}. "
        f"PrevQ:{(payload.previousQuestion or 'none')[:180]}. "
        f"PrevA:{(payload.previousAnswer or 'none')[:220]}."
    )

    try:
        question = generate_text(system_prompt, user_prompt, temperature=0.3, max_output_tokens=80)
    except Exception:
        question = f"For a {payload.role} {payload.interviewType} interview, explain one challenging project and your measurable impact."

    return GenerateQuestionResponse(questionText=question.strip())


def analyze_answer(payload: AnalyzeAnswerRequest) -> AnalyzeAnswerResponse:
    system_prompt = (
        "Return JSON only with keys: score, strengths, weaknesses, improvements, ideal_answer. "
        "score must be 0-10. Keep each text concise."
    )
    user_prompt = (
        f"Role:{payload.role};Type:{payload.interviewType};Mode:{payload.interviewerMode}. "
        f"Question:{payload.questionText[:260]}. "
        f"Answer:{payload.answerText[:900]}."
    )

    fallback = {
        "score": 6,
        "strengths": ["Attempted core response"],
        "weaknesses": ["Needs clearer structure and evidence"],
        "improvements": ["Use STAR and add measurable outcomes"],
        "ideal_answer": "Start with context, actions, and quantified impact in 4-6 lines.",
    }

    try:
        raw = generate_text(system_prompt, user_prompt, temperature=0.1, max_output_tokens=280)
        data = parse_json_strict(raw)
    except Exception:
        data = fallback

    score = float(data.get("score", fallback["score"]))
    score = max(0.0, min(10.0, score))

    strengths = data.get("strengths", fallback["strengths"])
    weaknesses = data.get("weaknesses", fallback["weaknesses"])
    improvements = data.get("improvements", fallback["improvements"])
    ideal_answer = data.get("ideal_answer", fallback["ideal_answer"])

    if isinstance(strengths, list):
        strengths = "; ".join(str(x) for x in strengths[:3])
    if isinstance(weaknesses, list):
        weaknesses = "; ".join(str(x) for x in weaknesses[:3])
    if isinstance(improvements, list):
        improvements = "; ".join(str(x) for x in improvements[:3])

    feedback = (
        f"Strengths: {strengths}\n"
        f"Weaknesses: {weaknesses}\n"
        f"Improvement: {improvements}\n"
        f"Ideal: {ideal_answer}"
    )

    return AnalyzeAnswerResponse(score=score, feedbackText=feedback)


def generate_feedback(payload: GenerateFeedbackRequest) -> GenerateFeedbackResponse:
    system_prompt = (
        "Return JSON only with keys: overallScore, communicationScore, technicalScore, confidenceScore, strengths, weaknesses, suggestions. "
        "Scores 0-10. Keep strengths/weaknesses/suggestions concise."
    )

    qa_limited = payload.qa[:7]
    compact_qa = "\n".join(
        [f"Q:{x.question[:180]}\nA:{x.answer[:320]}" for x in qa_limited]
    )

    user_prompt = (
        f"Role:{payload.role};Type:{payload.interviewType};Mode:{payload.interviewerMode}. "
        f"Use this transcript subset:\n{compact_qa}"
    )

    fallback = {
        "overallScore": 6.4,
        "communicationScore": 6.2,
        "technicalScore": 6.3,
        "confidenceScore": 6.1,
        "strengths": "Clear intent and baseline domain understanding.",
        "weaknesses": "Limited depth, missing quantified impact, uneven structure.",
        "suggestions": "Practice STAR format, add metrics, and keep answers concise with stronger technical specifics.",
    }

    try:
        raw = generate_text(system_prompt, user_prompt, temperature=0.1, max_output_tokens=360)
        data = parse_json_strict(raw)
    except Exception:
        data = fallback

    return GenerateFeedbackResponse(
        overallScore=float(data.get("overallScore", fallback["overallScore"])),
        communicationScore=float(data.get("communicationScore", fallback["communicationScore"])),
        technicalScore=float(data.get("technicalScore", fallback["technicalScore"])),
        confidenceScore=float(data.get("confidenceScore", fallback["confidenceScore"])),
        strengths=str(data.get("strengths", fallback["strengths"])),
        weaknesses=str(data.get("weaknesses", fallback["weaknesses"])),
        suggestions=str(data.get("suggestions", fallback["suggestions"])),
    )


def resume_analysis(payload: ResumeAnalysisRequest) -> ResumeAnalysisResponse:
    cache_key = f"{payload.filename}:{hash(payload.fileBase64)}"
    cached = _RESUME_SUMMARY_CACHE.get(cache_key)
    if cached:
        return ResumeAnalysisResponse(extractedText=cached, notes="resume-summary-cache-hit")

    try:
        raw_bytes = base64.b64decode(payload.fileBase64)
        extracted = raw_bytes.decode("utf-8", errors="ignore")
    except Exception as exc:
        raise ValueError(f"Invalid resume payload: {exc}")

    if not extracted.strip():
        extracted = "Could not extract readable text from file bytes."

    extracted = extracted[:7000]
    system_prompt = (
        "Summarize resume text in compact plain text with sections: Summary, Skills, Experience Highlights. Max 700 words."
    )
    user_prompt = f"Filename:{payload.filename}\nContent:\n{extracted}"

    try:
        summary = generate_text(system_prompt, user_prompt, temperature=0.0, max_output_tokens=900)
    except Exception:
        summary = extracted[:2500]

    _cache_resume(cache_key, summary)
    return ResumeAnalysisResponse(extractedText=summary, notes="resume-summarized")
