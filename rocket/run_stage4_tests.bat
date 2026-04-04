@echo off
REM Quick test runner - runs only the new Stage 4 tests
echo =====================================
echo Stage 4 Test Suite - Quick Run
echo =====================================
echo.

cd rocket
python -m pytest tests/test_validator.py tests/test_consistency.py tests/test_trust.py tests/test_planner.py tests/test_pipeline.py -v --tb=short

echo.
echo =====================================
echo Test Run Complete
echo =====================================
pause
