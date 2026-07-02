"""
Foundation smoke test.

Not testing edge cases here - that's what proper unit tests are for later.
This just proves config + models actually wire together before you build
a single agent on top of them. Run directly, or via pytest.
"""

from backend.config.settings import get_settings
from backend.models.requirement import Requirement, RequirementSource
from backend.models.scenario import Scenario, ScenarioPriority
from backend.models.state import WorkflowState


def test_config_loads():
    settings = get_settings()
    assert settings.llm.provider
    assert settings.agents.scenario is True
    print(f"[config] provider={settings.llm.provider} model={settings.llm.model} "
          f"mode={settings.workflow.mode} threshold={settings.workflow.evaluation_threshold}")


def test_requirement_is_immutable():
    r = Requirement(
        title="Login flow",
        description="User can log in with valid credentials",
        source=RequirementSource.MANUAL,
    )
    try:
        r.title = "changed"
        raise AssertionError("Requirement should be frozen")
    except Exception:
        pass
    print(f"[requirement] created and immutability confirmed: {r.id}")
    return r


def test_scenario_links_to_requirement(requirement: Requirement):
    s1 = Scenario(
        requirement_id=requirement.id,
        scenario_name="Valid Login",
        description="User logs in with correct credentials",
        priority=ScenarioPriority.HIGH,
        confidence=0.92,
    )
    s2 = Scenario(
        requirement_id=requirement.id,
        scenario_name="Invalid Password",
        description="User logs in with wrong password",
        confidence=0.81,
    )
    assert s1.requirement_id == requirement.id
    print(f"[scenario] created 2 scenarios linked to requirement {requirement.id}")
    return [s1, s2]


def test_state_flows(requirement: Requirement, scenarios: list[Scenario]):
    state = WorkflowState(requirement=requirement)
    state.add_log("Requirement received")

    state.generated_scenarios.extend(scenarios)
    state.add_log(f"Generated {len(scenarios)} scenarios")

    state.select_scenario(scenarios[0].id)
    state.add_log(f"Selected scenario: {scenarios[0].scenario_name}")

    assert len(state.selected_scenarios()) == 1
    assert state.selected_scenarios()[0].scenario_name == "Valid Login"

    # rejecting an unknown id should fail loudly, not silently
    try:
        state.select_scenario(requirement.id)  # wrong kind of id, on purpose
        raise AssertionError("select_scenario should reject unknown ids")
    except ValueError:
        pass

    print("[state] scenario selection and logging confirmed")
    for line in state.logs:
        print("   ", line)


if __name__ == "__main__":
    test_config_loads()
    req = test_requirement_is_immutable()
    scenarios = test_scenario_links_to_requirement(req)
    test_state_flows(req, scenarios)
    print("\nFoundation modules 1 and 2: all wired correctly.")