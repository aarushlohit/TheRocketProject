@echo off
cd /d "c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket"
.venv\Scripts\python.exe -m pytest tests\test_intent_system.py tests\test_semantic_ui.py tests\test_goal_expander.py tests\test_anti_hallucination.py tests\test_safety_stage5.py -v --tb=short
pause
