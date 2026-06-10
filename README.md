# Local Python Code Review Platform

A local FastAPI platform that reviews uploaded Python files using a local LLM through Ollama.

The platform:
- accepts a `.py` file
- starts a scan in the background
- stores the scan in a local SQLite database
- returns a `scan_id`
- lets the user fetch the scan result later

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/zivdana5/code-review-platform.git
cd code-review-platform
```

### 2. Create and activate a virtual environment

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

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Ollama

Install Ollama from:

```text
https://ollama.com/download
```

### 5. Pull the required model

```bash
ollama pull qwen2.5-coder:7b
```

You can check that the model exists with:

```bash
ollama list
```

### 6. Run the server

```bash
uvicorn code_review.main:app --reload
```

The server runs at:

```text
http://127.0.0.1:8000
```

### 7. Open Swagger UI

Open this URL in the browser:

```text
http://127.0.0.1:8000/docs
```

Use Swagger to upload a Python file and test the API.

---


## Model Provider Configuration

The model provider details are configurable with environment variables.

Default values:

```text
MODEL_PROVIDER_BASE_URL=http://localhost:11434
MODEL_PROVIDER_ENDPOINT=/api/chat
MODEL_NAME=qwen2.5-coder:7b
MODEL_TIMEOUT_SECONDS=120
```

### Run with a different Ollama model

First, pull the model you want to use:

```bash
ollama pull llama3.2
```

Then run the server with the new model name:

```bash
export MODEL_NAME="llama3.2"
uvicorn code_review.main:app --reload
```

The model must be installed locally before running the server.

### Change provider settings

The provider connection can be changed using environment variables:

```bash
export MODEL_PROVIDER_BASE_URL="http://localhost:11434"
export MODEL_PROVIDER_ENDPOINT="/api/chat"
export MODEL_NAME="qwen2.5-coder:7b"
export MODEL_TIMEOUT_SECONDS="120"
uvicorn code_review.main:app --reload
```

This keeps the model provider details separate from the code and makes future replacement easier.

---

## API Flow

### Create a scan

```text
POST /scans
```

Upload a `.py` file.

Example response:

```json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "running"
}
```

The scan runs in the background.

### Get scan result

```text
GET /scans/{scan_id}
```

Example completed response:

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

Example running response:

```json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "running"
}
```

Example failed response:

```json
{
  "scan_id": "3f7a62a1-7d3a-4c5e-bf9e-41d1f52e8b21",
  "status": "failed",
  "error_message": "Could not connect to model provider."
}
```

---

## Code Review Rules

The platform currently checks two rules:

1. `meaningful_variable_names`  
   Checks whether variable names are clear and meaningful.

2. `docstring_matches_logic`  
   Checks whether function docstrings match the actual code logic.

Each rule returns only:

```json
{
  "rule_id": "rule_name",
  "passed": true
}
```

or:

```json
{
  "rule_id": "rule_name",
  "passed": false
}
```

---

## Validation

Uploaded files must be:

- Python files with a `.py` extension
- not empty
- valid UTF-8 text

Invalid files return `400 Bad Request`.

---

## Database

The project uses a local SQLite database:

```text
scans.db
```

The database stores:

- scan id
- file name
- code hash
- scan status
- scan result
- error message
- creation time
- expiration time

Scan results are stored for 24 hours.

Expired scans are deleted automatically.

---


## Concurrency Limit

The platform supports up to 5 running scans at the same time.

If there are already 5 running scans, the API returns:

```text
429 Too Many Requests
```

---

## Project Structure

```text
code_review/
├── main.py
├── platform.py
├── database.py
└── code_reviewer.py

requirements.txt
README.md
AI_prompts.txt
```

### Main files

`main.py`  
Creates the FastAPI app and initializes the database tables.

`platform.py`  
Contains the API routes, file validation, scan creation, and background task.

`database.py`  
Contains the SQLite database model and database operations.

`code_reviewer.py`  
Contains the Ollama client, review rules, prompt building, and LLM response parsing.

---

