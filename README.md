# Local Python Code Review Platform

A local FastAPI service for reviewing uploaded Python code using a local LLM through Ollama.
The platform accepts a Python `.py` file, starts an asynchronous code review scan, stores the scan state in SQLite, and returns a `scan_id`. The user can later fetch the scan status and result using this ID.
---

## Quick Start
### 1. Create and activate a virtual environment
macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```
Windows:
```bash
python -m venv .venv
.venv\Scripts\activate
```
### 2. Install dependencies
```bash
pip install -r requirements.txt
```
```bash
pip install fastapi uvicorn sqlmodel requests python-multipart
```
### 3. Install Ollama
Install Ollama from:
https://ollama.com/download
Make sure Ollama is running locally.
Default Ollama server:
http://localhost:11434

### 4. Pull the required model
The default model is:
qwen2.5-coder:7b
Pull it with:
```bash
ollama pull qwen2.5-coder:7b
```
Verify installation:
```bash
ollama list
```
### 5. Run the FastAPI server
From the project root:
```bash
uvicorn code_review.main:app --reload
```
The server runs at:
```text
http://127.0.0.1:8000
```
### 6. Open Swagger UI
```text
http://127.0.0.1:8000/docs
```
Use Swagger UI to upload a Python file and call the API endpoints.
---

## API Flow

### 1. Create a scan
```http
POST /scans
```
Upload a `.py` file using form-data.
Example response:
```json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "running"
}
```
The scan runs in the background. The response does not wait for the LLM review to finish.
---

### 2. Get scan result
```http
GET /scans/{scan_id}
```
If the scan is still running:
```json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "running"
}
```
If the scan completed:
```json
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
```
If the scan failed:
```json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "failed",
  "error_message": "Could not connect to model provider. Make sure model provider is running locally."
}
```
If the scan ID does not exist:
```json
{
  "detail": "Scan not found"
}
```
---
## Endpoints
| Method | Path               | Description                          |
| ------ | ------------------ | ------------------------------------ |
| `GET`  | `/`                | Welcome                         |
| `POST` | `/scans`           | Upload Python file and create a scan |
| `GET`  | `/scans/{scan_id}` | Get scan status/result               |
---

## Code Review Rules
The current reviewer checks two rules:
Checks whether variables have clear and descriptive names.
Checks whether function docstrings describe the actual function behavior.
For example, if a docstring says that a function sorts a list but the implementation only filters values, the rule should fail.

## Validation Rules
Before creating a scan, the uploaded file is validated.
The file must:
* Have a `.py` extension.
* Not be empty.
* Be valid UTF-8 text.
Invalid files return `400 Bad Request`.
---

## Database
The project uses a local SQLite database.
Default database file: scans.db
The database stores scan metadata and results:
scan_id
filename
code_hash
status
result
error_message
created_at
expires_at
Tables are created automatically when the FastAPI app starts.
---

## Scan Lifecycle
A scan can have one of three statuses:
running - The scan was created and the background review is still in progress 
completed - The LLM review finished successfully and the result is available.
failed - The review failed, usually because the local model provider was unavailable, timed out, or returned an invalid response.
---

## Scan Caching
The platform calculates a SHA-256 hash of the uploaded code.
If the same code was already scanned and the previous scan has not expired, the existing scan is reused instead of calling the LLM again.
This avoids repeated work for identical code.
---

## Running Scan Limit
The platform allows up to 5 scans to run at the same time.
If 5 scans are already running, a new scan request returns:
```json
{
  "detail": "Too many scans in progress. Please try again later."
}
```
This prevents too many local LLM calls from running in parallel.
---

## Result Expiration
Scan results are valid for 24 hours.
Each scan stores:
created_at
expires_at
Expired scans are deleted before creating a new scan and before fetching scan results.
This keeps the local database small and prevents old results from being reused forever.
---

## Model Provider Configuration

The project uses Ollama by default.
Default configuration:
MODEL_PROVIDER_BASE_URL=http://localhost:11434
MODEL_PROVIDER_ENDPOINT=/api/chat
MODEL_NAME=qwen2.5-coder:7b
MODEL_TIMEOUT_SECONDS=120

## Project Structure
code_review/
├── main.py: Creates the FastAPI app, initializes database tables on        startup, and includes the API router.

├── platform.py: Contains the API routes, file validation, code hashing, scan creation, background task execution, and result retrieval.
├── database.py - Contains the SQLModel scan model and all SQLite database operations.

├── code_reviewer.py - Contains the review rules, the Ollama client, prompt handling, model response parsing, and final rule results.
├── requirements.txt
└── README.md
---
## Design Decisions
### FastAPI
FastAPI was chosen because this project is API-first and needs simple support for file uploads, background tasks, and Swagger UI.

### SQLite
SQLite was chosen because the assignment requires a local setup and the project does not need a separate database server.

### SQLModel
SQLModel provides a clean way to define the scan table and interact with SQLite.

### Ollama
Ollama is used to run the LLM locally. The platform sends prompts to the local Ollama API and expects a JSON result.

### Background Tasks
The scan request returns immediately with a `scan_id`, while the LLM review runs in the background. This avoids long-running HTTP requests.
