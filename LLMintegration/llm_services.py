from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI


def get_gemini_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-1.5-flash-latest",
        api_key=settings.GEMINI_API_KEY,  # set environment variable or Django settings
        temperature=0.7,  # higher values = more creative responses
        # max_output_tokens=512,  # Adjust based on your needs
        top_p=0.95,  # nucleus sampling: cumulative prob mass
        top_k=40,  # top-k sampling: restrict to k candidates
        model_kwargs={"response_mime_type": "application/json"},
    )
