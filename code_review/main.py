#iniate FASTAPI
from fastapi import FastAPI
from code_review.platform import router, db

""" This is the main entry point for the code review platform. It sets up the FastAPI application, initializes the databas
"""

app = FastAPI()
@app.on_event("startup")
def startup():
    db.create_tables()
app.include_router(router)
    


