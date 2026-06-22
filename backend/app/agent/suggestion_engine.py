"""
Cognitive Database Agent - Schema-Aware Suggestion Engine
=========================================================
Generates intelligent follow-up query suggestions after each agent response.

THEORY: Proactive Guidance
--------------------------
Non-technical users often don't know what to ask next after receiving a query result.
By leveraging the LLM and RAG schema context, we can proactively suggest relevant
follow-up questions that:
1. Build on the current query (drill down, filter, compare)
2. Are feasible given the actual schema
3. Respect the user's role and permissions
4. Guide exploration of the data

This transforms the UI from reactive (answer questions) to proactive (guide exploration).
"""

import logging
import json
import re
from typing import List, Dict, Optional, Any

from backend.app.agent.rag_retriever import get_context_for_query

logger = logging.getLogger(__name__)


# ================================
# Suggestion Prompt Template
# ================================
SUGGESTION_PROMPT_TEMPLATE = """You are a database query assistant helping users explore data.

Based on the user's current query and database schema, suggest exactly 3 natural-language follow-up questions.

Rules:
- Questions must be natural language (NOT SQL)
- Questions should build on the current query: drill-down, compare, filter, or show trends
- Questions must be feasible given the schema context provided
- Role restrictions: {role} (viewers cannot modify data; managers only access region: {region})
- Return ONLY a valid JSON array. No explanations, no markdown, no extra text.
- JSON format: [{{"question": "...", "category": "drill-down|compare|trend|filter"}}]
- Categories: "drill-down" (more detail), "compare" (vs something), "trend" (over time), "filter" (narrow scope)

Schema context:
{schema_context}

User's current query: {user_query}

Brief summary of results: {result_summary}

JSON array (3 suggestions):"""


# ================================
# Internal Helpers
# ================================
def _extract_result_summary(agent_response: str) -> str:
    """
    Extract a brief, clean summary from the agent response for context.
    Strips VIZ_HINT blocks and truncates to keep prompt size manageable.
    """
    # Remove VIZ_HINT blocks
    clean = re.sub(r'\[VIZ_HINT\].*?\[/VIZ_HINT\]', '', agent_response, flags=re.DOTALL)
    # Normalize whitespace
    clean = ' '.join(clean.split())
    # Truncate to first 400 chars
    return clean[:400].strip()


def _parse_suggestions_json(response_text: str) -> List[Dict[str, str]]:
    """
    Parse suggestions JSON from LLM response.

    The LLM may return the array directly or embed it in text.
    We search for the first valid JSON array in the response.
    """
    try:
        # Try direct parse first
        parsed = json.loads(response_text.strip())
        if isinstance(parsed, list):
            return _validate_suggestions(parsed)
    except (json.JSONDecodeError, ValueError):
        pass

    # Fallback: find JSON array within response text
    try:
        json_match = re.search(r'\[.*?\]', response_text, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, list):
                return _validate_suggestions(parsed)
    except (json.JSONDecodeError, AttributeError):
        pass

    logger.warning(f"Could not parse suggestions JSON from: {response_text[:200]}")
    return []


def _validate_suggestions(suggestions: list) -> List[Dict[str, str]]:
    """Validate and normalize suggestion structure. Returns at most 3 valid suggestions."""
    valid_categories = {'drill-down', 'compare', 'trend', 'filter'}
    valid = []

    for item in suggestions:
        if not isinstance(item, dict) or 'question' not in item:
            continue
        question = str(item['question']).strip()
        if not question:
            continue
        category = str(item.get('category', 'drill-down')).strip()
        if category not in valid_categories:
            category = 'drill-down'
        valid.append({'question': question, 'category': category})

    return valid[:3]


# ================================
# Main Public Function
# ================================
def generate_follow_up_suggestions(
    user_query: str,
    agent_response: str,
    role: str,
    region: Optional[str],
    llm: Any,
) -> List[Dict[str, str]]:
    """
    Generate 2-3 schema-aware follow-up query suggestions.

    Uses the RAG retriever to surface relevant schema context, then asks the LLM
    to suggest contextually appropriate follow-up questions.

    Args:
        user_query:      The user's original natural-language query.
        agent_response:  The agent's response/answer text.
        role:            User's database role ('admin', 'manager', 'viewer').
        region:          User's region (only relevant for 'manager' role).
        llm:             An initialized LangChain chat model instance.

    Returns:
        A list of suggestion dicts: [{"question": "...", "category": "..."}]
        Returns an empty list on any error (graceful degradation).
    """
    try:
        # Retrieve schema context relevant to this query
        schema_context = get_context_for_query(user_query, include_examples=False)

        # Build result summary from agent response
        result_summary = _extract_result_summary(agent_response)

        # Compose prompt
        prompt = SUGGESTION_PROMPT_TEMPLATE.format(
            role=role,
            region=region or "N/A",
            schema_context=schema_context[:1800],  # Limit context size
            user_query=user_query,
            result_summary=result_summary or "No specific result summary available.",
        )

        # Call LLM - use HumanMessage for compatibility with chat models
        from langchain_core.messages import HumanMessage
        response = llm.invoke([HumanMessage(content=prompt)])

        response_text = (
            response.content if hasattr(response, 'content') else str(response)
        )
        logger.debug(f"Suggestion LLM raw response: {response_text[:300]}")

        # Parse and return suggestions
        suggestions = _parse_suggestions_json(response_text)
        logger.info(f"Generated {len(suggestions)} follow-up suggestions for query: '{user_query[:60]}'")
        return suggestions

    except Exception as e:
        # Graceful degradation: suggestions are non-critical
        logger.warning(f"Failed to generate follow-up suggestions: {e}")
        return []


# ================================
# Export public API
# ================================
__all__ = [
    "generate_follow_up_suggestions",
]
