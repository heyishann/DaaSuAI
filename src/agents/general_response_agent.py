"""General Response Agent - Handles non-database user queries"""

from crewai import Agent, Task, Crew, LLM
from typing import Dict, Any, Optional

from ..core.settings import get_settings


class GeneralResponseAgent:
    """CrewAI agent that answers non-database related user questions."""

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
            role="General Support Assistant",
            goal="Answer user questions that do not require database access.",
            backstory="""You are a friendly assistant who helps users with general knowledge,
            platform instructions, troubleshooting tips, and other non-database requests.
            When you do not know something, you admit it gracefully and avoid fabricating data.""",
            verbose=False,
            allow_delegation=False,
            llm=llm,
        )

    def answer_query(
        self, user_query: str, additional_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a conversational answer for non-database questions."""

        context_section = ""
        if additional_context:
            context_section = f"\nAdditional Context: {additional_context}"

        task = Task(
            description=f"""
Provide a clear, helpful answer to the user's question below.
- Do NOT mention database operations or SQL.
- If the question cannot be answered confidently, politely explain the limitation.
- Keep the response under 200 words.

User Query: {user_query}{context_section}
""",
            expected_output="Conversational assistant style response",
            agent=self.agent,
        )

        try:
            crew = Crew(agents=[self.agent], tasks=[task], verbose=False)
            answer = crew.kickoff()
            return {
                "success": True,
                "answer": str(answer).strip(),
                "source": "general_response_agent",
            }
        except Exception as exc:
            return {
                "success": False,
                "answer": "I encountered an issue while trying to answer that. Please try again.",
                "source": "general_response_agent",
                "error": str(exc),
            }


