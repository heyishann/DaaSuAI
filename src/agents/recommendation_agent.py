"""Recommendation Agent - Suggests business actions using rules and ML/AI"""

from crewai import Agent, Task, Crew
from crewai.tools import BaseTool
from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from crewai.tools import tool

class RecommendationAgent:

    """CrewAI agent for generating actionable business recommendations."""
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.agent = self._create_agent()


    def _create_agent(self) -> Agent:
        return Agent(
            role="Business Recommendation Specialist",
            goal="Suggest effective business actions using rules and ML/AI",
            backstory=(
                "You are an expert in business strategy, customer retention, and "
                "operational efficiency. You use data, rules, and AI/ML to recommend "
                "actions that drive business growth and solve problems."
            ),
            verbose=True,
            allow_delegation=False,
            llm=self.model_name,
        )
        

    def generate_recommendations(self, df: pd.DataFrame, insights: str, user_query: str) -> Dict[str, Any]:
        """Generate actionable recommendations from a DataFrame, optionally using advanced revenue forecasting."""
        if df.empty:
            return {
                "success": False,
                "error": "No data available for recommendations.",
                "recommendations": ""
            }
        sample = df.head(10).to_dict(orient="records")
        columns = list(df.columns)
        row_count = len(df)


        task = Task(
            description=f"""
            You are a business recommendation expert. Analyze the following business data and suggest 1-3 actionable recommendations:
            User Query: {user_query}
            Columns: {columns}
            Some insight: {insights}
            Data Sample: {sample}
            Row Count: {row_count}
            Use a mix of business rules, ML/AI reasoning, and available tools if relevant.
            Focus on actions that drive growth, retention, or solve business problems.
            Amaze others by your recommendations which are beyond imagination.
            Respond in 1-3 bullet points, e.g., "Offer discounts to bring repeat customers back".
            """,
            expected_output="List of actionable recommendations",
            agent=self.agent
        )
        try:
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            recs = crew.kickoff()
            return {
                "success": True,
                "recommendations": str(recs)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Recommendation generation failed: {str(e)}",
                "recommendations": ""
            }
