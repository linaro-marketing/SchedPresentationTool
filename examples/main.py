import os
import sys
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
from sched_presentation_tool import SchedPresentationTool



if __name__ == "__main__":
    resources_updater = SchedPresentationTool(
        "https://linaroconnectsandiego.sched.com", "san19")
