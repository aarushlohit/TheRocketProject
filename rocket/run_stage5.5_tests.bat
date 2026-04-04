@echo off
REM Stage 5.5 Intelligence Layer Test Runner
REM Run from: rocket directory

echo ====================================
echo Stage 5.5 Intelligence Layer Tests
echo ====================================
echo.

cd /d "%~dp0"

REM Run Stage 5.5 tests
echo Running Intelligence Layer tests...
.venv\Scripts\python.exe -m pytest tests/test_intelligence_layer.py -v

echo.
echo ====================================
echo Complete Stage 5 + 5.5 Tests
echo ====================================
echo.

.venv\Scripts\python.exe -m pytest tests/test_intelligence_layer.py tests/test_intent_system.py tests/test_semantic_ui.py tests/test_goal_expander.py tests/test_anti_hallucination.py tests/test_safety_stage5.py -v

echo.
echo Done!
pause
