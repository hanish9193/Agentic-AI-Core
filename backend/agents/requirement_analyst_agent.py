from backend.agents.base import BaseAgent
from backend.models.state import WorkflowState
from backend.services.llm import LLMService
from backend.repository.project_repository import get_project_repository
from pydantic import BaseModel, Field
import re

class RequirementEnrichment(BaseModel):
    title: str = Field(description="A clean, concise title for the requirement (3-8 words)")
    description: str = Field(description="Enriched, formatted description. Clean up formatting and resolve any obvious ambiguities.")
    priority: str = Field(description="Must be one of: low, medium, high")
    business_domain: str = Field(description="Must be a capitalized single word business domain (e.g. Finance, Banking, Auth, Billing, General)")

class RequirementAnalystAgent(BaseAgent):
    name = "Requirement Analyst Agent"

    def __init__(self, llm_service: LLMService | None = None):
        self.llm_service = llm_service or LLMService()
        self.repo = get_project_repository()

    def run(self, state: WorkflowState) -> WorkflowState:
        if not state.requirement:
            raise ValueError(f"{self.name} requires state.requirement to be set")

        state.add_log(f"{self.name} started")
        req = state.requirement

        # Perform deterministic parsing first as baseline
        priority = "medium"
        if any(k in req.description.lower() for k in ["high", "critical", "urgent", "must"]):
            priority = "high"
        elif any(k in req.description.lower() for k in ["low", "minor", "nice to have"]):
            priority = "low"

        business_domain = "general"
        for k in ["banking", "finance", "auth", "login", "profile", "billing", "payment", "checkout", "search", "upload", "insurance", "retail", "healthcare"]:
            if k in req.description.lower():
                business_domain = k.capitalize()
                break

        title = req.title

        # Check if LLM enrichment is requested (e.g. via configuration or config/override)
        # Or if fields are left as default placeholder values
        needs_llm = (
            "REQ-MANUAL" in req.title or
            req.title == "Requirement Block" or
            "general" in business_domain.lower()
        )

        if needs_llm:
            state.add_log(f"{self.name}: Invoking LLM for metadata enrichment and ambiguity resolution.")
            prompt = (
                "You are an expert Business Analyst. Enrich the following requirement by cleaning up "
                "its formatting, generating a clean and concise title, extracting the priority, "
                "and identifying its specific business domain.\n\n"
                f"Raw Title: {req.title}\n"
                f"Raw Description: {req.description}\n"
            )
            try:
                enrichment = self.llm_service.structured_generate(
                    user=prompt,
                    response_model=RequirementEnrichment
                )
                
                # Re-create the Requirement object with enriched values
                from backend.models.requirement import Requirement
                enriched_req = Requirement(
                    id=req.id,
                    title=enrichment.title,
                    description=enrichment.description,
                    source=req.source,
                    uploaded_at=req.uploaded_at,
                    original_filename=req.original_filename,
                    requirement_id=req.requirement_id,
                    requirement_title=enrichment.title
                )
                state.requirement = enriched_req
                priority = enrichment.priority
                business_domain = enrichment.business_domain
                state.add_log(f"{self.name}: LLM enrichment complete (Domain: {business_domain}, Priority: {priority})")
            except Exception as e:
                state.add_log(f"{self.name}: LLM enrichment failed, falling back to deterministic parser: {e}")
        else:
            state.add_log(f"{self.name}: Using deterministic parser metadata (Domain: {business_domain}, Priority: {priority})")

        # Persist the finalized requirement to the project repository
        self.repo.save_requirement(state.requirement, priority=priority, business_domain=business_domain)
        state.add_log(f"{self.name}: Finalized requirement persisted successfully.")

        return state
