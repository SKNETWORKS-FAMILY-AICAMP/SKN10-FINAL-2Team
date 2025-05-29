from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/survey", response_class=HTMLResponse)
async def survey(request: Request):
    return templates.TemplateResponse("survey.html", {"request": request})

@router.post("/api/save_survey_results")
async def save_survey_results(data: dict):
    # TODO: 데이터베이스에 결과 저장
    return {"status": "success"} 