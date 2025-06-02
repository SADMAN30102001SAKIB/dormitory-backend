import os

from django.conf import settings
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import Conversation, Message


def get_gemini_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash-preview-05-20",
        api_key=settings.GEMINI_API_KEY,  # set environment variable or Django settings
        temperature=0.7,  # higher values = more creative responses
        # max_output_tokens=512,  # Adjust based on your needs
        top_p=0.95,  # nucleus sampling: cumulative prob mass
        top_k=40,  # top-k sampling: restrict to k candidates
    )


BASE_PROMPT_TEMPLATE = """
You serve as a academic advisor and mental health counsellor for students in a university. If it is an mental health/emotional support related query, be empathetic and perspectival. If it is an academic query, guide them through like a lovable senior bhai. 
In both cases, be informal and friendly, like a really close understanding friend.

Previous conversation summary:
{conversation_summary}

User's latest message:
{user_message}

Please respond compassionately, offering academic advice or emotional support as needed.
"""

SUMMARY_PROMPT_TEMPLATE = """
You are an AI that writes concise summaries of therapeutic/chatbot conversations.
Maintain mention of academic guidance and mental health context.

Conversation snippet:
{snippet}

Produce a short summary capturing the essence.
"""
#    You could also store every single message in memory directly (ConversationBufferMemory), but that can get costly. For now, summary is fine.


def generate_bot_response(conversation: Conversation, user_text: str) -> str:
    """
    Generates a bot response, updates the conversation history, re-summarizes the conversation and saves it to the database.
    """
    llm = get_gemini_llm()
    output_parser = StrOutputParser()

    prev_summary = conversation.summary or "No prior summary."

    prompt = PromptTemplate(
        input_variables=["conversation_summary", "user_message"],
        template=BASE_PROMPT_TEMPLATE.strip(),
    )

    chain = prompt | llm | output_parser

    bot_reply = chain.invoke(
        {"conversation_summary": prev_summary, "user_message": user_text}
    ).strip()

    # Save the new user message and bot reply to the DB
    Message.objects.create(conversation=conversation, sender="user", text=user_text)
    Message.objects.create(conversation=conversation, sender="bot", text=bot_reply)

    # If this is the first message and title is empty, set title from user text
    if not conversation.title:
        conversation.title = user_text.strip()[:50] or "Conversation"
        conversation.save(update_fields=["title"])

    # Re-summarize the conversation: include previous summary + last 10 messages
    last_msgs = Message.objects.filter(conversation=conversation).order_by(
        "-timestamp"
    )[:10]
    snippet_lines = []
    for msg in reversed(last_msgs):
        snippet_lines.append(f"{msg.sender.capitalize()}: {msg.text}")
    snippet = "\n".join(snippet_lines)
    full_for_summary = (
        f"So Far Entire Chat Summary: {prev_summary}\nRecent messages:\n{snippet}"
    )

    # Define the summarization chain using LCEL
    summary_prompt = PromptTemplate(
        input_variables=["snippet"], template=SUMMARY_PROMPT_TEMPLATE.strip()
    )
    # LCEL definition for summary: summary_prompt -> llm -> output_parser
    summary_chain = summary_prompt | llm | output_parser

    # Get the new summary using invoke
    new_summary = summary_chain.invoke({"snippet": full_for_summary}).strip()
    conversation.summary = new_summary
    conversation.save(
        update_fields=["summary", "updated_at"]
    )  # for Update -> instance.save(). for create -> instance = Model.objects.create() or Model.objects.get_or_create()

    return bot_reply
