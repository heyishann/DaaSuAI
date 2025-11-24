"""Query Generator Agent - Converts natural language to SQL queries using CrewAI"""

from crewai import Agent, Task, Crew, LLM
from typing import Any, Optional, Dict
import os
from pathlib import Path
from ..core.settings import get_settings


class QueryGeneratorAgent:
    """CrewAI agent for generating SQL queries from natural language."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.settings = get_settings()
        self.model_name = model_name
        self.agent = self._create_agent()
        
    def _load_prompt(self) -> str:
        """Load the SQL generation prompt."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "query_generation_prompt.md"
        
        try:
            with open(prompt_path, 'r') as f:
                prompt_content = f.read()
                print(f" Loaded SQL generation prompt ({len(prompt_content)} characters)")
                return prompt_content
        except FileNotFoundError:
            print(f" SQL prompt file not found at: {prompt_path}")
            return "You are an SQL query generator. Generate MySQL queries from natural language."
    
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent for query generation."""
        prompt = self._load_prompt()
        
        # Create LLM with proper configuration
        model_to_use = self.settings.llm_model
        print(f" Using LLM model: {model_to_use}")
        print(f" OpenAI API Key configured: {'Yes' if self.settings.openai_api_key else 'No'}")
        
        llm = LLM(
            model=model_to_use,
            api_key=self.settings.openai_api_key,
            temperature=0.6
        )
        
        return Agent(
            role="SQL Query Generator",
            goal="Generate accurate MySQL queries from natural language descriptions for an Organization management system",
            backstory=f"""You are an expert SQL developer specializing in business intelligence queries 
            for an organization. You understand the intricacies of employees performance,
            process tracking and tasks management systems.
            
            IMPORTANT: Follow these SQL generation rules exactly:
            {prompt}""",
            verbose=True,
            allow_delegation=False,
            llm=llm
        )
    
    def generate_query(self, user_query: str, business_id: str, additional_context: Optional[dict] = None) -> str:
        """Generate SQL query from natural language description."""
        
        context = f"""
        Organization ID: {business_id}
        User Query: {user_query}
        """
        
        if additional_context:
            context += f"\nAdditional Context: {additional_context}"
        
        task = Task(
            description=f"""
            Generate a MySQL query for the following request:

            {context}

            Requirements:

            ### 1. Context & Ambiguity Resolution (CRITICAL)
            - **Identify the Subject:** If the current request contains ambiguous pronouns (e.g., "List them", "Show details", "Which ones?", "Show me"), you MUST analyze the provided context to identify the **Active Entity/Table** from the previous turn.
            - **Carry Over Logic:** Apply the current action (e.g., "List", "Select") to that previously identified entity.
            - **Example:**
                - Context: "Total number of projects" (Subject = Projects)
                - Current Request: "List them"
                - Resulting Logic: Query the **Projects** table, not Users or Labours.
            - **Do not guess:** If the context is about "Projects", "them" always refers to Projects.

            ### 2. Core Rules
            - **Schema Adherence:** Strictly follow all table names, column names, data types, and foreign key relationships defined in the provided database schema.
            - **Strict Output Format:** Return **only** the final SQL query. Enclose the query in a single markdown code block (```sql ... ```). Do not add any explanations, notes, or text before or after the query.
            - **No Wildcards in SELECT:** **Never use SELECT ***. You must explicitly list all columns required to answer the user's request (e.g., id, name, status).
            - **Readable Aliases:** Use clear and consistent table aliases (e.g., `p` for projects, `u` for users) for all tables, especially in JOINs.
            - **Aggregation Safety:** When using aggregate functions (like SUM, COUNT, AVG), always wrap the function in COALESCE to ensure 0 is returned instead of NULL for empty sets.
                - Example: `COALESCE(SUM(t.hours), 0) AS total_hours`
            - **Data Type Safety:** Do not assume a string is an integer or vice versa. "Pankaj" is a name, not an ID.
            - **UNION Usage:** Use `UNION` if the user asks two distinct questions in one prompt that require combined results.

            ### 3. Filtering Logic (WHERE Clauses)
            - **Mandatory Organization Filter:** **Every query must** include a WHERE clause to filter data by the organization ID. Use the exact placeholder `{business_id}`.
                - Example: `WHERE o.id = '{business_id}'`
            - **Name Filtering (Dynamic & Case-Insensitive):**
                - When filtering by name (Project, User, Labour), use `LOWER(column) LIKE LOWER('%value%')`.
                - Replace spaces in the search string with `%`.
                - **Single-word Example:** `WHERE LOWER(u.name) LIKE LOWER('%pankaj%')`
                - **Multi-word Example:** `WHERE LOWER(p.name) LIKE LOWER('%green%heritage%resort%')`

            ### 4. Specific Business Logic
            - **Attendance Query Disambiguation:**
                - **Scenario 1 (Labour):** If the request explicitly mentions "labour" (e.g., "attendance of labour Pankaj"), use **labour-related** tables.
                - **Scenario 2 (User):** If "labour" is NOT mentioned (e.g., "attendance of Pankaj"), query **user-related** tables by default.
                - **Column Rule:** For attendance checks, always use the `check_in` column, not the `date` column.
            """,
            expected_output="A clean, well-formatted MySQL query",
            agent=self.agent
        )
        
        # Create a crew to execute the task
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=False
        )
        
        result = crew.kickoff()
        print(result)
        return self._clean_sql_output(str(result))
    
    def generate_query_with_feedback(self, user_query: str, business_id: str, 
                                   feedback_context: Dict[str, Any],
                                   additional_context: Optional[dict] = None) -> str:
        """Generate SQL query incorporating feedback from validation."""
        
        context = f"""
        Organization ID: {business_id}
        User Query: {user_query}
        """
        
        if additional_context:
            context += f"\nAdditional Context: {additional_context}"
        
        # Add feedback context
        feedback_info = f"""
        
        IMPORTANT - QUERY IMPROVEMENT NEEDED:
        This is attempt #{feedback_context['attempt_number']} to generate a better query.
        
        Previous Query (NEEDS IMPROVEMENT):
        {feedback_context['previous_query']}
        
        Validation Feedback:
        """
        
        if feedback_context['validation_errors']:
            feedback_info += f"\n ERRORS TO FIX:\n"
            for error in feedback_context['validation_errors']:
                feedback_info += f"- {error}\n"
        
        if feedback_context['validation_warnings']:
            feedback_info += f"\n WARNINGS TO ADDRESS:\n"
            for warning in feedback_context['validation_warnings']:
                feedback_info += f"- {warning}\n"
                
        if feedback_context['validation_suggestions']:
            feedback_info += f"\n SUGGESTIONS TO IMPLEMENT:\n"
            for suggestion in feedback_context['validation_suggestions']:
                feedback_info += f"- {suggestion}\n"
        
        feedback_info += f"""
        
        INSTRUCTIONS FOR IMPROVEMENT:
        1. Address ALL errors mentioned above
        2. Follow all suggestions to improve performance and correctness
        3. Keep the original intent of the query but make it better
        4. Generate a NEW, IMPROVED query - don't just copy the previous one
        5. Focus especially on performance, safety, and correctness
        6. Don't remove LIKE clause from the sql query, always use LIKE cluase for the name and whenever needed.
        """
        
        context += feedback_info
        
        task = Task(
            description=f"""
            Generate an IMPROVED MySQL query based on the feedback provided:
            
            {context}
            
            Requirements:
            1. Use the organization_id '{business_id}' to filter data (use o.id = '{business_id}')
            2. Follow all the schema rules and conventions provided
            3. Address ALL validation errors and warnings from the feedback
            4. Implement the suggestions provided
            5. Return only the SQL query, properly formatted
            6. Include appropriate JOINs and WHERE clauses
            7. Use COALESCE for NULL safety in aggregations
            8. Optimize for performance based on the feedback
            9. Don't remove LIKE clause from the sql query, always use LIKE cluase for the name and whenever needed.
            """,
            expected_output="A clean, well-formatted, improved MySQL query",
            agent=self.agent
        )
        
        # Create a crew to execute the task
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=False
        )
        
        result = crew.kickoff()
        return self._clean_sql_output(str(result))
    
    def _clean_sql_output(self, output: str) -> str:
        """Clean and format the SQL output."""
        # Remove markdown code blocks if present
        if "```sql" in output:
            start = output.find("```sql") + 6
            end = output.find("```", start)
            if end != -1:
                output = output[start:end]
        elif "```" in output:
            start = output.find("```") + 3
            end = output.find("```", start)
            if end != -1:
                output = output[start:end]
        
        print(output.strip())
        return output.strip()