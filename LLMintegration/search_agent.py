import logging
import json
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from LLMintegration.llm_services import get_gemini_llm

logger = logging.getLogger(__name__)

# --- Prompts ---
SEARCH_AGENT_PROMPT_TEMPLATE = """
You are an expert routing and query generation assistant.
Your task is to analyze the user's latest message in the context of the conversation history and determine if a web search is necessary to provide a good answer.
The user is interacting with a chatbot that has access to internal data about university life, posts, comments, and user profiles from a social platform.
If the question can be answered sufficiently with this internal data or the model's general knowledge, no web search is needed.
A web search is required for questions about real-time information, very recent events, or broad general knowledge not available in the internal data.

Based on the full context provided below, you must return a JSON object with two keys:
1. "web_search_required": A boolean value (true or false).
2. "queries": A list of 1 to 2 concise and effective web search queries if `web_search_required` is true. If `web_search_required` is false, this should be an empty list.

Full Context:
{full_context}
"""


# --- Chains ---
def get_search_generation_chain():
    """Returns a chain that determines if search is needed and generates queries."""
    llm = get_gemini_llm()
    prompt = PromptTemplate.from_template(SEARCH_AGENT_PROMPT_TEMPLATE)
    return prompt | llm | StrOutputParser()


# --- Search Tool Factory ---
def get_web_search_tool():
    """Initializes and returns the Tavily search tool."""
    # Tavily automatically uses the TAVILY_API_KEY from environment variables
    return TavilySearchResults(max_results=3)


# --- Main Orchestrator ---
def run_search_agent(full_context: str) -> list:
    """
    Orchestrates the process of query generation and web search based on a single LLM call.
    Returns a list of search results, or an empty list if no search is needed.
    """
    # logger.info(f"Search Agent: Received context - '{full_context}'")

    # 1. Decide if web search is needed and generate queries in a single call
    search_generation_chain = get_search_generation_chain()
    web_search_required = False
    queries = []
    try:
        response_str = search_generation_chain.invoke({"full_context": full_context})

        # Strip any code fences
        lines = response_str.strip().splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
        response_data = json.loads(cleaned)

        web_search_required = response_data.get("web_search_required", False)
        queries = response_data.get("queries", []) if web_search_required else []

        logger.info(
            f"Search Agent: Web search required: {web_search_required}, Queries: {queries}"
        )

    except Exception as e:
        logger.error(f"Search Agent: Parsing failed, no search. Error: {e}")

    if not web_search_required or not queries:
        return []

    # 2. Execute web search with Tavily
    logger.info("Search Agent: Executing web search with Tavily...")
    search_tool = get_web_search_tool()
    results = []
    for q in queries:
        try:
            r = search_tool.run(q)
            if r:
                results.append({"query": q, "result": r})
                logger.info(f"Search Agent: Got results for '{q}'")
        except Exception as err:
            logger.error(f"Search Agent: Error for '{q}': {err}")
    return results
