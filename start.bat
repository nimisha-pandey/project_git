cd /d %~dp0
start cmd /k ".\.venv\Scripts\activate.bat & uvicorn main:app --reload"
