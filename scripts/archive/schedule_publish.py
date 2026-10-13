"""
定时任务脚本：每小时发布一篇草稿
供 Windows Task Scheduler 调用
"""
import subprocess
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).parent / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "auto_publish.log"

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def main():
    log("Starting publish-next...")

    result = subprocess.run(
        [sys.executable, "-m", "src.cli.main", "workflow", "publish-next"],
        cwd=str(Path(__file__).parent),
        capture_output=True,
        text=True,
        timeout=60,
    )

    if result.stdout:
        for line in result.stdout.strip().splitlines():
            log(f"  OUT: {line}")
    if result.stderr:
        for line in result.stderr.strip().splitlines():
            log(f"  ERR: {line}")

    log(f"Exit code: {result.returncode}")
    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
