@echo off
cd /d "c:\Users\Prahan\Myoffice\Patent Project\TheRocketProject\rocket"
.venv\Scripts\python.exe -m pytest tests/test_intelligence_layer.py -v --tb=short
