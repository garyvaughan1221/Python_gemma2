# Project Name
Python Gemma2:2b Chatbot

Just playing around with AI.  I'm using Ollama with Gemma2:2b model to run locally.  My (aging) laptop is a Compaq Probook 6460b duoCore with 16GB of ram running Windows10.

I used VSCode to do this with the help of ClaudeAI.  Gemini in VSCode sucks, imo...



## Installation
First and foremost you'll need to download [Ollama](https://www.ollama.com/download).  It is a bundle of a GUI App and a system tray icon (a service).  They need to both be there.  Don't uninstall the GUI App, just close it.

Secondly, I used a virtual environment on this project.  The .venv folder is located outside of the 'my-assistant' folder.  It is not in the git repo.  Oki?

```powershell
python -m venv .venv
```

On my laptop, I used python 3.12.10 for this project.  It caused some module import resolution issues, but I figured them out, thus the usage a settings.json file in the .vsCode folder.  The settings.json file points to my local installation of python 3.12.10.

You could try using a different version though. Or install python 3.12.10 and run the command this way:

```powershell
python 3.12.10 -m venv .venv
```



## Usage
While in the /my-assistant folder, you can do these things:

### chat
Chat with Ollama locally.
```powershell
python chat.py
```

### ingest
Ingest documents of .txt of .pdf formats, from the /data folder >> into the /db/chroma.sqlite3 database.

```powershell
python ingest.py
```
