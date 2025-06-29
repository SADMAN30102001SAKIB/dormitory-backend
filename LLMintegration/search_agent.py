import logging
import json
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from LLMintegration.llm_services import get_gemini_llm

logger = logging.getLogger(__name__)

# --- Prompts ---

SEARCH_AGENT_PROMPT_TEMPLATE = """
You are an expert routing and query generation assistant.
Your task is to analyze a user's question and determine if a web search is necessary to provide a good answer.
The user is interacting with a chatbot that has access to internal data about university life, posts, comments, and user profiles from a social platform.
If the question can be answered sufficiently with this internal data or the model's general knowledge, no web search is needed.
A web search is required for questions about real-time information, very recent events, or broad general knowledge not available in the internal data.

Based on the user's question, you must return a JSON object with two keys:
1. "web_search_required": A boolean value (true or false).
2. "queries": A list of 1 to 3 concise and effective web search queries if `web_search_required` is true. If `web_search_required` is false, this should be an empty list.

User Question: {user_question}
"""

# --- Chains ---


def get_search_generation_chain():
    """Returns a chain that determines if search is needed and generates queries."""
    llm = get_gemini_llm()
    prompt = PromptTemplate.from_template(SEARCH_AGENT_PROMPT_TEMPLATE)
    return prompt | llm | StrOutputParser()


# --- Search Tool ---


def get_web_search_tool():
    """Initializes and returns the DuckDuckGo search tool."""
    return DuckDuckGoSearchRun()


# --- Main Orchestrator ---


def run_search_agent(user_question: str) -> list:
    """
    Orchestrates the process of query generation and web search based on a single LLM call.
    Returns a list of search results, or an empty list if no search is needed.
    """
    logger.info(f"Search Agent: Received query - '{user_question}'")

    # 1. Decide if web search is needed and generate queries in a single call
    search_generation_chain = get_search_generation_chain()
    web_search_required = False
    queries = []
    try:
        response_str = search_generation_chain.invoke({"user_question": user_question})

        # Clean the response string, removing markdown code fences
        lines = response_str.strip().splitlines()
        if lines and lines[0].lstrip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].lstrip().startswith("```"):
            lines = lines[:-1]
        # The join should be with a newline character, not a literal newline in the code.
        cleaned_response_str = "\n".join(lines).strip()

        # Handle potential empty string after cleaning
        if not cleaned_response_str:
            raise json.JSONDecodeError("Cleaned response is empty.", "", 0)

        response_data = json.loads(cleaned_response_str)

        web_search_required = response_data.get("web_search_required", False)
        if web_search_required:
            queries = response_data.get("queries", [])

        logger.info(
            f"Search Agent: Web search required: {web_search_required}, Queries: {queries}"
        )

    except (json.JSONDecodeError, Exception) as e:
        logger.error(
            f"Search Agent: Error parsing search generation response. Defaulting to no web search. Error: {e}"
        )
        # On any exception, ensure we fallback to no search required.
        web_search_required = False
        queries = []

    if not web_search_required or not queries:
        logger.info("Search Agent: Web search not required or no queries generated.")
        return []

    # 2. Execute web search
    logger.info("Search Agent: Executing web search...")
    search_tool = get_web_search_tool()
    all_results = []
    for query in queries:
        try:
            result = search_tool.run(query)
            if result and "No good DuckDuckGo Search results found" not in result:
                all_results.append({"query": query, "result": result})
                logger.info(f"Search Agent: Found results for query '{query}'")
        except Exception as e:
            logger.error(
                f"Search Agent: Error during web search for query '{query}': {e}"
            )

    logger.info(f"Search Agent: Finished with {len(all_results)} results.")
    return all_results
