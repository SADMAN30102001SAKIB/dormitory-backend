import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from django.conf import settings
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from .llm_services import get_gemini_llm
from .models import Conversation, Message
from .search_agent import run_search_agent
from .vectorstore_utils import search_vectorstore
from users.models import Profile, UserMemory

logger = logging.getLogger(__name__)

# Create a separate debug logger for LLM pipeline debugging
debug_logger = logging.getLogger("llm_debug")
debug_logger.setLevel(logging.DEBUG)

# Create file handler for debug logs (if not already created)
if not debug_logger.handlers:
    # Create the directory if it doesn't exist
    log_dir = os.path.join(
        os.path.dirname(__file__), "..", "developersResources", "LLM"
    )
    os.makedirs(log_dir, exist_ok=True)

    log_file_path = os.path.join(log_dir, "llm_debug.log")
    debug_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    debug_handler.setLevel(logging.DEBUG)
    debug_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    debug_handler.setFormatter(debug_formatter)
    debug_logger.addHandler(debug_handler)
    debug_logger.propagate = False  # Don't send to parent loggers


def format_web_results(docs: list) -> str:
    """Formats the retrieved documents from a web search for inclusion in the prompt."""
    if not docs:
        return "No relevant information found from web search."

    formatted_docs = []
    for i, doc in enumerate(docs):
        result = doc.get("result", "")
        query = doc.get("query", "")

        entry = f"External Context {i+1} (From query: '{query}'):\n{result}"
        formatted_docs.append(entry)

    return "\n\n".join(formatted_docs)


# YOU SHOULD ENSURE THE RETRIEVED CONTEXT IS RELAVENT TO THE USER'S UNIVERSITY/LOCATION/CURRENT DATE.
# YOU CAN DO THIS BY FILTERING THE RETRIEVED CONTEXT, OR YOU CAN LET THE LLM DO IT. OR CAN WE QUERY THE VECTOR STORE WITH USER'S UNIVERSITY/LOCATION/CURRENT DATE AS WELL. OR COMBINE ALL THESE METHODS.
BASE_PROMPT_TEMPLATE = """
You are Dormie, a friendly and empathetic academic advisor and mental health counsellor for university students.
If the query is mental health or emotional support related, be empathetic and perspectival.
If it is an academic query, guide them like a knowledgeable and approachable senior.
Always maintain an informal, friendly, and understanding tone.
ACTIVELY engage in conversations and offer relevant suggestions in the flow of ongoing dialogue.

Always attach the internal link of the retrived information (in a bracket) in your response, so that the user can cross check it theirselves.
You also should make sure NOT to respond with an outdated information, so check the date of the retrived information and make sure the response is relevant to the current date. Today's date is {current_date}.

Here is some information about the user you are talking to:
---
{user_profile}
{user_memory}
---

Previous conversation summary of this specific conversation:
---
{conversation_summary}
---

Recent chat history for this specific conversation:
---
{recent_messages}
---

User's very latest message waiting for your response:
---
{user_message}
---

Use the following context to answer the user's question. The context is sourced from internal university data and external web searches. Use the information that is most relevant to the user's query and the current date. If no context is provided, rely on your general knowledge.
---
{retrieved_context}
---

You have three jobs. Your primary task is to respond to the user's latest message based on the conversation history and any relevant information given above. Secondly, you will also provide a summary of the entire conversation so far, which will be used to help you answer future questions on this conversation. Finally, you will provide a "memory" (if applicable, otherwise keep the value of the key an empty string) of the user's key life events, plans, aspirations or anything they mention (strictly) in their latest message that might help you personalize your response better across conversations.

You MUST respond STRICTLY in VALID JSON format (NOT even ```json ``` these code fences) with three keys: 'reply', 'summary', and 'memory'.
"""


def format_retrieved_docs(docs: list) -> str:
    """Formats the retrieved documents for inclusion in the prompt."""
    if not docs:
        return ""

    formatted_docs = []
    for i, doc in enumerate(docs):
        content = doc.page_content
        metadata = doc.metadata
        source_type = metadata.get("source_type", "document")
        title = metadata.get("title", "")
        author = metadata.get("author_username", "N/A")
        created_at = metadata.get("created_at", "Unknown date")
        url = metadata.get("url", "Not Found")

        entry = f"Internal Context {i+1} (Source: {source_type}"
        if title:
            entry += f", Title: '{title}'"
        entry += (
            f", Author: {author}, Date Created: {created_at}, URL: {url}):\n{content}"
        )
        formatted_docs.append(entry)

    return "\n\n".join(
        formatted_docs
    )  # joins all formatted entries in the list with double newlines


def generate_bot_response(conversation: Conversation, user_text: str) -> str:
    debug_logger.info("=" * 80)
    debug_logger.info(f"🚀 STARTING LLM PIPELINE for conversation {conversation.id}")
    debug_logger.info(f"📝 User input: {user_text}")
    debug_logger.info("=" * 80)

    logger.info(
        f"Generating bot response for conversation {conversation.id}, user_text: '{user_text[:50]}...'"
    )
    llm = get_gemini_llm()
    output_parser = StrOutputParser()

    user = conversation.user
    try:
        profile = Profile.objects.get(user=user)
        profile_info_parts = []
        if profile.bio:
            profile_info_parts.append(f"Bio: {profile.bio}")
        if profile.about_me:
            profile_info_parts.append(f"About Me: {profile.about_me}")
        if profile.gender:
            profile_info_parts.append(f"Gender: {profile.get_gender_display()}")
        if profile.address:
            profile_info_parts.append(f"Address: {profile.address}")

        # Education
        educations = profile.educations.all()
        if educations:
            education_details = []
            for edu in educations:
                institution_name = (
                    edu.institution.name if edu.institution else "an institution"
                )
                start_str = (
                    edu.start_date.strftime("%Y-%m-%d") if edu.start_date else "N/A"
                )
                end_str = (
                    edu.end_date.strftime("%Y-%m-%d") if edu.end_date else "Present"
                )
                batch_year = f", Batch: {edu.series}" if edu.series else ""

                detail = f"{edu.degree} in {edu.major} from {institution_name} batch of {batch_year} from ({start_str} to {end_str})"
                education_details.append(detail)
            if education_details:
                profile_info_parts.append("Education:\n" + "\n".join(education_details))

        # Work Experience
        work_experiences = profile.work_experiences.all()
        if work_experiences:
            work_details = []
            for work in work_experiences:
                organization_name = (
                    work.organization.name if work.organization else "an organization"
                )
                start_str = work.start_date.strftime("%Y-%m-%d")
                end_str = (
                    work.end_date.strftime("%Y-%m-%d") if work.end_date else "Present"
                )
                detail = (
                    f"- {work.title} at {organization_name} ({start_str} to {end_str})"
                )
                work_details.append(detail)
            if work_details:
                profile_info_parts.append(
                    "Work Experience:\n" + "\n".join(work_details)
                )

        # Achievements
        achievements = profile.achievements.all()
        if achievements:
            achievement_details = []
            for ach in achievements:
                date_str = ach.date_received.strftime("%Y-%m-%d")
                detail = f"- {ach.title} from {ach.issuer} ({date_str})"
                achievement_details.append(detail)
            if achievement_details:
                profile_info_parts.append(
                    "Achievements:\n" + "\n".join(achievement_details)
                )

        profile_info = "\n\n".join(profile_info_parts)
        if not profile_info:
            profile_info = "No profile information available."

    except Profile.DoesNotExist:
        profile_info = "No profile information available."

    debug_logger.info("👤 USER PROFILE EXTRACTED:")
    debug_logger.info(f"{profile_info}")
    debug_logger.info("-" * 50)  # retrieve all memories for user and combine
    user_memories = UserMemory.objects.filter(user=user).order_by("created_at")
    if user_memories.exists():
        memory_content = "\n".join(mem.content for mem in user_memories)
    else:
        memory_content = "No memories stored yet."

    debug_logger.info("🧠 USER MEMORIES EXTRACTED:")
    debug_logger.info(f"{memory_content}")
    debug_logger.info("-" * 50)

    prev_summary = (
        conversation.summary
        or "This is the beginning of your conversation with Dormie."
    )

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

    # Parallel execution of vectorstore search and web search
    retrieved_docs = []
    web_search_results = []

    def search_vectorstore_task():
        nonlocal retrieved_docs
        logger.info("Starting vector store search...")
        user_text_with_summary = (
            f"User's message: {user_text}\n\nPrevious Summary: {prev_summary}"
        )
        debug_logger.info("🔍 VECTOR STORE SEARCH QUERY:")
        debug_logger.info(f"{user_text_with_summary}")
        debug_logger.info("-" * 50)
        retrieved_docs = search_vectorstore(user_text_with_summary)
        logger.info("Finished vector store search.")

    def run_search_agent_task():
        nonlocal web_search_results
        logger.info("Starting web search agent...")
        web_search_query = f"User message: {user_text}\n\nConversation Summary: {prev_summary}\n\nRecent Messages:\n{recent_messages}"
        web_search_results = run_search_agent(web_search_query)
        logger.info("Finished web search agent.")

    with ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(search_vectorstore_task)
        executor.submit(run_search_agent_task)

    internal_context = format_retrieved_docs(retrieved_docs)
    debug_logger.info("📚 RETRIEVED CONTEXT FROM VECTOR STORE:")
    debug_logger.info(f"{internal_context}")
    debug_logger.info("-" * 50)

    web_context = format_web_results(web_search_results)
    if web_context:
        debug_logger.info("🌐 RETRIEVED CONTEXT FROM WEB SEARCH:")
        debug_logger.info(f"{web_context}")
        debug_logger.info("-" * 50)

    # Combine contexts intelligently
    all_contexts = []
    if retrieved_docs:  # Check if the search returned any documents
        all_contexts.append(
            f"--- INTERNAL CONTEXT (from university posts & comments) ---\n{internal_context}"
        )
    if web_search_results:  # Check if the web search returned any results
        all_contexts.append(
            f"--- EXTERNAL CONTEXT (from web search) ---\n{web_context}"
        )

    if not all_contexts:
        context_for_prompt = (
            "No specific context was retrieved. Rely on general knowledge."
        )
    else:
        context_for_prompt = "\n\n".join(all_contexts)

    logger.debug(f"Final combined context for prompt: {context_for_prompt}")

    # single chain: response + summary
    prompt = PromptTemplate(
        input_variables=[
            "conversation_summary",
            "retrieved_context",
            "user_message",
            "recent_messages",
            "current_date",
            "user_profile",
            "user_memory",
        ],
        template=BASE_PROMPT_TEMPLATE,
    )
    chain = prompt | llm | output_parser

    # Debug: Log the complete prompt that will be sent to LLM
    prompt_data = {
        "conversation_summary": prev_summary,
        "retrieved_context": context_for_prompt,
        "user_message": user_text,
        "recent_messages": recent_messages,
        "current_date": datetime.now().date(),
        "user_profile": profile_info,
        "user_memory": memory_content,
    }

    debug_logger.info("🤖 COMPLETE PROMPT BEING SENT TO LLM:")
    debug_logger.info(prompt.format(**prompt_data))
    debug_logger.info("-" * 50)

    raw = chain.invoke(prompt_data).strip()

    debug_logger.info("🎯 RAW LLM RESPONSE (before processing):")
    debug_logger.info(f"{raw}")
    debug_logger.info("-" * 50)

    # print(
    #     "Raw LLM output before manual fence crossing:",
    #     raw,
    # )  # Debugging line to see raw output
    # print("RAW ENDED HERE")  # Debugging line to see type of raw
    # print("")    # strip markdown code fences (``` or ```json)
    lines = raw.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].lstrip().startswith("```"):
        lines = lines[:-1]
    raw = "\n".join(lines).strip()

    debug_logger.info("✂️ CLEANED RAW RESPONSE (after removing code fences):")
    debug_logger.info(f"{raw}")
    debug_logger.info("-" * 50)

    # parse JSON from model
    try:
        data = json.loads(raw)
        debug_logger.info("✅ SUCCESSFULLY PARSED JSON:")
        debug_logger.info(f"{json.dumps(data, indent=2)}")
        debug_logger.info("-" * 50)
    except json.JSONDecodeError:
        logger.exception("Failed to parse LLM output as JSON: %s", raw)
        debug_logger.error("❌ FAILED TO PARSE JSON - USING FALLBACK:")
        debug_logger.error(f"Raw response: {raw}")
        debug_logger.error("-" * 50)
        data = {
            "reply": "Exception Occured: Apparantly model failed to respond correctly",
            "summary": prev_summary,
            "memory": memory_content,
        }

    # print(data)

    # Safely extract and strip 'reply'
    raw_reply = data.get("reply")
    if isinstance(raw_reply, str):
        bot_reply = raw_reply.strip()
    else:
        if (
            raw_reply is not None
        ):  # It's not a string and not None, so it's an unexpected type
            logger.warning(
                f"LLM 'reply' field was type {type(raw_reply)} not string: {raw_reply}. Using empty string."
            )
        bot_reply = ""  # Default to empty string if not a string or if None

    # Safely extract and strip 'summary'
    raw_summary = data.get("summary")
    if isinstance(raw_summary, str):
        new_summary = raw_summary.strip()
    else:
        if raw_summary is not None:
            logger.warning(
                f"LLM 'summary' field was type {type(raw_summary)} not string: {raw_summary}. Using empty string."
            )
        new_summary = ""  # Default to empty string if not a valid string

    # Safely extract and strip 'memory'
    raw_memory = data.get("memory")
    if isinstance(raw_memory, str):
        new_memory = raw_memory.strip()
    elif isinstance(raw_memory, dict):  # Handle the problematic dict case
        logger.warning(
            f"LLM 'memory' field was a dict: {raw_memory}. Using empty string."
        )
        new_memory = ""
    elif raw_memory is None:  # Key was present but value was None, or key not present
        new_memory = ""
    else:  # Handle other unexpected types
        logger.warning(
            f"LLM 'memory' field was type {type(raw_memory)} not string, dict, or None: {raw_memory}. Using empty string."
        )
        new_memory = ""

    debug_logger.info("📋 FINAL EXTRACTED VALUES:")
    debug_logger.info(f"Bot Reply: {bot_reply}")
    debug_logger.info(f"New Summary: {new_summary}")
    debug_logger.info(f"New Memory: {new_memory}")
    debug_logger.info("-" * 50)

    # save messages and summary
    Message.objects.create(conversation=conversation, sender="user", text=user_text)
    Message.objects.create(conversation=conversation, sender="bot", text=bot_reply)
    conversation.summary = new_summary
    conversation.save(update_fields=["summary", "updated_at"])

    # Save user memory (create new memory entry)
    if new_memory != "":
        UserMemory.objects.create(user=user, content=new_memory)
        debug_logger.info("💾 NEW MEMORY SAVED TO DATABASE")

    debug_logger.info("🏁 LLM PIPELINE COMPLETED SUCCESSFULLY")
    debug_logger.info("=" * 80)
    debug_logger.info("")  # Add blank line for readability

    return bot_reply
