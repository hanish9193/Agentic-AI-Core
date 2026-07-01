from backend.config.settings import get_settings

settings = get_settings()

print("=" * 40)
print("Application Configuration")
print("=" * 40)

print(f"Environment : {settings.app_env}")
print(f"Log Level   : {settings.log_level}")

print("\nLLM")
print(f"Provider    : {settings.llm.provider}")
print(f"Model       : {settings.llm.model}")
print(f"Temperature : {settings.llm.temperature}")

print("\nWorkflow")
print(f"Mode        : {settings.workflow.mode}")
print(f"Human Review: {settings.workflow.human_review_enabled}")
print(f"Threshold   : {settings.workflow.evaluation_threshold}")

print("\nAgents")
print(settings.agents)

print("\nBrowser")
print(f"Browser     : {settings.browser.type}")
print(f"Headless    : {settings.browser.headless}")

print("\nRAG")
print(f"Enabled     : {settings.rag.enabled}")
print(f"Vector DB   : {settings.rag.vector_db_provider}")