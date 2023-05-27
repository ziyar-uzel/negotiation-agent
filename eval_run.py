import json
import pickle
import time
from pathlib import Path

from utils.plot_trace import plot_trace
from utils.runners import run_session

RESULTS_DIR = Path("eval_results")
if not RESULTS_DIR.exists():
    RESULTS_DIR.mkdir(parents=True)

all_agents = [
    {
        "class": "agents.template_agent.template_agent.TemplateAgent",
        "parameters": {"storage_dir": "agent_storage/TemplateAgent"},
    },
    {
        "class": "agents.boulware_agent.boulware_agent.BoulwareAgent",
    },
    {
        "class": "agents.conceder_agent.conceder_agent.ConcederAgent",
    },
    {
        "class": "agents.hardliner_agent.hardliner_agent.HardlinerAgent",
    },
    {
        "class": "agents.linear_agent.linear_agent.LinearAgent",
    },
    {
        "class": "agents.random_agent.random_agent.RandomAgent",
    },
    {
        "class": "agents.stupid_agent.stupid_agent.StupidAgent",
    },
    {
        "class": "agents.CSE3210.agent2.agent2.Agent2",
    },
    {
        "class": "agents.CSE3210.agent3.agent3.Agent3",
    },
    {
        "class": "agents.CSE3210.agent7.agent7.Agent7",
    },
    {
        "class": "agents.CSE3210.agent11.agent11.Agent11",
    },
    {
        "class": "agents.ANL2022.dreamteam109_agent.dreamteam109_agent.DreamTeam109Agent",
        "parameters": {"storage_dir": "agent_storage/DreamTeam109Agent"},
    },
    {
        "class": "agents.ANL2022.Pinar_Agent.Pinar_Agent.Pinar_Agent",
        "parameters": {"storage_dir": "agent_storage/Pinar_Agent"},
    },
    {
        "class": "agents.group50_agent.group50_agent.Group50Agent",
        "parameters": {"storage_dir": "agent_storage/Group50Agent"},
    },
]

domains = {
    "00": ["domains/domain00/profileA.json", "domains/domain00/profileB.json"],
    "01": ["domains/domain01/profileA.json", "domains/domain01/profileB.json"],
    "02": ["domains/domain02/profileA.json", "domains/domain02/profileB.json"],
    "03": ["domains/domain03/profileA.json", "domains/domain03/profileB.json"],
    "04": ["domains/domain04/profileA.json", "domains/domain04/profileB.json"],
    "05": ["domains/domain05/profileA.json", "domains/domain05/profileB.json"],
}

for domain_name, profiles in domains.items():
    domain_results_dir = Path(RESULTS_DIR, f"domain{domain_name}")
    if not domain_results_dir.exists():
        domain_results_dir.mkdir()

    for agent in all_agents:
        negotiation_results_dir = Path(
            domain_results_dir, time.strftime("%Y%m%d-%H%M%S")
        )
        if not negotiation_results_dir.exists():
            negotiation_results_dir.mkdir()

        settings = {
            "agents": [
                {
                    "class": "agents.group50_agent.group50_agent.Group50Agent",
                    "parameters": {"storage_dir": "agent_storage/Group50Agent"},
                },
                agent,
            ],
            "profiles": profiles,
            "deadline_time_ms": 10000,
        }
        session_results_trace, session_results_summary = run_session(settings)

        # plot trace to html file
        if not session_results_trace["error"]:
            plot_trace(
                session_results_trace,
                negotiation_results_dir.joinpath("trace_plot.html"),
            )

        # write results to file
        with open(
            negotiation_results_dir.joinpath("session_results_trace.json"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(session_results_trace, indent=2))
        with open(
            negotiation_results_dir.joinpath("session_results_summary.json"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(json.dumps(session_results_summary, indent=2))
