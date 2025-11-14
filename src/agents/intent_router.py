"""Intent Router Agent - Classifies whether a user query requires database access"""

from crewai import Agent, Task, Crew, LLM
from typing import Dict, Any, Optional
import json

from ..core.settings import get_settings


class IntentRouterAgent:
    """CrewAI agent that decides if a user query should hit the database pipeline."""

    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.settings = get_settings()
        self.model_name = model_name
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        llm = LLM(
            model=self.settings.llm_model,
            api_key=self.settings.openai_api_key,
            temperature=0.6,
        )

        return Agent(
            role="Intent Classification Specialist",
            goal="Decide whether a user query needs database access or general knowledge",
            backstory="""You specialize in routing natural language requests to the correct workflow.
            You are excellent at identifying when a prompt refers to structured business data that
            must be fetched from the SQL database versus when the user just needs a general answer.""",
            verbose=False,
            allow_delegation=False,
            llm=llm,
        )

    def classify_query(
        self, user_query: str, additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Classify whether the incoming query is database related."""
        context_section = ""
        if additional_context:
            context_section = f"\nAdditional Context: {additional_context}"

        task = Task(
            description=f"""
Determine if the user question requires querying a structured SQL database or not.
Return ONLY a JSON object with the following fields:
{{
  "is_database_query": true or false,
  "intent_category": "database" or "general",
  "confidence": number between 0 and 1,
  "reason": "short explanation (max 2 sentences)"
}}

Database queries usually:
- Mention metrics, counts, tables, reports, analytics, dashboards, organization IDs, business IDs, or historical company data.
- Require up-to-date business information only available in the SQL database.

General queries usually:
- Ask for definitions, how-to instructions, opinions, greetings, jokes or any answer that does not depend on company data.
- Ask about the application itself, capabilities, troubleshooting, or other non-data topics.

User Query: {user_query}{context_section}
""",
            expected_output="JSON classification result",
            agent=self.agent,
        )

        crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
        result = crew.kickoff()
        return self._parse_result(str(result))

    def _parse_result(self, result: str) -> Dict[str, Any]:
        """Extract JSON payload from the agent's response."""
        try:
            start_idx = result.find("{")
            end_idx = result.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_payload = result[start_idx:end_idx]
                data = json.loads(json_payload)
                return {
                    "is_database_query": bool(data.get("is_database_query")),
                    "intent_category": data.get("intent_category", "database"
                                               if data.get("is_database_query") else "general"),
                    "confidence": float(data.get("confidence", 0.5)),
                    "reason": data.get("reason", "").strip() or "No reason provided.",
                    "raw_response": result,
                }
        except Exception:
            pass

        # Fallback heuristic: assume database query if unsure
        lowered = result.lower()
        fallback_is_db = "database" in lowered or "sql" in lowered
        return {
            "is_database_query": fallback_is_db,
            "intent_category": "database" if fallback_is_db else "general",
            "confidence": 0.3,
            "reason": "Unable to parse classifier response; default routing applied.",
            "raw_response": result,
        }


