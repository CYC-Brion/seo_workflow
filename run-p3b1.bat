@echo off
chcp 65001 > nul
cd /d "d:\工作流项目"
echo ==========================================
echo Running Part 3 - Batch 1 (13 keywords)
echo ==========================================
python -m src.cli.main workflow run keyword_library/seo_phase3_long_cycle_part3_batch1.xlsx
echo ==========================================
echo DONE! Check output/ for results.
echo ==========================================
pause
