import json
import logging
import os

from django.conf import settings
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import Conversation, Message
from .vectorstore_utils import search_vectorstore
import re
from datetime import datetime

logger = logging.getLogger(__name__)


def get_gemini_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-05-20",
        api_key=settings.GEMINI_API_KEY,  # set environment variable or Django settings
        temperature=0.7,  # higher values = more creative responses
        # max_output_tokens=512,  # Adjust based on your needs
        top_p=0.95,  # nucleus sampling: cumulative prob mass
        top_k=40,  # top-k sampling: restrict to k candidates
    )


# YOU SHOULD ENSURE THE RETRIEVED CONTEXT IS RELAVENT TO THE USER'S UNIVERSITY/LOCATION/CURRENT DATE.
# YOU CAN DO THIS BY FILTERING THE RETRIEVED CONTEXT, OR YOU CAN LET THE LLM DO IT. OR CAN WE QUERY THE VECTOR STORE WITH USER'S UNIVERSITY/LOCATION/CURRENT DATE AS WELL. OR COMBINE ALL THESE METHODS.
BASE_PROMPT_TEMPLATE = """
You are Dormie, a friendly and empathetic academic advisor and mental health counsellor for university students.
If the query is mental health/emotional support related, be empathetic and perspectival.
If it is an academic query, guide them like a knowledgeable and approachable senior.
Always maintain an informal, friendly, and understanding tone.

Always attach the internal link of the retrived information (in a bracket) in your response, so that the user can cross check it theirselves.
You also should make sure NOT to respond with an outdated information, so check the date of the retrived information and make sure the response is relevant to the current date. Today's date is {current_date}.

You will be provided with the following information to help you answer the user's question:

Potentially relevant information from posts or comments of an inter-university connected network.(use this information if it directly helps answer the user's current question, otherwise ignore it):
---
{retrieved_context}
---

Previous conversation summary:
---
{conversation_summary}
---

Recent chat history:
---
{recent_messages}
---

User's very latest message waiting for your response:
---
{user_message}
---

You have two jobs. Your primary task is to respond to the user's latest message based on the conversation history and any relevant information given above. Secondly, you will also provide a summary of the entire conversation so far, which will be used to help you answer future questions.
You MUST respond STRICTLY in VALID JSON format (NOT even ```json ``` these code fences) (as it will be DIRECTLY parsed later) with two keys: 'reply' and 'summary' accordingly.
"""


def format_retrieved_docs(docs: list) -> str:
    """Formats the retrieved documents for inclusion in the prompt."""
    if not docs:
        return "No relevant information found in university posts or comments for this query."

    formatted_docs = []
    for i, doc in enumerate(docs):
        content = doc.page_content
        metadata = doc.metadata
        source_type = metadata.get("source_type", "document")
        title = metadata.get("title", "")
        author = metadata.get("author_username", "N/A")
        created_at = metadata.get("created_at", "Unknown date")
        url = metadata.get("url", "Not Found")

        entry = f"Context {i+1} (Source: {source_type}"
        if title:
            entry += f", Title: '{title}'"
        entry += f", Author: {author}):\n{content}"
        entry += f", Date Created at: {created_at}" if created_at else ""
        entry += f", URL: {url}" if url else ""
        formatted_docs.append(entry)

    return "\n\n".join(
        formatted_docs
    )  # joins all formatted entries in the list with double newlines
    """ Example output:
    Context 1 (Source: post, Title: 'My Blog', Author: john_doe, Created at: 2023-10-01):
    Post Title: My Blog
    Post Content: Hello, world!

    Context 2 (Source: comment, Title: 'My Blog', Author: jane_smith, Created at: 2023-10-02):
    Comment on post titled 'My Blog': Great post!
    """


def generate_bot_response(conversation: Conversation, user_text: str) -> str:
    logger.info(
        f"Generating bot response for conversation {conversation.id}, user_text: '{user_text[:50]}...'"
    )
    llm = get_gemini_llm()
    output_parser = StrOutputParser()

    prev_summary = (
        conversation.summary
        or "This is the beginning of your conversation with Dormie."
    )

    # 1. Retrieve relevant documents from vector store
    logger.info("Searching vector store for relevant documents...")
    user_text_with_summary = f"{prev_summary}\n\nUser's message: {user_text}"  # Include summary in the search query
    retrieved_docs = search_vectorstore(user_text_with_summary)
    context_for_prompt = format_retrieved_docs(retrieved_docs)
    logger.debug(f"Retrieved context for prompt: {context_for_prompt}")

    # build last 6 messages snippet
    last_msgs = Message.objects.filter(conversation=conversation).order_by(
        "-timestamp"
    )[
        :6
    ]  # most recent first
    recent_lines = [
        f"{msg.sender.capitalize()}: {msg.text}"
        for msg in reversed(last_msgs)  # oldest to newest
    ]
    recent_messages = "\n".join(recent_lines)
    # single chain: response + summary
    prompt = PromptTemplate(
        input_variables=[
            "conversation_summary",
            "retrieved_context",
            "user_message",
            "recent_messages",
            "current_date",
        ],
        template=BASE_PROMPT_TEMPLATE,
    )
    chain = prompt | llm | output_parser
    raw = chain.invoke(
        {
            "conversation_summary": prev_summary,
            "retrieved_context": context_for_prompt,
            "user_message": user_text,
            "recent_messages": recent_messages,
            "current_date": datetime.now().date(),
        }
    ).strip()

    # print(
    #     "Raw LLM output before manual fence crossing:",
    #     raw,
    # )  # Debugging line to see raw output
    print("RAW ENDED HERE")  # Debugging line to see type of raw
    print("")

    # strip markdown code fences (``` or ```json)
    lines = raw.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].lstrip().startswith("```"):
        lines = lines[:-1]
    raw = "\n".join(lines).strip()

    # parse JSON from model
    try:
        print(
            "Raw LLM output after manual fence crossing:",
            raw,
        )  # Debugging line to see raw output
        # print("RAW ENDED HERE")  # Debugging line to see type of raw
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Failed to parse LLM output as JSON: %s", raw)
        data = {
            "reply": "Exception Occured: Apparantly model failed to respond correctly",
            "summary": prev_summary,
        }

    bot_reply = data.get("reply", "").strip()
    new_summary = data.get("summary", "").strip()

    # save messages and summary
    Message.objects.create(conversation=conversation, sender="user", text=user_text)
    Message.objects.create(conversation=conversation, sender="bot", text=bot_reply)
    conversation.summary = new_summary
    conversation.save(update_fields=["summary", "updated_at"])
    return bot_reply
