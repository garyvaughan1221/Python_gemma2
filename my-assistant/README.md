# CODE UPDATE: This code project has evolved since the early coding sessions/commits.

The current version of this repo is using Gemini 2.5 Flash via the Google API, not Gemma 2B via Ollama. It's also using Supabase instead of ChromaDB for vector storage.

**So the current stack is:**

>- **LLM**: Gemini 2.5 Flash (cloud, Google API)
>- **Embeddings**: gemini-embedding-001 (Google API)
>- **Vector store**: Supabase (cloud, Postgres + pgvector)
>- **Framework**: LangChain
>- **UI**: docker container on 'Google Cloud Run'

<br>&nbsp;</br>
## Reason:
I didn't know what I was doing at first...I was just learning and I wanted to have it running locally first.
Once it was running locally with scraping and ingesting, I offloaded some of the heavy lifting to the cloud.
Then eventually went with PostGres over 'sqlite chroma db' for the data storage.
Then I moved the UI to Google Cloud Run to have a live url: [click me](https://pierce-assistant-469343134497.us-west1.run.app).

<br>&nbsp;</br>
## Notes for the future:
>- I will work on scraping and ingesting data from PierceCounty.gov.
>- Eventually/probably pretty up the UI.
