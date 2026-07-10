from enum import Enum

class WorkflowOperation(str, Enum):
    INGEST = "ingest"
    BACKLOG = "backlog"
    GENERATE_SCENARIOS = "generate_scenarios"
    APPROVE_SCENARIO = "approve_scenario"
    GENERATE_TESTCASES = "generate_testcases"
    APPROVE_TESTCASE = "approve_testcase"
    GENERATE_PLAYWRIGHT = "generate_playwright"
    EXECUTE = "execute"
    GENERATE_REPORT = "generate_report"
