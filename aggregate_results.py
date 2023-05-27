import json
import os
from collections import defaultdict
from pathlib import Path

EVAL_RESULTS_DIR = Path("eval_results")
if not EVAL_RESULTS_DIR.exists():
    raise RuntimeError("EVALUATION RESULTS COULD NOT BE FOUND")

domain_results = defaultdict(list)
for domain in os.listdir(EVAL_RESULTS_DIR):
    domain_dir = EVAL_RESULTS_DIR.joinpath(domain)
    for neg in os.listdir(domain_dir):
        with open(
            f"{domain_dir}/{neg}/session_results_summary.json", mode="r"
        ) as res_file:
            result_dict = json.load(res_file)

        utility_keys = sorted(
            [k for k in result_dict.keys() if k.startswith("utility")]
        )
        result_dict["utility_1"] = result_dict.pop(utility_keys[0])
        result_dict["utility_2"] = result_dict.pop(utility_keys[1])
        domain_results[domain].append(result_dict)

domain_means = {}
for domain_name, domain_result in domain_results.items():
    mean_results = {
        "num_offers": 0,
        "utility_1": 0,
        "utility_2": 0,
        "nash_product": 0,
        "social_welfare": 0,
    }
    for result in domain_result:
        for cat_name, cat_value in result.items():
            if cat_name not in mean_results:
                continue
            mean_results[cat_name] += cat_value / len(domain_result)
    domain_means[domain_name] = mean_results

with open(f"{EVAL_RESULTS_DIR}/mean_results.json", mode="w") as f:
    json.dump(domain_means, f)
