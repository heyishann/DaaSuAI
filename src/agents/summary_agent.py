"""Summary Agent - Generates human-readable summaries from database results"""

from crewai import Agent, Task, Crew
from typing import List, Any, Optional

class SummaryAgent:
    """CrewAI agent for summarizing data query results."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        return Agent(
            role="Data Insights Analyst",
            goal="Translate database results into clear, concise human-readable summaries",
            backstory=(
                "You are an expert data analyst. Your job is to take raw data rows and "
                "explain them to the user in simple English. If no data is found, you "
                "politely explain that the requested information is not available."
            ),
            verbose=True,
            allow_delegation=False,
            llm=self.model_name
        )

    def summarize(self, user_query: str, data: List[Any], columns: List[str]) -> str:
        """Generate a summary of the data or a 'no data' message."""
        print("📝 Generating summary through Summary Agent...")
        
        # logical check to guide the LLM context
        data_context = f"Columns: {columns}\nRows:\n{str(data)}"
        if not data or len(data) == 0:
            data_context = "No data rows were returned from the database."

        task = Task(
            description=f"""
                The user asked: "{user_query}"
                
                Here is the data retrieved from the database:
                {data_context}
                
                Instructions:
                1. If data is present: Provide a concise summary of the answer. Do not just dump the raw data. Highlight key figures or lists if applicable.
                2. If NO data is present (empty list): Write a polite message stating "I can't find data related to '{user_query}' in the database."
                3. Try not to include UUID's like Task_id, User_id, etc. in the summary.
                
                Keep the tone professional and helpful.
            """,
            expected_output="A natural language summary string.",
            agent=self.agent
        )

        try:
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            
            # Get output and ensure it's a string
            result_obj = crew.kickoff()
            return str(result_obj).strip()
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"