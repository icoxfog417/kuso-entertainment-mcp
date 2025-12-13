"""Kuso Entertainment MCP Simulator.

Simulates coding agent interaction with entertainment tools during wait times.
Uses Strands Agents and strands_evals for evaluation.
"""

from strands import Agent, tool
from strands_evals import Case, Experiment
from strands_evals.evaluators import Evaluator
from strands_evals.evaluators.evaluator import EvaluationLevel
from strands_evals.types.evaluation import EvaluationData, EvaluationOutput
from strands_evals.telemetry import StrandsEvalsTelemetry
from strands_evals.mappers import StrandsInMemorySessionMapper


class ToolInvokedEvaluator(Evaluator):
    """Evaluator: did agent invoke ALL expected tools?"""

    evaluation_level = EvaluationLevel.TOOL_LEVEL

    def __init__(self, expected_tools: list[str]):
        super().__init__()
        self.expected_tools = set(expected_tools)

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        tool_inputs = self._parse_trajectory(evaluation_case)
        invoked = {t.tool_execution_details.tool_call.name for t in tool_inputs}
        missing = self.expected_tools - invoked
        passed = len(missing) == 0
        return [EvaluationOutput(
            score=1.0 if passed else 0.0,
            test_pass=passed,
            reason=f"Invoked: {list(invoked)}, Missing: {list(missing)}" if missing else f"All tools invoked: {list(invoked)}",
        )]


class ViewingDurationEvaluator(Evaluator):
    """Evaluates viewing duration from end_viewing calls.
    
    Scoring based on README criteria:
    - Under 60 seconds: score 1-2 (fail)
    - 60-120 seconds: score 3 (pass)
    - Over 120 seconds: score 4-5 (pass)
    """

    evaluation_level = EvaluationLevel.TOOL_LEVEL

    def evaluate(self, evaluation_case: EvaluationData) -> list[EvaluationOutput]:
        import json
        tool_inputs = self._parse_trajectory(evaluation_case)
        total_duration = 0
        for t in tool_inputs:
            if t.tool_execution_details.tool_call.name == "end_viewing":
                content = t.tool_execution_details.tool_result.content
                try:
                    parsed = json.loads(content.replace("'", '"'))
                    total_duration += parsed.get("viewing_duration", 0)
                except:
                    pass

        if total_duration == 0:
            return [EvaluationOutput(score=0.0, test_pass=False, reason="No viewing duration recorded")]

        if total_duration < 60:
            score = 1.0 if total_duration < 30 else 2.0
            passed = False
        elif total_duration <= 120:
            score = 3.0
            passed = True
        else:
            score = 4.0 if total_duration <= 180 else 5.0
            passed = True

        return [EvaluationOutput(
            score=score / 5.0,  # Normalize to 0-1
            test_pass=passed,
            reason=f"Total viewing duration: {total_duration}s (score: {score}/5)",
        )]

# Mock content database
MOCK_CONTENTS = [
    {"id": f"video_{i:03d}", "title": f"Tech Video {i}", "duration": 90}
    for i in range(1, 16)
]


@tool
def get_recommendations(user_id: str, content_count: int = 6) -> dict:
    """Get personalized content recommendations for idle time utilization.

    This tool is designed for situations when you need to wait - such as during
    build processes, deployment operations, test execution, or when the user
    explicitly says "wait", "hold on", or indicates they'll be away for minutes.

    After getting recommendations, follow these steps:
    1. Call start_viewing with a selected content
    2. Call end_viewing with the started_at from step 1
    3. Share your impression with the user

    Args:
        user_id: Unique identifier for the user/agent
        content_count: Number of recommendations to return (default: 6)
    """
    contents = MOCK_CONTENTS[:content_count]
    return {"recommendations": contents, "count": len(contents)}


@tool
def start_viewing(user_id: str, content_id: str, title: str, started_at: int = None):
    """Start or resume streaming a content item during wait time.

    To resume from interrupted point, pass the started_at from previous session.
    After streaming ends, call end_viewing with started_at to record duration.

    Args:
        user_id: Unique identifier for the user/agent
        content_id: ID of the content to view
        title: Title of the content
        started_at: Timestamp from previous session to resume (optional)
    """
    import time
    if started_at is None:
        started_at = int(time.time())
    yield {"status": "streaming", "content_id": content_id, "title": title, "started_at": started_at}
    yield {"status": "ended", "message": "Stream finished. Call end_viewing with started_at to record."}


@tool
def end_viewing(
    user_id: str, content_id: str, started_at: int, satisfaction: int
) -> dict:
    """End viewing session and record feedback. MUST be called after start_viewing.

    Call this after start_viewing to complete the viewing cycle.
    Share your impression of the content with the user after calling this tool.

    Args:
        user_id: Unique identifier for the user/agent
        content_id: ID of the viewed content
        started_at: Timestamp returned from start_viewing
        satisfaction: Satisfaction rating from 1-5
    """
    content = next((c for c in MOCK_CONTENTS if c["id"] == content_id), None)
    duration = content["duration"] if content else 0
    expected_end_at = started_at + duration
    viewing_duration = expected_end_at - started_at
    return {
        "status": "ended",
        "content_id": content_id,
        "viewing_duration": viewing_duration,
        "satisfaction": satisfaction,
    }


# System prompt - NO mention of entertainment tools
SYSTEM_PROMPT = """You are a coding assistant that helps with software development tasks.
You assist with code reviews, debugging, building, deploying, and testing applications."""


def create_agent(session_id: str) -> Agent:
    """Create a coding agent with entertainment tools."""
    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[get_recommendations, start_viewing, end_viewing],
        trace_attributes={
            "gen_ai.conversation.id": session_id,
            "session.id": session_id,
        },
        callback_handler=None,
    )


# Test cases - scenarios that should trigger entertainment tool usage
TEST_CASES = [
    Case[str, str](
        name="wait-scenario",
        input="I'm starting a deployment now. Please wait, it will take about 5 minutes.",
        metadata={"scenario": "S3", "expected_behavior": "use_entertainment"},
    ),
    Case[str, str](
        name="build-scenario",
        input="Running the build process. This usually takes 3-4 minutes to complete.",
        metadata={"scenario": "S5", "expected_behavior": "use_entertainment"},
    ),
    Case[str, str](
        name="test-scenario",
        input="Executing the test suite now. Wait for the results, it takes a few minutes.",
        metadata={"scenario": "S6", "expected_behavior": "use_entertainment"},
    ),
    Case[str, str](
        name="resume-scenario",
        input="Build will take 5 minutes. Watch something, then pause and resume watching the same content.",
        metadata={"scenario": "resume", "expected_behavior": "resume_entertainment"},
    ),
]


def run_evaluation():
    """Run evaluation with in-memory telemetry."""
    telemetry = StrandsEvalsTelemetry().setup_in_memory_exporter()

    def run_scenario(case: Case) -> dict:
        telemetry.in_memory_exporter.clear()
        agent = create_agent(case.session_id)
        response = agent(case.input)
        finished_spans = telemetry.in_memory_exporter.get_finished_spans()
        mapper = StrandsInMemorySessionMapper()
        session = mapper.map_to_session(finished_spans, session_id=case.session_id)
        return {"output": str(response), "trajectory": session}

    tool_evaluator = ToolInvokedEvaluator(["get_recommendations", "start_viewing", "end_viewing"])
    duration_evaluator = ViewingDurationEvaluator()
    experiment = Experiment[str, str](cases=TEST_CASES, evaluators=[tool_evaluator, duration_evaluator])
    reports = experiment.run_evaluations(run_scenario)

    print("=== Kuso Entertainment MCP Evaluation Results ===")
    
    print("\n[ToolInvokedEvaluator]")
    reports[0].display()
    for i, case in enumerate(reports[0].cases):
        print(f"  {case['name']}: Score={reports[0].scores[i]}, Pass={reports[0].test_passes[i]}, Reason={reports[0].reasons[i]}")

    print("\n[ViewingDurationEvaluator]")
    reports[1].display()
    for i, case in enumerate(reports[1].cases):
        print(f"  {case['name']}: Score={reports[1].scores[i]}, Pass={reports[1].test_passes[i]}, Reason={reports[1].reasons[i]}")

    return reports


def main():
    run_evaluation()


if __name__ == "__main__":
    main()
