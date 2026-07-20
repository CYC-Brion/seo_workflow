@echo off
REM ========================
REM SEO Workflow Batch Runner
REM 在独立的终端窗口运行，不会因 Claude Code 断开而中断
REM ========================

cd /d "d:\工作流项目"

echo ==========================================
echo Running Part 3 - Batch 1 (13 keywords)
echo ==========================================
python -m src.cli.main workflow run keyword_library/seo_phase3_long_cycle_part3_batch1.xlsx
if %errorlevel% neq 0 (
    echo [WARN] Part 3 Batch 1 exited with code %errorlevel%
)

echo ==========================================
echo Running Part 3 - Batch 2 (14 keywords)
echo ==========================================
python -m src.cli.main workflow run keyword_library/seo_phase3_long_cycle_part3_batch2.xlsx
if %errorlevel% neq 0 (
    echo [WARN] Part 3 Batch 2 exited with code %errorlevel%
)

echo ==========================================
echo Running Part 4 - Batch 1 (13 keywords)
echo ==========================================
python -m src.cli.main workflow run keyword_library/seo_phase3_long_cycle_part4_batch1.xlsx
if %errorlevel% neq 0 (
    echo [WARN] Part 4 Batch 1 exited with code %errorlevel%
)

echo ==========================================
echo Running Part 4 - Batch 2 (14 keywords)
echo ==========================================
python -m src.cli.main workflow run keyword_library/seo_phase3_long_cycle_part4_batch2.xlsx
if %errorlevel% neq 0 (
    echo [WARN] Part 4 Batch 2 exited with code %errorlevel%
)

echo ==========================================
echo Running Part 5 - Batch 1 (11 keywords)
echo ==========================================
python -m src.cli.main workflow run keyword_library/seo_phase3_long_cycle_part5_batch1.xlsx
if %errorlevel% neq 0 (
    echo [WARN] Part 5 Batch 1 exited with code %errorlevel%
)

echo ==========================================
echo Running Part 5 - Batch 2 (12 keywords)
echo ==========================================
python -m src.cli.main workflow run keyword_library/seo_phase3_long_cycle_part5_batch2.xlsx
if %errorlevel% neq 0 (
    echo [WARN] Part 5 Batch 2 exited with code %errorlevel%
)

echo ==========================================
echo ALL DONE! Check output/ for results.
echo ==========================================
pause
