@echo off
pip install -r requirements.txt
if not exist database.db (
    py init_db.py
)
py app.py
pause
