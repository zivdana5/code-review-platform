# Local Python Code Review Platform

A local FastAPI service for reviewing uploaded Python code using a local LLM through Ollama. 
The platform accepts a Python `.py` file, starts an asynchronous code review scan, stores the scan state in a local SQLite database, and returns a `scan_id`. The user can later fetch the scan status and result using this ID.

---

## Quick Start

### 1. Create and activate a virtual environment
**macOS / Linux:**
` ` `bash
python3 -m venv .venv
source .venv/bin/activate
` ` `

**Windows:**
` ` `bash
python -m venv .venv
.venv\Scripts\activate
` ` `

### 2. Install dependencies
` ` `bash
pip install -r requirements.txt
` ` `

### 3. Install Ollama
This project uses Ollama to run the LLM locally.
1. Install Ollama from the official site: https://ollama.com/download
2. Make sure Ollama is running locally. The default Ollama server URL is: `http://localhost:11434`

### 4. Pull the required model
The default model for this project is `qwen2.5-coder:7b`. Pull it by running:
` ` `bash
ollama pull qwen2.5-coder:7b
` ` `
*(You can verify the installation by running `ollama list`)*

### 5. Run the FastAPI server
From the project root directory, run:
` ` `bash
uvicorn code_review.main:app --reload
` ` `
The server will start at: `http://127.0.0.1:8000`

### 6. Open Swagger UI
Navigate to `http://127.0.0.1:8000/docs` in your browser. You can use the interactive Swagger UI to upload a Python file and test the API endpoints.

---

## API Flow

### 1. Create a Scan
**Endpoint:** `POST /scans`

Upload a `.py` file using `form-data`.
**Example Response:**
` ` `json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "running"
}
` ` `
*Note: The scan runs in the background. The response returns immediately without waiting for the LLM review to finish.*

### 2. Get Scan Result
**Endpoint:** `GET /scans/{scan_id}`

**If the scan is still running:**
` ` `json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "running"
}
` ` `

**If the scan completed:**
` ` `json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "completed",
  "result": {
    "checked_rules": [
      {
        "rule_id": "meaningful_variable_names",
        "passed": true
      },
      {
        "rule_id": "docstring_matches_logic",
        "passed": false
      }
    ]
  }
}
` ` `

**If the scan failed:**
` ` `json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "failed",
  "error_message": "Could not connect to model provider. Make sure the model provider is running locally."
}
` ` `

---

## Code Review Rules
The current reviewer checks the code against two rules:
1. **Meaningful Variable Names:** Checks whether variables have clear and descriptive names (avoiding arbitrary names like `x`, `foo`, `tmp` unless contextually appropriate).
2. **Docstring Matches Logic:** Checks whether function docstrings accurately describe the actual function behavior. (e.g., if a docstring says a function sorts a list, but the implementation only filters values, the rule will fail).

---

## Validation & Constraints

* **File Validation:** Uploaded files must have a `.py` extension, must not be empty, and must be valid UTF-8 text. Invalid files return a `400 Bad Request`.
* **Scan Caching:** The platform calculates a SHA-256 hash of the uploaded code. If the exact same code was already scanned and hasn't expired, the existing scan result is reused.
* **Concurrency Limit:** The platform allows up to **5 scans** to run concurrently to avoid overloading the local machine. Additional requests will return a `429 Too Many Requests` error.
* **Result Expiration:** Scan results are temporarily stored in a SQLite database (`scans.db`) and are strictly valid for **24 hours**. Expired scans are automatically purged.

---

## Model Provider Configuration
The project is parameterized to allow easy replacement of the LLM provider using environment variables. 
**Default configuration:**
* `MODEL_PROVIDER_BASE_URL` = `http://localhost:11434`
* `MODEL_PROVIDER_ENDPOINT` = `/api/chat`
* `MODEL_NAME` = `qwen2.5-coder:7b`
* `MODEL_TIMEOUT_SECONDS` = `120`

### Bonus: Testing with LM Studio
The platform is fully parameterized and can easily work with other local providers like LM Studio.

To test with LM Studio instead of Ollama:

1. Open LM Studio and start the Local Server (the default port is usually `1234`).
2. Set the environment variables in your terminal to override the default Ollama settings:

**macOS / Linux:**
` ` `bash
export MODEL_PROVIDER_BASE_URL="http://localhost:1234"
export MODEL_PROVIDER_ENDPOINT="/v1/chat/completions"
export MODEL_NAME="your-downloaded-model-name"
` ` `

**Windows (PowerShell):**
` ` `powershell
$env:MODEL_PROVIDER_BASE_URL="http://localhost:1234"
$env:MODEL_PROVIDER_ENDPOINT="/v1/chat/completions"
$env:MODEL_NAME="your-downloaded-model-name"
` ` `

3. Run the FastAPI server from the same terminal session:
` ` `bash
uvicorn code_review.main:app --reload
` ` `

---

## Project Structure
` ` `text
code_review/
├── main.py          # Creates the FastAPI app and initializes the DB tables
├── platform.py      # Contains the API routes, file validation, and background tasks
├── database.py      # Contains the SQLModel schema and SQLite database operations
├── code_reviewer.py # Contains the Ollama client, prompt building, and review rules
├── requirements.txt
└── README.md
` ` `