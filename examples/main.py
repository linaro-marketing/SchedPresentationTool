import os
import sys
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
from sched_presentation_tool import SchedPresentationTool
from secret import SCHED_API_KEY

if __name__ == "__main__":
    resources_updater = SchedPresentationTool(
        "https://bud20.sched.com", "bud20", SCHED_API_KEY)
