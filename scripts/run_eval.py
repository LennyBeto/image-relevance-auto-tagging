"""Standalone eval runner — same logic the /eval/run endpoint uses, callable
from the command line for EVIDENCE.md / CI. Prints top-1 precision."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.eval import run_eval

if __name__ == "__main__":
    db = SessionLocal()
    result = run_eval(db)
    print(json.dumps(result, indent=2))
    print(f"\nTOP-1 PRECISION: {result['top1_precision']:.2%}")
