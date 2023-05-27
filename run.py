import json
import time
from pathlib import Path

from utils.plot_trace import plot_trace
from utils.runners import run_session

RESULTS_DIR = Path("results", time.strftime("%Y%m%d-%H%M%S"))
# recover
# create results directory if it does not exist
if not RESULTS_DIR.exists():
    RESULTS_DIR.mkdir(parents=True)

# Settings to run a negotiation session:
# You need to specify the classpath of 2 agents to start a negotiation. Parameters for the agent can be added as a dict
# You need to specify the preference profiles for both agents. The first profile will be assigned to the first agent.
# You need to specify a time deadline (is milliseconds (ms)) we are allowed to negotiate before we end without agreement
settings = {
    "agents": [
        {
            "class": "agents.group50_agent.group50_agent.Group50Agent",
            "parameters": {"storage_dir": "agent_storage/Group50Agent"},
        },
        # {
        #     "class": "agents.template_agent.template_agent.TemplateAgent",
        #     "parameters": {"storage_dir": "agent_storage/TemplateAgent"},
        # },
        # {
        #     "class": "agents.boulware_agent.boulware_agent.BoulwareAgent",
        # },
        # {
        #     "class": "agents.conceder_agent.conceder_agent.ConcederAgent",
        # },
        # {
        #     "class": "agents.hardliner_agent.hardliner_agent.HardlinerAgent",
        # },
        # {
        #     "class": "agents.linear_agent.linear_agent.LinearAgent",
        # },
        # {
        #     "class": "agents.random_agent.random_agent.RandomAgent",
        # },
        # {
        #     "class": "agents.stupid_agent.stupid_agent.StupidAgent",
        # },
        {
            "class": "agents.CSE3210.agent2.agent2.Agent2",
        },
        # {
        #     "class": "agents.CSE3210.agent3.agent3.Agent3",
        # },
        # {
        #     "class": "agents.CSE3210.agent7.agent7.Agent7",
        # },
        # {
        #     "class": "agents.CSE3210.agent11.agent11.Agent11",
        # },
        # {
        #     "class": "agents.ANL2022.dreamteam109_agent.dreamteam109_agent.DreamTeam109Agent",
        #     "parameters": {"storage_dir": "agent_storage/DreamTeam109Agent"},
        # },
        # {
        #     "class": "agents.ANL2022.Pinar_Agent.Pinar_Agent.Pinar_Agent",
        #     "parameters": {"storage_dir": "agent_storage/Pinar_Agent"},
        # },
    ],
    "profiles": ["domains/domain00/profileA.json", "domains/domain00/profileB.json"],
    "deadline_time_ms": 10000,
}

# run a session and obtain results in dictionaries
session_results_trace, session_results_summary = run_session(settings)

# plot trace to html file
if not session_results_trace["error"]:
    plot_trace(session_results_trace, RESULTS_DIR.joinpath("trace_plot.html"))

# write results to file
with open(
    RESULTS_DIR.joinpath("session_results_trace.json"), "w", encoding="utf-8"
) as f:
    f.write(json.dumps(session_results_trace, indent=2))
with open(
    RESULTS_DIR.joinpath("session_results_summary.json"), "w", encoding="utf-8"
) as f:
    f.write(json.dumps(session_results_summary, indent=2))
