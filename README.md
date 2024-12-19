# CHESS+: Enhanced Contextual SQL Synthesis with Chat Capabilities

This repository contains an enhanced version of CHESS (Contextual Harnessing for Efficient SQL Synthesis), extending it with interactive chat capabilities and additional components.

## Original CHESS Framework
This project builds upon the original CHESS framework, which addresses text-to-SQL translation through four specialized agents:

1. **Information Retriever (IR)**: Extracts relevant data
2. **Schema Selector (SS)**: Prunes large schemas
3. **Candidate Generator (CG)**: Generates high-quality candidates
4. **Unit Tester (UT)**: Validates queries through LLM-based testing

## New Features

### Interactive Chat Capabilities
The enhanced version introduces interactive chat functionality through new specialized components:

1. **Chat Context Analyzer**: Understands user intent and conversation flow
2. **Response Generator**: Produces natural language responses
3. **SQL Executor**: Manages query execution and result formatting
4. **Enhanced Information Retriever**: Improved keyword extraction and context management

### Key Enhancements
- **Interactive Sessions**: Maintain context across multiple queries
- **Natural Conversations**: More intuitive interaction with the SQL generation system
- **Result Formatting**: Clean presentation of query results
- **Context-Aware Responses**: Improved understanding of follow-up questions

## Installation and Setup

1. **Clone the repository**:
    ```bash
    git clone https://github.com/noincent/chess-plus.git
    cd chess-plus-main
    ```

2. **Set up Python virtual environment** (Python 3.8+ recommended):
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    pip install -r requirements.txt
    ```

3. **Configure environment variables**:
    - Copy `dotenv_copy` to `.env`:
      ```bash
      cp dotenv_copy .env
      ```
    - Edit `.env` and fill in your API keys and configuration





## Project Structure
```
CHESS/
├── src/           # Core source code
├── run/           # Configuration files
├── templates/     # SQL templates
└── logs/          # Log files
```


## Supporting Other LLMs

To use your own LLM, modify the `get_llm_chain(engine, temperature, base_uri=None)` function and add your LLM in `run/langchain_utils.py`.


## Web Interface Integration

CHESS+ provides a FastAPI-based web interface that allows easy integration with any frontend application. The web server exposes a RESTful API that handles natural language queries and returns SQL responses.

### Starting the Web Server

1. **Run the web server**:
   ```bash
   python web_interface.py
   ```
   The server will start on `http://0.0.0.0:8010`

### API Endpoints

#### POST /create_session
Creates a new chat session.

**Request Format**:
```json
{
    "user_id": "unique_user_identifier",
    "db_id": "optional_database_id"  // defaults to "wtl_employee_tracker"
}
```

**Response Format**:
```json
{
    "session_id": "generated_uuid",
    "db_id": "database_id",
    "user_id": "user_id"
}
```

#### POST /generate
Processes natural language queries using an existing session.

**Request Format**:
```json
{
    "prompt": "Your natural language query",
    "session_id": "session_id_from_create_session"
}
```

**Response Format**:
```json
{
    "result": "Natural language response from CHESS"
}
```

#### POST /end_session/{session_id}
Explicitly ends a chat session.

**Response Format**:
```json
{
    "message": "Session ended successfully"
}
```

### Testing with curl

You can test the API directly using curl commands. First, install jq for better JSON formatting:
```bash
sudo apt install jq
```

Then run these commands in sequence:

1. Create a new session:
```bash
curl -X POST http://localhost:8010/create_session \
-H "Content-Type: application/json" \
-d '{"user_id": "test_user", "db_id": "wtl_employee_tracker"}' | jq
```

2. Store the session ID (replace YOUR_SESSION_ID with the id from previous response):
```bash
export SESSION_ID="YOUR_SESSION_ID"
```

3. Make a query:
```bash
curl -X POST http://localhost:8010/generate \
-H "Content-Type: application/json" \
-d "{\"prompt\": \"Show me all employees\", \"session_id\": \"$SESSION_ID\"}" | jq
```

4. Make a follow-up query:
```bash
curl -X POST http://localhost:8010/generate \
-H "Content-Type: application/json" \
-d "{\"prompt\": \"How many of them are in sales?\", \"session_id\": \"$SESSION_ID\"}" | jq
```

5. End the session:
```bash
curl -X POST "http://localhost:8010/end_session/$SESSION_ID" | jq
```

### Frontend Integration Example

```javascript
// Example frontend usage
async function chatWithCHESS() {
    // Step 1: Create a new session
    const sessionResponse = await fetch('http://localhost:8010/create_session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            user_id: 'user123',
            db_id: 'employee_db'
        })
    });
    const { session_id } = await sessionResponse.json();

    // Step 2: Use the session for queries
    const queryResponse = await fetch('http://localhost:8010/generate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            prompt: "Show me all employees in the sales department",
            session_id: session_id
        })
    });
    const result = await queryResponse.json();
    console.log(result.result);

    // Step 3: End the session when done
    await fetch(`http://localhost:8010/end_session/${session_id}`, {
        method: 'POST'
    });
}
```

### Session Management
The web interface uses a session-based system to maintain conversation context:

1. **Creating Sessions**: 
   - Each conversation starts with a new session
   - Sessions are unique even for the same user and database
   - Use `/create_session` to start a fresh conversation

2. **Using Sessions**:
   - Include the `session_id` with each query
   - Sessions maintain conversation context
   - Invalid or expired sessions return 400 error

3. **Ending Sessions**:
   - Sessions can be explicitly ended using `/end_session`
   - Start a new session to begin a fresh conversation

### CORS Configuration
The web interface has CORS enabled and allows:
- All origins (`*`)
- All methods
- All headers
- Credentials

### Error Handling
The API returns standard HTTP status codes:
- `400`: Bad Request (invalid input or expired session)
- `404`: Session not found (when ending session)
- `500`: Internal Server Error

## Troubleshooting

1. **Missing API Keys**: Ensure all required API keys are set in `.env`
2. **Database Connection**: Check if database files exist in the correct location
3. **Port Conflicts**: If port 8010 is in use, modify the port in the startup command

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

See [LICENSE](LICENSE) file for details.

## Attribution

This project is based on the original CHESS framework. If you use this enhanced version in your research, please cite both this repository and the original CHESS paper:

```bibtex
@article{talaei2024chess,
  title={CHESS: Contextual Harnessing for Efficient SQL Synthesis},
  author={Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin},
  journal={arXiv preprint arXiv:2405.16755},
  year={2024}
}