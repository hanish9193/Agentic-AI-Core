from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.services.rag_service import RAGFlowService
from backend.repository.project_repository import get_project_repository

class FeatureInventoryAgent(BaseAgent):
    name = "Feature Inventory Agent"

    def __init__(self, rag_service: RAGFlowService | None = None):
        self.rag_service = rag_service or RAGFlowService()
        self.repo = get_project_repository()

    def run(self, state: WorkflowState) -> WorkflowState:
        if not state.requirement:
            raise ValueError(f"{self.name} requires state.requirement to be set")

        state.add_log(f"{self.name} started")
        req = state.requirement

        if not self.rag_service.is_active():
            state.add_log(f"{self.name}: RAGFlow service is not active or not configured. Skipping feature inventory mapping.")
            return state

        try:
            # Query vector store for related feature contexts
            query = f"Feature capabilities and user scenarios related to: {req.description}"
            context = self.rag_service.retrieve_context(query, top_k=3)

            if context.strip():
                state.add_log(f"{self.name}: Retrieved relevant feature context from RAG dataset.")
                # Save feature mapping report inside the requirement
                new_req = req.model_copy(update={"feature_mapping": context})
                self.repo.save_requirement(new_req)
                state.requirement = new_req
                state.add_log(f"{self.name}: Feature overlap mapped and persisted in requirement metadata.")
            else:
                state.add_log(f"{self.name}: No overlapping features detected in RAG database.")
        except Exception as e:
            # Failure of RAG / knowledge sources must never fail requirement ingestion
            state.add_log(f"{self.name}: Gracefully skipped optional feature mapping after error: {e}")

        return state
