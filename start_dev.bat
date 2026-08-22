@echo off
echo ==============================================================================
echo       Starting InterviewQuest AI (Backend FastAPI + Frontend Vite)
echo ==============================================================================

start "InterviewQuest Backend" cmd /k "cd backend && .\venv\Scripts\python -m uvicorn app.main:app --reload --port 8000"
start "InterviewQuest Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo Backend running at: http://localhost:8000
echo API Documentation:  http://localhost:8000/docs
echo Frontend running at: http://localhost:5173
echo.
pause
