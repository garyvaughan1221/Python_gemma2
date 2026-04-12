from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chat import ask
from fastapi.responses import RedirectResponse

app = FastAPI()

@app.get("/")
def root():
    return RedirectResponse(url="/public/index.html")

# Allow your HTML front end to talk to the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve your HTML front end at localhost:8000
app.mount("/public", StaticFiles(directory="public"), name="public")

class Question(BaseModel):
    question: str

@app.post("/ask")
def ask_question(body: Question):
    answer = ask(body.question)
    return {"answer": answer}