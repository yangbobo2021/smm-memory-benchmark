"""Bind the Luna runtime policy to the frozen no-pacing retry runner."""
from pathlib import Path
import run_unpaced_retry as runner

HERE = Path(__file__).resolve().parent
runner.AMENDMENT = HERE / 'execution-runtime-policy.json'

if __name__ == '__main__':
    runner.main()
