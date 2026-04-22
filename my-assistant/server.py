from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from pydantic import BaseModel
from chat import ask, ask_stream

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory="public"), name="public")

class Question(BaseModel):
    question: str

@app.get("/")
def root():
    return RedirectResponse(url="/public/index.html")


# Probably not needed anymore...
@app.post("/ask")
def ask_question(body: Question):
    answer = ask(body.question)
    return {"answer": answer}


# Streaming endpoint for real-time responses.  This allows the client to receive partial answers as they are generated.
# The client can use this to display a loading indicator or show the answer as it comes in, improving the user experience.
# The ask_stream function is a generator that yields parts of the answer as they are generated.  The StreamingResponse will send these parts to the client as they are received, allowing for a more interactive experience.
# Called by HTTP_POST '/ask-stream' (in index.html) with a JSON body containing the question.  The response is a stream of text that can be consumed by the client in real-time.
@app.post("/ask-stream")
def ask_stream_endpoint(body: Question):
    return StreamingResponse(
        ask_stream(body.question),
        media_type="text/plain"
    )