from collections import defaultdict
from typing import Optional

from geniusweb.issuevalue.Bid import Bid
from geniusweb.issuevalue.DiscreteValueSet import DiscreteValueSet
from geniusweb.issuevalue.Domain import Domain
from geniusweb.issuevalue.Value import Value
from scipy.stats import chisquare


class OpponentModel:
    def __init__(self, domain: Domain, k: int, alpha: int, beta: int):
        self.domain: Domain = domain
        self.k: int = k
        self.alpha: int = alpha
        self.beta: int = beta
        self.offer_count: int = 0
        self.issue_estimators: dict[str, IssueEstimator] = {
            i: IssueEstimator(v) for i, v in domain.getIssuesValues().items()
        }
        self.n: int = len(self.issue_estimators)
        self.current_window: list[Bid] = []
        self.prev_window: list[Bid] = []

    def update(self, bid: Bid, time: float) -> None:
        self.offer_count += 1
        for issue_id, issue_estimator in self.issue_estimators.items():
            issue_estimator.update(bid.getValue(issue_id))
        self.current_window.append(bid)

        if len(self.current_window) < self.k:
            return
        if len(self.prev_window) == 0:
            self.prev_window = [b for b in self.current_window]
            self.current_window = []
            return

        current_weights: dict[str, float] = {
            issue_name: issue.weight
            for issue_name, issue in self.issue_estimators.items()
        }

        prev_freq_values: dict[str, dict[Value, float]] = self.freq(self.prev_window)
        current_freq_values: dict[str, dict[Value, float]] = self.freq(
            self.current_window
        )
        for issue, val_set in self.domain.getIssuesValues().items():
            for val in val_set:
                if val not in prev_freq_values[issue]:
                    prev_freq_values[issue][val] = 1 / (self.n + len(self.prev_window))
                if val not in current_freq_values[issue]:
                    current_freq_values[issue][val] = 1 / (
                        self.n + len(self.current_window)
                    )

        e: set[str] = set()
        concession: bool = False
        for issue in self.domain.getIssues():
            prev_freq_values_i: dict[Value, float] = prev_freq_values[issue]
            prev_freq_values_i = {
                k: prev_freq_values_i[k]
                for k in sorted(prev_freq_values_i.keys(), key=lambda x: hash(x))
            }
            current_freq_values_i: dict[Value, float] = current_freq_values[issue]
            current_freq_values_i = {
                k: current_freq_values_i[k]
                for k in sorted(current_freq_values_i.keys(), key=lambda x: hash(x))
            }
            _, p = chisquare(
                list(current_freq_values_i.values()), list(prev_freq_values_i.values())
            )
            if p > 0.05:
                e.add(issue)
            else:
                v_i: dict[Value, int] = {}
                for val, val_est in self.issue_estimators[issue].value_trackers.items():
                    v_i[val] = val_est.count
                for val in self.domain.getValues(issue):
                    if val not in v_i:
                        v_i[val] = 0
                v_i = {k: v_i[k] for k in sorted(v_i.keys(), key=lambda x: hash(x))}
                prev_expected_util = sum(
                    [
                        a * b
                        for a, b in zip(
                            (v_i.values()), list(prev_freq_values_i.values())
                        )
                    ]
                )
                current_expected_util = sum(
                    [
                        a * b
                        for a, b in zip(
                            list(v_i.values()), list(current_freq_values_i.values())
                        )
                    ]
                )
                if current_expected_util < prev_expected_util:
                    concession = True

        if len(e) != self.n and concession:
            for issue in e:
                current_weights[issue] += self.delta(time)
            for issue in e:
                self.issue_estimators[issue].weight = current_weights[issue]

        self.prev_window = self.current_window
        self.current_window = []

    def freq(self, bids: list[Bid]) -> dict[str, dict[Value, float]]:
        value_occurrence_counts: dict[str, dict[Value, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        for bid in bids:
            for issue, value in bid.getIssueValues().items():
                value_occurrence_counts[issue][value] += 1

        freq_values: dict[str, dict[Value, float]] = defaultdict(dict)
        for bid in bids:
            for issue, value in bid.getIssueValues().items():
                freq_values[issue][value] = (
                    1 + value_occurrence_counts[issue][value]
                ) / (self.n + len(bids))
        return freq_values

    def delta(self, t: float) -> float:
        return self.alpha * (1 - t**self.beta)

    def get_predicted_utility(self, bid: Bid, gamma: float) -> Optional[float]:
        if self.offer_count < 2 * self.k or bid is None:
            return None

        total_issue_weight: float = 0.0
        value_utilities: list[float] = []
        issue_weights: list[float] = []
        for issue_id, issue_estimator in self.issue_estimators.items():
            value: Value = bid.getValue(issue_id)
            value_utilities.append(issue_estimator.get_value_utility(value, gamma))
            issue_weights.append(issue_estimator.weight)
            total_issue_weight += issue_estimator.weight

        # normalise the issue weights such that the sum is 1.0
        if total_issue_weight == 0.0:
            issue_weights = [1 / len(issue_weights) for _ in issue_weights]
        else:
            issue_weights = [iw / total_issue_weight for iw in issue_weights]

        # calculate predicted utility by multiplying all value utilities with their issue weight
        predicted_utility = sum(
            [iw * vu for iw, vu in zip(issue_weights, value_utilities)]
        )

        return predicted_utility


class IssueEstimator:
    def __init__(self, value_set: DiscreteValueSet) -> None:
        self.max_value_count = 0
        self.num_values = value_set.size()
        self.value_trackers: dict[Value, ValueEstimator] = defaultdict(ValueEstimator)
        self.weight = 0

    def update(self, value: Value):
        value_tracker: ValueEstimator = self.value_trackers[value]
        value_tracker.update()
        self.max_value_count = max([value_tracker.count, self.max_value_count])

    def get_value_utility(self, value: Value, gamma: float) -> float:
        if value in self.value_trackers:
            return self.value_trackers[value].calculate_utility(
                self.max_value_count, gamma
            )
        else:
            return 1 / ((1 + self.max_value_count) ** gamma)


class ValueEstimator:
    def __init__(self) -> None:
        self.count: int = 0

    def update(self) -> None:
        self.count += 1

    def calculate_utility(self, max_value_count: int, gamma: float) -> float:
        return ((1 + self.count) ** gamma) / ((1 + max_value_count) ** gamma)
