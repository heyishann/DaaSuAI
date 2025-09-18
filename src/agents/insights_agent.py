"""Insights Agent - Converts DataFrame data into narrative insights"""

from crewai import Agent, Task, Crew
from typing import Dict, Any, Optional
import pandas as pd

class InsightsAgent:
    """CrewAI agent for generating narrative insights from data."""
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.agent = self._create_agent()

    def _create_agent(self) -> Agent:
        return Agent(
            role="Business Insights Specialist",
            goal="Convert business data into actionable narrative insights",
            backstory="""You are an expert in business analytics and storytelling. You analyze data and communicate key findings, trends and anomalies, and amaze others by your insights results.""",
            verbose=True,
            allow_delegation=False,
            llm=self.model_name
        )

    def generate_insights(self, df: pd.DataFrame, user_query: str) -> Dict[str, Any]:
        """Generate narrative insights from a DataFrame."""
        if df.empty:
            return {
                "success": False,
                "error": "No data available for insights.",
                "insights": ""
            }
        # Prepare a sample for context
        sample = df.head(10).to_dict()
        columns = list(df.columns)
        row_count = len(df)
        task = Task(
            description=f"""
            You are a business analytics expert. Analyze the following business data and provide a concise, business-relevant narrative insight:
            User Query: {user_query}
            Columns: {columns}
            Data Sample: {sample}
            Row Count: {row_count}
            Focus on:
            - Key trends and patterns
            - Anomalies and outliers
            - Direct comparisons (e.g., new vs. existing staff, month-over-month changes)
            Use direct, clear language (e.g., "The new stylist onboarded in June is underperforming compared to team average.").
            Respond in 2-5 sentences, referencing specific time periods, groups, or metrics when possible.
            """,
            expected_output="Narrative insight text",
            agent=self.agent
        )
        try:
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            insight = crew.kickoff()
            return {
                "success": True,
                "insights": str(insight)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Insight generation failed: {str(e)}",
                "insights": ""
            }
