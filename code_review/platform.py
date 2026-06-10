
import hashlib
import json
import uuid
import os
from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException
from code_review.code_reviewer import OllamaClient, CodeReviewer, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS, OLLAMA_ENDPOINT, OLLAMA_BASE_URL
from code_review.database import Database, STATUS_RUNNING, STATUS_COMPLETED, STATUS_FAILED, EXPIRATION_HOURS
END_FILE_FORMATS = ".py"
MAX_CONCURRENT_SCANS = 5


""" This file defines the API routes and handlers for the code review platform. 
It uses FastAPI to create endpoints for uploading code files, checking scan status, and retrieving results. 
It also initializes the database and the code reviewer client."""

router = APIRouter()
db = Database()

""" The OllamaClient is initialized with the model provider configuration."""
MODEL_PROVIDER_BASE_URL = os.getenv("MODEL_PROVIDER_BASE_URL",OLLAMA_BASE_URL)
MODEL_PROVIDER_ENDPOINT = os.getenv("MODEL_PROVIDER_ENDPOINT",OLLAMA_ENDPOINT)
MODEL_NAME = os.getenv("MODEL_NAME",OLLAMA_MODEL)
MODEL_TIMEOUT_SECONDS = int(os.getenv("MODEL_TIMEOUT_SECONDS",str(OLLAMA_TIMEOUT_SECONDS)))

llm_client = OllamaClient(
    base_url=MODEL_PROVIDER_BASE_URL,
    endpoint=MODEL_PROVIDER_ENDPOINT,
    model=MODEL_NAME,
    timeout_seconds=MODEL_TIMEOUT_SECONDS,
)

code_reviewer = CodeReviewer(
    llm_client=llm_client
)

async def check_if_valid_file_input(file: UploadFile) -> str:
    if file is None or file.filename is None:
        raise HTTPException(status_code=400, detail="file is required")
    if not file.filename.endswith(END_FILE_FORMATS):
        raise HTTPException(status_code=400, detail="only " + END_FILE_FORMATS + " files are supported")
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400,detail="Uploaded file is empty.")
    try:
        code_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="File must be a valid UTF-8 text file."
        )
    return code_text

def create_code_hash(code_text) -> str:
    """ This function creates a SHA-256 hash of the code text. This is used to identify duplicate scans"""
    return hashlib.sha256(code_text.encode("utf-8")).hexdigest()


def run_code_review_scan(scan_id: str, code_text: str) -> None:
    """ This function runs the code review scan in the background. It calls the code reviewer to review the code and updates 
        the result in the database. 
        If there is an error during the review, it marks the scan as failed with the error message."""
    try:
        review_result = code_reviewer.review_code(code_text)
        result_json = json.dumps(review_result)
        db.update_scan_result(scan_id, result_json)

    except Exception as error:
        db.mark_scan_failed(scan_id, str(error))



""" The API routes are defined below."""

@router.get("/")
def read_root():
    db.delete_expired_scans()
    return {"message": "Hi! welcome to my code review platform"}


@router.post("/scans")
async def create_scan(background_tasks: BackgroundTasks,file: UploadFile = File(...)):
    db.delete_expired_scans()

    code_text = await check_if_valid_file_input(file)
    code_hash = create_code_hash(code_text)

    existing_code= db.get_scan_by_hash(code_hash)

    if existing_code:
        return {
            "scan_id": existing_code.scan_id,
            "status": existing_code.status
        }
    else:
        if db.count_running_scans() >= MAX_CONCURRENT_SCANS:
            raise HTTPException(status_code=429, detail="Too many scans in progress. Please try again later.")
        else:
            scan_id = str(uuid.uuid4())
            scan = db.create_scan(
                scan_id=scan_id,
                file_name=file.filename,
                code_hash=code_hash,
                status=STATUS_RUNNING,
            )
            background_tasks.add_task(run_code_review_scan,scan_id, code_text)

    return {
        "scan_id": scan.scan_id,
        "status": scan.status,
        }

@router.get("/scans/{scan_id}")
async def get_scan_result(scan_id: str):
    db.delete_expired_scans()
    scan = db.get_scan_by_id(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    response = {
        "scan_id": scan.scan_id,
        "status": scan.status,
    }
    if scan.status == STATUS_COMPLETED:
        response["result"] = json.loads(scan.result)
    elif scan.status == STATUS_FAILED:
        response["error_message"] = scan.error_message

    return response
