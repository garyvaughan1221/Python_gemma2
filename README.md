# Project Name
Python Gemma2:2b Chatbot

Just playing around with AI.  I'm using Ollama with Gemma2:2b model to run locally.  My (aging) laptop is a Compaq Probook 6460b duoCore with 16GB of ram running Windows10.

I used VSCode to do this with the help of ClaudeAI.  Gemini in VSCode sucks, imo...

## Update, Updated code >>>>
As of April 23, 2026 this code has been updated to use supabase as the db (so use an earlier commit if you don't have a supabase db).
Also, the code is not using Ollama anymore.  I'm using Gemini 2.5 from AI Studio.  I have a google cloud account, but created my Gemini API Key in Google AI Studio. <---

April 24, 2026
This is now running on Google Cloud Run.  It is running in a docker container.  ClaudeAI gave me the DockerFile and setup instructions.  I used Google CloudSDK CLI to setup via powershell.
Here is the [chat interace](https://pierce-assistant-469343134497.us-west1.run.app).
## Update, Updated Code <<<<

<br>&nbsp;</br>
<br>&nbsp;</br>
## Installation
First and foremost you'll need to download [Ollama](https://www.ollama.com/download).  It is a bundle of a GUI App and a system tray icon (a service).  They need to both be there.  Don't uninstall the GUI App, just close it.

Secondly, I used a virtual environment on this project.  The .venv folder is located outside of the 'my-assistant' folder.  It is not in the git repo.  Oki?


To make your own virtual folder.  You should probably google this for some R&D if you aren't aware of how to do this or why.
```powershell
python -m venv .venv
```

ALTERNATIVELY, On my laptop, I used python 3.12.10 for this project. I chose to do this to simulate an environment where the app has to be coded for a specific version of python; as opposed to the latest version. It caused some module import resolution issues, but I figured them out, thus the usage a settings.json file in the .vsCode folder.  The settings.json file points to my local installation of python 3.12.10.

You could try using a different version though. Or install python 3.12.10 and run the command this way:
```powershell
python 3.12.10 -m venv .venv
```

Now you have to activate your virtual environment before installing the modules in '\my-assistant\requirements.txt'. Before running this command make sure to be in the correct root folder!
```powershell
.venv\Scripts\activate
```

Go into the subroot folder and install the modules this way.
```powershell
cd my-assistant
pip install -r requirements.txt
```

Once that is finished, try running the app.
```powershell
python  -m uvicorn server:app --reload
```


<br/><br/>
## Usage
While in the /my-assistant folder, you can do these things:


### chat
Chat with Ollama locally.
```powershell
python chat.py
```

### ingest
Ingest documents of .txt of .pdf formats, from the 'my-assistant/data' folder >> into the /db/chroma.sqlite3 database. The script is setup to keep track of what was ingested via the 'ingested.json' file.  Just drop the files into the 'data' folder and run the script.  The script code should be fairly easy to read.  If you can't read it well, you probably should learn to code more before tackling something like this; -(or learn by trial & error?)

```powershell
python ingest.py
```
