# CrewAI SQL Generator

A natural language to SQL query generation system powered by CrewAI agents, MySQL MCP integration, and interactive data visualization.

## 🚀 Features

- **Natural Language Processing**: Convert plain English questions into SQL queries
- **Multi-Agent System**: Uses CrewAI agents for query generation, validation, execution, and visualization
- **MySQL MCP Integration**: Secure database operations via Model Context Protocol
- **Real-time Visualization**: Interactive charts and graphs using Plotly
- **Chat Interface**: User-friendly web interface for natural language queries
- **Safety & Validation**: Built-in query validation and security measures

## 🏗️ Architecture

The system uses four specialized CrewAI agents:

1. **Query Generator Agent**: Converts natural language to SQL using domain-specific prompts
2. **Query Validator Agent**: Validates SQL queries for safety and correctness
3. **Query Executor Agent**: Executes queries via MySQL MCP
4. **Data Visualizer Agent**: Creates interactive visualizations from results

## 🔧 Setup Instructions

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- Node.js 18+ (for MCP server)
- OpenAI API key (or other LLM provider)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd crewai_sqlgen

# Create and activate virtual environment (REQUIRED)
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Copy environment file
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```env
# LLM Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration (Docker will handle this)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=beauty_wellness
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Application Configuration
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
```

### 3. Start with Docker (Recommended)

```bash
# Start MySQL database
docker-compose up postgres -d

# Wait for database to be ready (check with health check)
docker-compose ps

# Optional: Start pgAdmin for database management
docker-compose --profile admin up pgadmin -d

# Install Python dependencies in virtual environment
pip install -r requirements.txt
```

### 4. Run the Application

```bash
# Make sure virtual environment is activated
# Start the FastAPI application
python run.py
# Or alternatively:
# python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access the Application

- **Chat Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **pgAdmin** (if started): http://localhost:5050
  - Email: admin@example.com
  - Password: admin

## 📖 Usage

### Web Interface

1. Open http://localhost:8000 in your browser
2. Enter your business ID (use `demo-business-123` for sample data)
3. Ask questions in natural language:
   - "Show me top performing employees this month"
   - "What is our revenue trend over the last 6 months?"
   - "Which services are most popular?"
   - "Show customer retention rates"

### API Usage

#### Generate SQL Query

```bash
curl -X POST "http://localhost:8000/api/query" \
     -H "Content-Type: application/json" \
     -d '{
       "query": "Show me top performing employees this month",
       "business_id": "demo-business-123"
     }'
```

#### Validate SQL Query

```bash
curl -X POST "http://localhost:8000/api/validate-sql" \
     -H "Content-Type: application/json" \
     -d '{
       "sql_query": "SELECT * FROM employees",
       "business_id": "demo-business-123"
     }'
```

## 🗄️ Database Schema

The system includes a sample beauty/wellness business schema with:

- **vendor_locations**: Business locations
- **employees**: Staff members
- **users**: Customers
- **services**: Available services
- **bills**: Invoices and payments
- **active_queues**: Current day appointments
- **appointments**: Scheduled appointments

### Sample Business IDs

- `demo-business-123`: Elegant Beauty Spa
- `demo-business-456`: Wellness Center Plus  
- `demo-business-789`: Luxe Hair Studio

## 🔧 Configuration

### MCP Configuration

The system uses MySQL MCP for secure database operations. Configuration is in `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "MySQL://..."]
    }
  },
  "security": {
    "allowed_operations": ["SELECT", "WITH"],
    "blocked_operations": ["DROP", "DELETE", "TRUNCATE", "ALTER", "CREATE", "INSERT", "UPDATE"],
    "query_timeout": 30,
    "max_rows": 1000
  }
}
```

### Agent Configuration

Agents can be configured with different LLM providers:

```python
# In src/core/settings.py
OPENAI_API_KEY=your_key_here        # For OpenAI GPT models
ANTHROPIC_API_KEY=your_key_here     # For Claude models  
GEMINI_API_KEY=your_key_here        # For Google Gemini models
```

## 🚀 Deployment

### Docker Deployment

```bash
# Build and run everything
docker-compose --profile app up --build

# Or run individual services
docker-compose up postgres -d
docker-compose --profile app up app
```

### Production Deployment

1. Update environment variables for production
2. Use proper secret management
3. Configure reverse proxy (nginx/traefik)
4. Set up SSL certificates
5. Configure monitoring and logging

## 🧪 Testing

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## 📊 Example Queries

The system can handle various business intelligence queries:

### Employee Performance
```
"Show me top performing employees this month"
"Which employee has the highest customer satisfaction?"
"Employee revenue comparison for last quarter"
```

### Revenue Analysis
```
"What is our revenue trend over the last 6 months?"
"Compare revenue by service category"
"Show monthly recurring revenue"
```

### Service Analytics
```
"Which services are most popular?"
"Average booking duration by service type"
"Service profitability analysis"
```

### Customer Insights
```
"Show customer retention rates"
"List new customers this month"
"Customer lifetime value analysis"
```

## 🛡️ Security Features

- Query validation and sanitization
- Read-only database operations
- Business ID filtering for data isolation
- SQL injection prevention
- Query timeout limits
- Result row limits

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check if MySQL is running
   docker-compose ps postgres
   
   # Check logs
   docker-compose logs postgres
   ```

2. **LLM API Errors**
   - Verify API key in `.env` file
   - Check API key permissions and credits
   - Try with a different model

3. **MCP Connection Issues**
   - Ensure Node.js is installed
   - Check MCP server logs
   - Verify MySQL connection string

### Debug Mode

Enable debug mode in `.env`:
```env
DEBUG=true
LOG_LEVEL=DEBUG
```

## 📝 Development

### Project Structure

```
crewai_sqlgen/
├── venv/               # Virtual environment (created by you)
├── src/
│   ├── agents/           # CrewAI agents
│   ├── api/             # FastAPI application
│   ├── core/            # Core utilities
│   ├── prompts/         # LLM prompts
│   └── templates/       # HTML templates
├── config/              # Configuration files
├── database/           # Database setup
├── tests/              # Test files
├── requirements.txt     # Python dependencies
├── run.py              # Application startup script
└── docker-compose.yml  # Docker configuration
```

### Virtual Environment Best Practices

**ALWAYS use a virtual environment** to avoid dependency conflicts:

```bash
# Create virtual environment
python -m venv venv

# Activate (do this every time you work on the project)
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Deactivate when done
deactivate
```

### Adding New Agents

1. Create agent class in `src/agents/`
2. Add to orchestrator in `src/core/crew_orchestrator.py`
3. Update API endpoints if needed

### Customizing Prompts

Edit prompts in `src/prompts/` to customize for your domain:
- `query_generation_prompt.md`: SQL generation rules
- Add domain-specific examples and schema information

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Search existing issues
3. Create a new issue with detailed information

---

**Built with CrewAI, FastAPI, MySQL MCP, and Plotly** 🚀