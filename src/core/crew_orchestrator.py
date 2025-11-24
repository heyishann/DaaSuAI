"""CrewAI Orchestrator - Coordinates all agents in the SQL generation pipeline"""

from crewai import Crew, Process
from typing import Dict, Any, Optional
import asyncio
from ..agents.query_generator import QueryGeneratorAgent
from ..agents.query_validator import QueryValidatorAgent
from ..agents.query_executor import QueryExecutorAgent
from ..agents.intent_router import IntentRouterAgent
from ..agents.general_response_agent import GeneralResponseAgent
from ..core.conversation_store import ConversationStore
# from ..agents.data_visualizer import DataVisualizerAgent


class SQLGenerationCrew:
    """Orchestrates the SQL generation, validation, execution, and visualization pipeline."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.intent_router = IntentRouterAgent(model_name)
        self.query_generator = QueryGeneratorAgent(model_name)
        self.query_validator = QueryValidatorAgent(model_name)
        self.query_executor = QueryExecutorAgent(model_name)
        self.general_responder = GeneralResponseAgent(model_name)
        self.conversation_store: Optional[ConversationStore] = None
        # self.data_visualizer = DataVisualizerAgent(model_name)
        
    def set_mcp_client(self, db_client):
        """Set the database client for database operations."""
        self.query_executor.set_mcp_client(db_client)
        self.conversation_store = ConversationStore(db_client)
    
    async def process_user_query(self, user_query: str, business_id: str,
                                 session_id: Optional[str] = None,
                                 additional_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a complete user query through the entire pipeline."""
        
        pipeline_result = {
            "user_query": user_query,
            "organization_id": business_id,
            "steps": {
                "context": {},
                "routing": {},
                "query_generation": {},
                "query_validation": {},
                "query_execution": {},
                "general_response": {},
                # "data_visualization": {}
            },
            "final_result": {}
        }
        
        try:
            conversation_context = None
            if session_id and self.conversation_store:
                conversation_context = await self.conversation_store.fetch_last_entry(session_id)
                pipeline_result["steps"]["context"] = {
                    "session_id": session_id,
                    "previous_message": conversation_context
                }

            enriched_context = self._merge_context(additional_context, conversation_context)

            # Step 0: route the user query
            routing_decision = self.intent_router.classify_query(
                user_query, enriched_context
            )
            pipeline_result["steps"]["routing"] = routing_decision

            if not routing_decision.get("is_database_query", True):
                general_response = self.general_responder.answer_query(
                    user_query, enriched_context
                )
                pipeline_result["steps"]["general_response"] = general_response
                pipeline_result["final_result"] = {
                    "success": general_response.get("success", False),
                    "response_type": "general_answer",
                    "answer": general_response.get("answer"),
                    "sql_query": None,
                    "data": None,
                    "columns": None,
                    "row_count": None,
                    "execution_time": None,
                    "validation_info": None,
                    "routing_decision": routing_decision,
                    "error": general_response.get("error"),
                }
                await self._persist_conversation(session_id, user_query, pipeline_result["final_result"])
                return pipeline_result

            # Step 1: Generate SQL query with feedback loop
            sql_query, generation_attempts = await self._generate_query_with_feedback(
                user_query, business_id, enriched_context
            )
            
            # Store generation details
            pipeline_result["steps"]["query_generation"] = {
                "success": True,
                "sql_query": sql_query,
                "attempts": generation_attempts,
                "feedback_used": len(generation_attempts) > 1
            }
            
            # Get final validation result
            validation_result = self.query_validator.validate_query(sql_query, business_id)
            pipeline_result["steps"]["query_validation"] = validation_result
            print(pipeline_result)
            # Step 3: Execute the query
            print("⚙️ Executing SQL query...")
            execution_result = await self.query_executor.execute_query(sql_query)
            pipeline_result["steps"]["query_execution"] = execution_result
            if not execution_result["success"]:
                return {
                    **pipeline_result,
                    "final_result": {
                        "success": False,
                        "error": "Query execution failed",
                        "details": execution_result
                    }
                }
            
            # Step 4: Create visualizations
            # print("📊 Creating visualizations...")
            # visualization_result = self.data_visualizer.visualize_data(
            #     execution_result, user_query
            # )
            # pipeline_result["steps"]["data_visualization"] = visualization_result
            
            # Step 5: Format final response
            # try:
            #     formatted_results = self.query_executor.format_results(execution_result)
            # except Exception as e:
            #     print(f"⚠️ Error formatting results: {e}")
            #     formatted_results = "Results formatting failed. Raw data available."
            
            # Clean data by handling NaN values
            clean_data = self._clean_data_for_json(execution_result["data"])
            
            pipeline_result["final_result"] = {
                "success": True,
                "response_type": "database_query",
                "sql_query": sql_query,
                "data": clean_data,
                "columns": execution_result["columns"],
                "row_count": execution_result["row_count"],
                "execution_time": execution_result["execution_time"],
                "routing_decision": routing_decision,
                # "formatted_summary": formatted_results,
                # "visualizations": visualization_result.get("visualizations", []),
                "validation_info": {
                    "confidence_score": validation_result["confidence_score"],
                    "warnings": validation_result["warnings"],
                    "suggestions": validation_result["suggestions"]
                }
            }
            await self._persist_conversation(session_id, user_query, pipeline_result["final_result"])
            
            return pipeline_result
            
        except Exception as e:
            return {
                **pipeline_result,
                "final_result": {
                    "success": False,
                    "response_type": "database_query",
                    "error": f"Pipeline execution failed: {str(e)}",
                    "details": {"error_type": type(e).__name__},
                    "routing_decision": pipeline_result["steps"].get("routing"),
                }
            }
    
    def get_pipeline_status(self) -> Dict[str, str]:
        """Get the status of all pipeline components."""
        return {
            "intent_router": "active",
            "query_generator": "active",
            "query_validator": "active", 
            "query_executor": "active" if hasattr(self.query_executor, 'mcp_client') and self.query_executor.mcp_client else "no_db_client",
            "general_responder": "active",
            "data_visualizer": "active"
        }
    
    async def validate_setup(self) -> Dict[str, Any]:
        """Validate that all components are properly configured."""
        status = self.get_pipeline_status()
        
        issues = []
        if status["query_executor"] == "no_db_client":
            issues.append("Database client not configured for query execution")
        
        return {
            "is_valid": len(issues) == 0,
            "status": status,
            "issues": issues
        }

    def _merge_context(self, incoming_context: Optional[Dict[str, Any]], previous_message: Optional[Dict[str, Any]]):
        """Combine provided context with the previous conversation turn."""
        if not previous_message:
            return incoming_context

        merged = incoming_context.copy() if incoming_context else {}
        merged["previous_message"] = {
            "user_query": previous_message.get("user_query"),
            "response_type": previous_message.get("response_type"),
            "response_text": previous_message.get("response_text"),
            "sql_query": previous_message.get("sql_query"),
            "metadata": previous_message.get("metadata", {}),
        }
        return merged

    async def _persist_conversation(self, session_id: Optional[str], user_query: str, final_result: Dict[str, Any]):
        """Store the interaction for future context."""
        if not self.conversation_store:
            return

        metadata = {
            "routing_decision": final_result.get("routing_decision"),
            "row_count": final_result.get("row_count"),
            "execution_time": final_result.get("execution_time"),
        }

        await self.conversation_store.save_entry(
            session_id=session_id,
            user_query=user_query,
            final_result=final_result,
            metadata={k: v for k, v in metadata.items() if v is not None},
        )
    
    def _clean_data_for_json(self, data):
        """Clean data by replacing NaN values with None for JSON serialization."""
        import math
        
        if not data:
            return data
        
        clean_data = []
        for row in data:
            clean_row = []
            for cell in row:
                # Handle NaN values (from pandas/numpy)
                if isinstance(cell, float) and math.isnan(cell):
                    clean_row.append(None)
                # Handle None values
                elif cell is None:
                    clean_row.append(None)
                # Handle string 'NaN' 
                elif isinstance(cell, str) and cell.lower() in ['nan', 'null']:
                    clean_row.append(None)
                else:
                    clean_row.append(cell)
            clean_data.append(clean_row)
        
        return clean_data
    
    async def _generate_query_with_feedback(self, user_query: str, business_id: str, 
                                           additional_context: Optional[Dict[str, Any]] = None) -> tuple:
        """Generate SQL query with feedback loop for validation and improvement."""
        
        max_attempts = 3
        attempts = []
        
        for attempt in range(1, max_attempts + 1):
            print(f"🔄 Generating SQL query (attempt {attempt}/{max_attempts})")
            
            # Generate query (with feedback from previous attempts if any)
            feedback_context = None
            if attempts:
                # Get feedback from last validation
                last_attempt = attempts[-1]
                feedback_context = {
                    "previous_query": last_attempt["sql_query"],
                    "validation_errors": last_attempt["validation"]["errors"],
                    "validation_warnings": last_attempt["validation"]["warnings"],
                    "validation_suggestions": last_attempt["validation"]["suggestions"],
                    "attempt_number": attempt
                }
            
            # Generate query
            if feedback_context:
                sql_query = self.query_generator.generate_query_with_feedback(
                    user_query, business_id, feedback_context, additional_context
                )
            else:
                sql_query = self.query_generator.generate_query(
                    user_query, business_id, additional_context
                )
            
            # Validate the query
            print(f"🔍 Validating SQL query (attempt {attempt})")
            validation_result = self.query_validator.validate_query(sql_query, business_id)
            
            # Store this attempt
            attempt_data = {
                "attempt": attempt,
                "sql_query": sql_query,
                "validation": validation_result
            }
            attempts.append(attempt_data)
            
            # Check if we should accept this query
            should_retry = self._should_retry_generation(validation_result, attempt, max_attempts)
            
            if not should_retry:
                print(f"✅ Query accepted after {attempt} attempts")
                break
            else:
                print(f"🔁 Query needs improvement, retrying ({attempt}/{max_attempts})")
        
        # Return the best query (last attempt)
        final_query = attempts[-1]["sql_query"]
        return final_query, attempts
    
    def _should_retry_generation(self, validation_result: Dict[str, Any], attempt: int, max_attempts: int) -> bool:
        """Determine if query generation should be retried based on validation results."""
        
        # Don't retry if we've reached max attempts
        if attempt >= max_attempts:
            return False
        
        # Only retry if query is invalid - if valid, proceed regardless of warnings
        if not validation_result["is_valid"]:
            return True
        
        # Don't retry if query is valid - proceed to next step
        return False