import os
import sys
from sched_data_interface import SchedDataInterface
sys.path.insert(0, os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))
from sched_presentation_tool import SchedPresentationTool
from secret import SCHED_API_KEY

if __name__ == "__main__":
    sched_data_interface = SchedDataInterface(
        "https://bud20.sched.com",
        SCHED_API_KEY,
        "bud20")
    json_data = sched_data_interface.getSessionsData()
    presentation_tool = SchedPresentationTool("presentations/", "other_files/", json_data)
    presentation_tool.download()
