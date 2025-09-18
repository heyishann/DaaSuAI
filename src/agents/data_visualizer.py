"""Data Visualizer Agent - Creates visual representations of query results"""

from crewai import Agent, Task, Crew
from typing import Dict, List, Any, Optional
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
import json
import base64
from io import BytesIO
import io


class DataVisualizerAgent:
    """CrewAI agent for creating data visualizations."""
    
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.model_name = model_name
        self.agent = self._create_agent()
        
    def _create_agent(self) -> Agent:
        """Create the CrewAI agent for data visualization."""
        return Agent(
            role="Data Visualization Specialist",
            goal="Create meaningful and insightful visualizations from business data",
            backstory="""You are a data visualization expert who specializes in creating 
            clear, informative charts and graphs for business intelligence. You understand 
            how to choose the right visualization type for different kinds of data and 
            business questions.""",
            verbose=True,
            allow_delegation=False,
            llm=self.model_name
        )
    
    def visualize_data(self, results: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """Create visualizations from query results."""
        
        if not results["success"] or not results["data"]:
            return {
                "success": False,
                "error": "No data to visualize",
                "visualizations": []
            }
        
        # Convert to DataFrame for easier processing
        df = pd.DataFrame(results["data"], columns=results["columns"], index=None)
        # Analyze data and suggest visualization types
        task = Task(
            description=f"""
            Analyze the following data and suggest appropriate visualization types:
            
            User Query: {user_query}
            Columns: {results['columns']}
            Data Sample: {df.head().to_dict() if not df.empty else 'No data'}
            Row Count: {len(df)}
            
            Based on the data structure and user query, suggest:
            1. The most appropriate chart type (bar, line, pie, scatter, etc.)
            2. Which columns should be used for X and Y axes
            3. Any grouping or aggregation needed
            4. Color coding if applicable
            5. Title and labels for the chart
            
            Return a single JSON response with visualization recommendations :
            {{
                "chart_type": "bar|line|pie|scatter|table",
                "x_column": "column_name",
                "y_column" or "y_columns": "column_name", 
                "color_column": "column_name or null",
                "title": "Chart Title",
                "x_label": "X Axis Label",
                "y_label": "Y Axis Label"
            }}
            """,
            expected_output="JSON with visualization recommendations",
            agent=self.agent
        )
        
        try:
            # Create a crew to execute the task
            crew = Crew(
                agents=[self.agent],
                tasks=[task],
                verbose=False
            )
            
            recommendation = crew.kickoff()
            viz_config = self._parse_visualization_config(str(recommendation))
            
            # Create the visualization
            chart = self._create_chart(df, viz_config)
            
            return {
                "success": True,
                "visualizations": [chart],
                "config": viz_config
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Visualization creation failed: {str(e)}",
                "visualizations": []
            }
    
    def _parse_visualization_config(self, recommendation: str) -> Dict[str, Any]:
        """Parse the AI recommendation into a configuration."""
        
        try:
            # Try to extract JSON from the recommendation
            start_idx = recommendation.find('{')
            end_idx = recommendation.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = recommendation[start_idx:end_idx]
                config = json.loads(json_str)
                return config
        except:
            pass
        
        # Fallback configuration
        return {
            "chart_type": "bar",
            "x_column": None,
            "y_column": None,
            "title": "Data Visualization",
            "x_label": "X",
            "y_label": "Y"
        }
    
    def _create_chart(self, df: pd.DataFrame, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a chart based on the configuration."""
        x_col = config.get('x_column')
        y_col = config.get('y_columns') or config.get('y_column')
        chart_type = config.get('chart_type')
        title = config.get('title')
        x_label = config.get('x_label')
        y_label = config.get('y_label')

        if not x_col and len(df.columns) > 0:
            x_col = df.columns[0]
        if not y_col and len(df.columns) > 1:
            y_col = df.columns[1]

        if not isinstance(y_col, list):
            y_col = [y_col]
        try:
            if chart_type == "bar":
                if len(y_col) > 1:
                    fig, ax = plt.subplots(1, len(y_col), figsize=(10, 5))
                    for i, col in enumerate(y_col):
                        ax[i].bar(df[x_col], df[col])
                        ax[i].set_title(f"{title} - {col}")
                        ax[i].set_xlabel(x_label)
                        ax[i].set_ylabel(col)
                        ax[i].tick_params(axis='x', labelrotation=45)
                else:
                    fig, ax = plt.subplots()
                    ax.bar(df[x_col], df[y_col[0]])
                    ax.set_title(title)
                    ax.set_xlabel(x_label)
                    ax.set_ylabel(y_label)
                    ax.tick_params(axis='x', labelrotation=45)

            elif chart_type == "line":
                if len(y_col) > 1:
                    fig, ax = plt.subplots(1, len(y_col), figsize=(10, 5))
                    for i, col in enumerate(y_col):
                        ax[i].plot(df[x_col], df[col], marker='o')
                        ax[i].set_xlabel(x_label)
                        ax[i].set_ylabel(col)
                        ax[i].tick_params(axis='x', labelrotation=45)
                else:
                    fig, ax = plt.subplots()
                    ax.plot(df[x_col], df[y_col[0]])
                    ax.set_title(title)
                    ax.set_xticks(df[x_col])
                    ax.set_xlabel(x_label)
                    ax.set_ylabel(y_label)
                    ax.tick_params(axis='x', labelrotation=45)

            elif chart_type == "pie":
                if len(y_col) > 1:
                    fig, ax = plt.subplots(1, len(y_col), figsize=(10,5))
                    for i, col in enumerate(y_col):
                        ax[i].pie(df[col], labels=df[x_col], autopct="%1.1f%%")
                        ax[i].set_title(f"{title} - {col}")
                else:
                    fig, ax = plt.subplots()
                    ax.pie(df[y_col[0]], labels=df[x_col], autopct="%1.1f%%")
                    ax.set_title(title)

            elif chart_type == "scatter":
                if len(y_col)>1:
                    fig, ax = plt.subplots(1, len(y_col), figsize=(10,5))
                    for i, col in enumerate(y_col):
                        ax[i].scatter(df[x_col], df[y_col])
                        ax[i].set_xlabel(x_label)
                        ax[i].set_ylabel(col)
                        ax[i].set_title(f"{title} - {col}")
                        ax[i].tick_params(axis='x', labelrotation=45)
                    else:
                        fig, ax = plt.subplots()
                        ax.scatter(df[x_col], df[y_col[0]])
                        ax.set_title(title)
                        ax.set_xlabel(x_label)
                        ax.set_ylabel(y_label)
                        ax.tick_params(axis='x', labelrotation=45)

            else:
                ax.bar(df[x_col], df[y_col[0]])


            # Save chart as base64
            buf = io.BytesIO()
            fig.savefig(buf, format="png")
            buf.seek(0)
            chart_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            plt.close(fig)

            return {
            "type": chart_type,
            "data": f"data:image/png;base64,{chart_base64}",
            "config": config,
            "summary": f"Generated a {chart_type} chart of {y_col} vs {x_col}"
            }

        except Exception as e:
            print(f"Chart generation failed: {e}")  # Debug
            return {
                "type": "table",
                "data": df.to_html(classes="table table-striped"),
                "config": config,
                "summary": f"Data table with {len(df)} rows and {len(df.columns)} columns"
            }

    
    def _generate_chart_summary(self, df: pd.DataFrame, config: Dict[str, Any]) -> str:
        """Generate a text summary of the chart."""
        
        chart_type = config.get("chart_type", "chart")
        title = config.get("title", "Data visualization")
        
        summary = f"{title} - {chart_type} chart showing {len(df)} data points"
        
        # Add insights based on data
        if len(df) > 0:
            if len(df.columns) >= 2:
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    max_val = df[numeric_cols[0]].max()
                    min_val = df[numeric_cols[0]].min()
                    summary += f". Values range from {min_val} to {max_val}"
        
        return summary
    
    def create_dashboard(self, multiple_results: List[Dict[str, Any]], user_query: str) -> Dict[str, Any]:
        """Create a dashboard with multiple visualizations."""
        
        visualizations = []
        
        for i, result in enumerate(multiple_results):
            viz = self.visualize_data(result, f"{user_query} - Chart {i+1}")
            if viz["success"]:
                visualizations.extend(viz["visualizations"])
        
        return {
            "success": len(visualizations) > 0,
            "dashboard": {
                "title": f"Dashboard for: {user_query}",
                "visualizations": visualizations,
                "created_at": pd.Timestamp.now().isoformat()
            }
        }