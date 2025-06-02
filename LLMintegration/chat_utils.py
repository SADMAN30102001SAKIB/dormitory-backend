import logging
import os

from django.conf import settings
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from .models import Conversation, Message
from .vectorstore_utils import search_vectorstore

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


BASE_PROMPT_TEMPLATE = """
You are Dormie, a friendly and empathetic academic advisor and mental health counsellor for university students.
If the query is mental health/emotional support related, be empathetic and perspectival.
If it is an academic query, guide them like a knowledgeable and approachable senior.
Always maintain an informal, friendly, and understanding tone.

Previous conversation summary:
{conversation_summary}

Potentially relevant information from university posts or comments (use this information if it directly helps answer the user's current question, otherwise ignore it):
---
{retrieved_context}
---

User's latest message:
{user_message}

Please respond to the user's latest message.
If the "Potentially relevant information" is useful and directly answers the user's question, integrate it naturally into your response. Do not explicitly mention "Based on the retrieved information..." or "I found a post...".
If the retrieved information is not relevant or doesn't help, answer based on your general knowledge and the conversation history.
If no relevant information was found (i.e., "retrieved_context" is empty or says "No relevant information found"), just proceed with a general answer.
"""

SUMMARY_PROMPT_TEMPLATE = """
You are an AI that writes concise summaries of therapeutic/chatbot conversations.
Maintain mention of academic guidance and mental health context.

Conversation snippet:
{snippet}

Produce a short summary capturing the essence.
"""
#    You could also store every single message in memory directly (ConversationBufferMemory), but that can get costly. For now, summary is fine.


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

        entry = f"Context {i+1} (Source: {source_type}"
        if title:
            entry += f", Title: '{title}'"
        entry += f", Author: {author}):\n{content}"
        formatted_docs.append(entry)

    return "\n\n".join(formatted_docs)


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
    retrieved_docs = search_vectorstore(user_text, k=3)  # Retrieve top 3 documents
    context_for_prompt = format_retrieved_docs(retrieved_docs)
    logger.debug(f"Retrieved context for prompt: {context_for_prompt}")

    # 2. Create the main generation chain using LCEL
    prompt = PromptTemplate(
        input_variables=["conversation_summary", "retrieved_context", "user_message"],
        template=BASE_PROMPT_TEMPLATE.strip(),
    )

    chain = prompt | llm | output_parser

    logger.info("Invoking LLM chain...")
    bot_reply = chain.invoke(
        {
            "conversation_summary": prev_summary,
            "retrieved_context": context_for_prompt,
            "user_message": user_text,
        }
    ).strip()
    logger.info(f"LLM generated reply: '{bot_reply[:50]}...'")

    # Save messages (User and Bot)
    Message.objects.create(conversation=conversation, sender="user", text=user_text)
    Message.objects.create(conversation=conversation, sender="bot", text=bot_reply)
    logger.info("User and Bot messages saved.")

    if not conversation.title and user_text:
        conversation.title = user_text.strip()[:50]
        # conversation.save(update_fields=["title"]) # Will be saved with summary update
        logger.info(f"Conversation title set to: '{conversation.title}'")

    # 3. Re-summarize the conversation
    # Prepare snippet for summarization: include user message and bot reply
    last_msgs_for_snippet = Message.objects.filter(conversation=conversation).order_by(
        "-timestamp"
    )[
        :6
    ]  # Get last 6 messages for snippet context
    snippet_lines = []
    for msg in reversed(last_msgs_for_snippet):  # Chronological order
        snippet_lines.append(f"{msg.sender.capitalize()}: {msg.text}")
    snippet_for_summary = "\n".join(snippet_lines)

    summary_context_for_llm = prev_summary
    if prev_summary == "This is the beginning of your conversation with Dormie.":
        # For the very first summary, don't pass the greeting as "previous summary"
        summary_context_for_llm = "This is the first exchange in the conversation."

    full_for_summary = f"Existing Summary (if any): {summary_context_for_llm}\n\nMost Recent Exchange to Summarize:\n{snippet_for_summary}"

    logger.info("Generating new conversation summary...")
    summary_prompt_template = PromptTemplate(
        input_variables=["snippet"], template=SUMMARY_PROMPT_TEMPLATE.strip()
    )
    summary_chain = summary_prompt_template | llm | output_parser
    new_summary = summary_chain.invoke({"snippet": full_for_summary}).strip()
    logger.info(f"New summary: '{new_summary[:50]}...'")

    conversation.summary = new_summary
    update_fields = ["summary", "updated_at"]
    if not conversation.title and user_text:  # if title was just set
        conversation.title = (
            user_text.strip()[:50] or "Conversation"
        )  # Ensure title isn't empty
        update_fields.append("title")

    conversation.save(update_fields=update_fields)
    logger.info("Conversation summary and updated_at field saved.")

    return bot_reply
