"""Query Validator Agent - Validates SQL queries for safety and correctness"""

from crewai import Agent, Task, Crew
from typing import Dict, List, Any
import re
import sqlparse


class QueryValidatorAgent:
    """CrewAI agent for validating SQL queries."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.agent = self._create_agent()
        
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent for query validation."""
        return Agent(
            role="SQL Query Validator",
            goal="Validate SQL queries for safety, correctness, and adherence to business rules",
            backstory="""You are a database security expert with deep knowledge of MySQL.
            You specialize in identifying potentially harmful queries, performance issues, 
            and ensuring queries follow proper business logic and security practices.""",
            verbose=True,
            allow_delegation=False,
            llm=self.model_name
        )
    
    def validate_query(self, sql_query: str, business_id: str) -> Dict[str, Any]:
        """Validate a SQL query for safety and correctness."""
        
        # First, do basic syntax and safety checks
        basic_validation = self._basic_validation(sql_query, business_id)
        
        if not basic_validation["is_valid"]:
            return basic_validation
        
        # Then use AI agent for deeper validation
        task = Task(
            description=f"""
            Validate the following SQL query for Organization system:
            
            SQL Query:
            {sql_query}
            
            Organization ID: {business_id}
            
            Check for:
            1. Proper Organization ID filtering (should use o.id = '{business_id}')
            2. Correct table joins and relationships
            3. Adherence to schema conventions
            4. Logical correctness of the query
            
            Return a JSON response with:
            {{
                "is_valid": true/false,
                "errors": ["list of errors if any"],
                "warnings": ["list of warnings if any"],
                "suggestions": ["list of optimization suggestions"],
                "confidence_score": 0.0-1.0
            }}
            """,
            expected_output="JSON validation result with detailed analysis",
            agent=self.agent
        )
        
        # Create a crew to execute the task
        crew = Crew(
            agents=[self.agent],
            tasks=[task],
            verbose=False
        )
        
        result = crew.kickoff()
        
        try:
            # Parse the AI response and combine with basic validation
            ai_validation = self._parse_validation_result(str(result))
            return self._combine_validations(basic_validation, ai_validation)
        except Exception as e:
            return {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "suggestions": [],
                "confidence_score": 0.0
            }
    
    def _basic_validation(self, sql_query: str, business_id: str) -> Dict[str, Any]:
        """Perform basic SQL validation checks."""
        errors = []
        warnings = []
        
        # Check for dangerous SQL commands as standalone statements (not as part of column names)
        dangerous_commands = [
            r"\\bDROP\\b",
            r"\\bDELETE\\b",
            r"\\bTRUNCATE\\b",
            r"\\bALTER\\b",
            r"\\bCREATE\\b",
            r"\\bINSERT\\b",
            r"\\bUPDATE\\b"
        ]
        # Only match if these appear as commands (start of line or after semicolon, ignoring case)
        for pattern in dangerous_commands:
            if re.search(rf"(^|;)\\s*{pattern}", sql_query, re.IGNORECASE):
                errors.append(f"Potentially dangerous SQL command detected: {pattern.replace('\\\\b','')}")
        
        # Check for business ID filtering
        if business_id not in sql_query:
            errors.append("Query must include Organization ID filtering")
        
        # Check for proper UUID filtering pattern
        # uuid_pattern = r"vl\.uuid\s*=\s*['\"]" + re.escape(business_id) + r"['\"]"
        # if not re.search(uuid_pattern, sql_query, re.IGNORECASE):
        #     warnings.append("Business ID filtering should use vl.uuid = 'business_id' pattern")
        
        # Basic syntax check
        try:
            parsed = sqlparse.parse(sql_query)
            if not parsed:
                errors.append("Invalid SQL syntax")
        except Exception as e:
            errors.append(f"SQL parsing error: {str(e)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": [],
            "confidence_score": 1.0 if len(errors) == 0 else 0.0
        }
    
    def _parse_validation_result(self, result: str) -> Dict[str, Any]:
        """Parse the AI agent's validation result."""
        import json
        
        # Try to extract JSON from the result
        try:
            # Look for JSON block
            start_idx = result.find('{')
            end_idx = result.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = result[start_idx:end_idx]
                return json.loads(json_str)
        except:
            pass
        
        # Fallback: create a basic result
        return {
            "is_valid": "valid" in result.lower() and "error" not in result.lower(),
            "errors": [],
            "warnings": [],
            "suggestions": [],
            "confidence_score": 0.5
        }
    
    def _combine_validations(self, basic: Dict[str, Any], ai: Dict[str, Any]) -> Dict[str, Any]:
        """Combine basic and AI validation results."""
        return {
            "is_valid": basic["is_valid"] and ai["is_valid"],
            "errors": basic["errors"] + ai.get("errors", []),
            "warnings": basic["warnings"] + ai.get("warnings", []),
            "suggestions": basic["suggestions"] + ai.get("suggestions", []),
            "confidence_score": min(basic["confidence_score"], ai.get("confidence_score", 0.5))
        }