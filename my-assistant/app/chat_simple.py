import ollama

response = ollama.chat(
    model='gemma2:2b',
    messages=[
        {'role': 'user', 'content': 'Explain what a quitclaim deed is in plain English.'}
    ]
)

print(response['message']['content'])