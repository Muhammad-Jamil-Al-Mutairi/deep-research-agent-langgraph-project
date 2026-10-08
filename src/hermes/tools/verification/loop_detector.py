"""Loop detection.

``LoopDetectionResult`` and ``LoopDetector`` are GIVEN by the SDAIA starter notebook
(section 2) and are kept verbatim. HERMES wires them into the pipeline in three places:

1. Tool repetition - ``LoopDetector.check_tool_call`` runs before every research-agent
   tool call (``hermes.agents.common.loop_guard_middleware``).
2. Design repetition - the guard node calls ``check_tool_call('propose_design', fingerprint)``
   so re-proposing an identical design is caught.
3. Stagnation - the guard node calls ``check_output_stagnation`` on designer rationales and
   ``MetricStagnationDetector`` (HERMES extension) on the numeric verification score.
"""

from dataclasses import dataclass


@dataclass
class LoopDetectionResult:
    is_looping: bool
    strategy: str  # 'exact', 'fuzzy', 'stagnation', or 'none'
    message: str
    confidence: float


class LoopDetector:
    """Detects agent loops using exact match, fuzzy match, and stagnation."""

    def __init__(self, exact_threshold: int = 2, fuzzy_threshold: float = 0.8,
                 stagnation_window: int = 3):
        self.exact_threshold = exact_threshold
        self.fuzzy_threshold = fuzzy_threshold
        self.stagnation_window = stagnation_window
        self.tool_history: list[tuple[str, str]] = []  # (tool_name, args_str)
        self.output_history: list[str] = []

    def _jaccard_similarity(self, s1: str, s2: str) -> float:
        """Word-level overlap between two strings: shared words / all words."""
        tokens1 = set(s1.lower().split())
        tokens2 = set(s2.lower().split())
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
        return len(tokens1 & tokens2) / len(tokens1 | tokens2)

    def check_tool_call(self, tool_name: str, tool_input: str) -> LoopDetectionResult:
        """Call this BEFORE running a tool. Flags identical or near-identical repeats."""
        current = (tool_name, tool_input.strip())
        exact_count = sum(1 for past_tool, past_input in self.tool_history
                          if (past_tool, past_input.strip()) == current)
        if exact_count >= self.exact_threshold:
            self.tool_history.append(current)
            return LoopDetectionResult(
                is_looping=True, strategy='exact', confidence=1.0,
                message=(f"Exact loop detected: '{tool_name}' called {exact_count + 1} "
                         f'times with identical arguments. Change your approach.'))

        recent_history = self.tool_history[-5:]
        fuzzy_matches = sum(1 for past_tool, past_input in recent_history
                            if past_tool == tool_name
                            and self._jaccard_similarity(tool_input, past_input) >= self.fuzzy_threshold)
        if fuzzy_matches >= self.exact_threshold:
            self.tool_history.append(current)
            return LoopDetectionResult(
                is_looping=True, strategy='fuzzy', confidence=0.85,
                message=(f"Fuzzy loop detected: '{tool_name}' called with very similar "
                         f'arguments {fuzzy_matches + 1} times. Try a different approach.'))

        self.tool_history.append(current)
        return LoopDetectionResult(is_looping=False, strategy='none', message='', confidence=0.0)

    def check_output_stagnation(self, output: str) -> LoopDetectionResult:
        """Flags when the last few outputs are all nearly the same text."""
        self.output_history.append(output)
        if len(self.output_history) < self.stagnation_window:
            return LoopDetectionResult(is_looping=False, strategy='none', message='', confidence=0.0)

        recent = self.output_history[-self.stagnation_window:]
        similarities = [self._jaccard_similarity(recent[i], recent[j])
                        for i in range(len(recent)) for j in range(i + 1, len(recent))]
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0
        if avg_similarity >= self.fuzzy_threshold:
            return LoopDetectionResult(
                is_looping=True, strategy='stagnation', confidence=avg_similarity,
                message=(f'Output stagnation detected: last {self.stagnation_window} '
                         f'outputs are {avg_similarity:.0%} similar. The agent is not '
                         f'making progress. Try a different approach entirely.'))
        return LoopDetectionResult(is_looping=False, strategy='none', message='', confidence=0.0)

    def reset(self):
        self.tool_history.clear()
        self.output_history.clear()


# ---- HERMES extension ---------------------------------------------------------------


class MetricStagnationDetector:
    """Numeric stagnation: the design keeps failing and its score stops improving.

    The verification score is 0 for a passing design and the negative sum of normalised
    shortfalls otherwise, so "better" means "closer to 0". Text similarity alone cannot
    see this: two rationales can read differently while the runtime stays at 1.20 h.
    """

    def __init__(self, window: int = 3, epsilon: float = 0.02):
        self.window = window
        self.epsilon = epsilon

    def check(self, scores: list[float]) -> LoopDetectionResult:
        if len(scores) < self.window:
            return LoopDetectionResult(False, 'none', '', 0.0)
        recent = scores[-self.window:]
        if any(s >= 0 for s in recent):  # a passing design is progress
            return LoopDetectionResult(False, 'none', '', 0.0)
        improvement = recent[-1] - max(recent[:-1])
        if improvement < self.epsilon:
            return LoopDetectionResult(
                is_looping=True, strategy='stagnation', confidence=1.0,
                message=(f'Metric stagnation detected: verification score over the last {self.window} '
                         f'designs is {", ".join(f"{s:.3f}" for s in recent)} (improvement {improvement:+.3f} '
                         f'< {self.epsilon}). Changing strategy.'))
        return LoopDetectionResult(False, 'none', '', 0.0)
