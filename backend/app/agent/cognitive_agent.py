"""
Cognitive Database Agent - Main Agent Logic
===========================================
Implements the "brain" of the system using LangChain and Google Gemini.

THEORY: ReAct Pattern (Reasoning + Acting)
-------------------------------------------
The ReAct pattern enables agents to:
1. REASON about what needs to be done (plan steps)
2. ACT by selecting and using appropriate tools
3. OBSERVE the results
4. REPEAT until the task is complete

This creates a thought-action loop that enables complex multi-step operations.

Example flow for "Archive sales from 2022":
- Thought: I need to move 2022 sales to archive table
- Action: Use run_query to SELECT 2022 sales
- Observation: Found 16 records
- Thought: Now I need to INSERT these into sales_archive
- Action: Use run_insert with the data
- Observation: Insert successful
- Thought: Finally DELETE from sales_data
- Action: Use run_delete
- Observation: Deleted 16 records
- Final Answer: Successfully archived 16 sales records from 2022
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from langchain.agents import AgentExecutor, create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
import asyncio
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.agents import AgentAction, AgentFinish

from backend.app.core.config import settings
from backend.app.agent.tools import get_all_tools, set_agent_context
from backend.app.agent.rag_retriever import get_context_for_query
from backend.app.agent.suggestion_engine import generate_follow_up_suggestions

logger = logging.getLogger(__name__)


# ================================
# Agent Prompt Template
# ================================
AGENT_PROMPT_TEMPLATE = """You are a Cognitive Database Agent with expertise in PostgreSQL and data management.
Your role is to help users interact with a database that has Row-Level Security (RLS) enabled.

IMPORTANT SECURITY CONTEXT:
- You are currently operating with the role: {role}
- This role determines what data you can access and modify
- Row-Level Security (RLS) policies are enforced at the database level
- If you attempt an unauthorized operation, you will receive a permission denied error
- Always inform the user about your current role and its limitations

ROLE CAPABILITIES:
- db_admin: Full access to all data and operations
- db_manager: Can view and modify data in their assigned region only (region: {region})
- db_viewer: Read-only access to all data, cannot modify anything

AVAILABLE TOOLS:
{tools}

RELEVANT SCHEMA INFORMATION:
{context}

TASK EXECUTION GUIDELINES:
1. **Multi-Step Planning**: For complex tasks, break them down into clear steps
2. **Schema First**: Always check the schema before writing queries
3. **Security Awareness**: Remember your role's limitations
4. **Error Handling**: If a query fails due to permissions, explain why to the user
5. **Transaction Safety**: For multi-step operations (like archiving), explain each step

VISUALIZATION GUIDANCE:
When your query returns tabular data, include a visualization hint in your Final Answer using this EXACT format:

[VIZ_HINT]
chart_type: <bar|line|area|pie|table>
x_axis: <column_name for x-axis>
y_axis: <comma-separated column names for y-axis>
reasoning: <one-line explanation of why this chart type fits>
[/VIZ_HINT]

Choose chart_type based on the SEMANTIC MEANING of the query:
- "trends", "over time", "growth" → line or area
- "distribution", "breakdown", "share" → pie (if ≤8 categories)
- "compare", "versus", "by region", "by category" → bar
- Large datasets (50+ rows) or complex/wide structure → table
- If no tabular data is returned, omit the [VIZ_HINT] block entirely

CRITICAL FORMATTING RULES:
- Action Input MUST be ONLY the required parameter - NO extra commentary or explanations
- Example CORRECT: Action Input: sales_data
- Example WRONG: Action Input: sales_data (assuming this is the table with sales information)
- DO NOT add parentheses, explanations, or assumptions to Action Input
- Keep Action Input minimal and exact

RESPONSE FORMAT:
Use the following format for your responses:

Question: the input question or task you must solve
Thought: your reasoning about what to do next
Action: the tool to use (must be one of [{tool_names}])
Action Input: the input to the tool
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original question

EXAMPLE - Multi-Step Operation:
Question: Archive all sales data from 2022
Thought: This requires three steps: 1) SELECT data, 2) INSERT into archive, 3) DELETE from main table. Let me start by getting the sales_data schema.
Action: get_schema
Action Input: sales_data
Observation: [schema details]
Thought: Now I'll query the 2022 sales data to see what we're working with
Action: run_query
Action Input: SELECT * FROM sales_data WHERE year = 2022
Observation: [16 records returned]
Thought: Now I'll insert these into sales_archive
Action: run_insert
Action Input: INSERT INTO sales_archive (original_id, year, quarter, amount, region, product, user_id, archived_by) SELECT id, year, quarter, amount, region, product, user_id, '{role}' FROM sales_data WHERE year = 2022
Observation: [insert successful]
Thought: Finally, delete from sales_data
Action: run_delete
Action Input: DELETE FROM sales_data WHERE year = 2022
Observation: [16 rows deleted]
Thought: I now know the final answer
Final Answer: Successfully archived 16 sales records from 2022. The data has been moved from sales_data to sales_archive.

Begin!

CONVERSATION HISTORY:
{chat_history}

Use this history to understand follow-up questions. If the user says "filter that", "show me more", 
"now by region", etc., refer to the previous query context.

Question: {input}
Thought: {agent_scratchpad}
"""


# ================================
# VIZ_HINT Parser
# ================================
def _parse_viz_hint(output: str) -> tuple:
    """
    Parse [VIZ_HINT]...[/VIZ_HINT] block from agent output.

    Returns:
        (clean_output, visualization_hint_dict | None)
        clean_output: the agent's text with the VIZ_HINT block stripped
        visualization_hint: dict with chart_type, x_axis, y_axis, reasoning or None
    """
    pattern = r'\[VIZ_HINT\](.*?)\[/VIZ_HINT\]'
    match = re.search(pattern, output, re.DOTALL)

    if not match:
        return output, None

    hint_text = match.group(1).strip()
    # Strip the VIZ_HINT block from the response text shown to users
    clean_output = re.sub(pattern, '', output, flags=re.DOTALL).strip()

    # Parse key: value pairs from hint block
    hint = {}
    for line in hint_text.split('\n'):
        line = line.strip()
        if ':' in line:
            key, _, value = line.partition(':')
            hint[key.strip()] = value.strip()

    # Validate required fields
    if 'chart_type' not in hint:
        return clean_output, None

    valid_chart_types = {'bar', 'line', 'area', 'pie', 'table'}
    chart_type = hint.get('chart_type', 'table').lower()
    if chart_type not in valid_chart_types:
        chart_type = 'table'  # Safe fallback (e.g. choropleth → table)

    visualization_hint = {
        'chart_type': chart_type,
        'x_axis': hint.get('x_axis', ''),
        'y_axis': hint.get('y_axis', ''),
        'reasoning': hint.get('reasoning', ''),
    }

    logger.info(f"Parsed VIZ_HINT: {visualization_hint}")
    return clean_output, visualization_hint


class StreamingCallback(BaseCallbackHandler):
    """Callback handler for streaming agent execution events to an asyncio.Queue."""

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self.queue = queue
        self.loop = loop

    def on_agent_action(self, action: AgentAction, **kwargs: Any) -> Any:
        self.loop.call_soon_threadsafe(
            self.queue.put_nowait,
            {"type": "thought", "content": action.log}
        )

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs: Any) -> Any:
        tool_name = serialized.get("name") or kwargs.get("name") or ""
        self.loop.call_soon_threadsafe(
            self.queue.put_nowait,
            {"type": "tool_start", "tool": tool_name, "input": input_str}
        )

    def on_tool_end(self, output: str, **kwargs: Any) -> Any:
        self.loop.call_soon_threadsafe(
            self.queue.put_nowait,
            {"type": "tool_result", "output": output}
        )

    def on_agent_finish(self, finish: AgentFinish, **kwargs: Any) -> Any:
        raw_output = finish.return_values.get("output", "")
        clean_output, viz_hint = _parse_viz_hint(raw_output)

        # Send the clean answer (without VIZ_HINT markup)
        self.loop.call_soon_threadsafe(
            self.queue.put_nowait,
            {"type": "final_answer", "content": clean_output}
        )

        # If LLM provided visualization guidance, stream it as a separate event
        if viz_hint:
            self.loop.call_soon_threadsafe(
                self.queue.put_nowait,
                {"type": "visualization_hint", "hint": viz_hint}
            )


# ================================
# Cognitive Agent Class
# ================================
class CognitiveAgent:
    """
    The main cognitive agent that orchestrates database operations.
    """

    def __init__(
        self,
        role: str = "viewer",
        region: Optional[str] = None,
        verbose: bool = None,
        memory: bool = True,
    ):
        """
        Initialize the cognitive agent.

        Args:
            role: Database role to use ('admin', 'manager', 'viewer')
            region: Region for manager role
            verbose: Enable verbose output (shows reasoning steps)
            memory: Enable conversation memory
        """
        self.role = role
        self.region = region
        self.verbose = verbose if verbose is not None else settings.agent_verbose

        # Set agent context for tools
        set_agent_context(role=role, region=region)

        # Initialize LLM based on provider
        if settings.llm_provider == "ollama":
            logger.info(f"Using Ollama LLM: {settings.llm_model}")
            self.llm = ChatOllama(
                model=settings.llm_model,
                base_url=settings.ollama_base_url,
                temperature=settings.llm_temperature,
            )
        else:
            logger.info(f"Using Google Gemini LLM: {settings.llm_model}")
            self.llm = ChatGoogleGenerativeAI(
                model=settings.llm_model,
                google_api_key=settings.google_api_key,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )

        # Get tools
        self.tools = get_all_tools()

        # Initialize memory if requested
        self.memory = None
        if memory:
            self.memory = ConversationBufferWindowMemory(
                k=10,
                memory_key="chat_history",
                input_key="input",
                output_key="output",
                return_messages=True,
            )

        # Create agent
        self.agent_executor = None
        self._create_agent()

        logger.info(f"Initialized CognitiveAgent (role={role}, region={region}, verbose={self.verbose})")

    def _create_agent(self):
        """Create the ReAct agent with tools and prompt."""
        # Format tool descriptions
        self.tools_description = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
        self.tool_names_str = ", ".join([tool.name for tool in self.tools])

        # Create prompt
        prompt = PromptTemplate(
            template=AGENT_PROMPT_TEMPLATE,
            input_variables=["input", "agent_scratchpad", "context", "tools", "tool_names", "chat_history"],
            partial_variables={
                "role": self.role,
                "region": self.region or "N/A",
            },
        )

        # Create ReAct agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

        # Create executor
        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=self.verbose,
            max_iterations=settings.agent_max_iterations,
            max_execution_time=settings.agent_max_execution_time,
            early_stopping_method="force",
            handle_parsing_errors=True,
            memory=self.memory,
            return_intermediate_steps=True,
        )

    def run(self, user_input: str, include_rag_context: bool = True) -> Dict[str, Any]:
        """
        Execute a user query using the agent.

        Args:
            user_input: User's natural language query
            include_rag_context: Whether to include RAG context in the prompt

        Returns:
            Dictionary with agent response and metadata
        """
        logger.info(f"Processing user input: '{user_input[:100]}...'")

        try:
            # Get RAG context if requested
            context = ""
            if include_rag_context:
                context = get_context_for_query(user_input)
                logger.debug(f"Retrieved RAG context: {len(context)} characters")

            # Run agent
            result = self.agent_executor.invoke(
                {
                    "input": user_input,
                    "context": context,
                    "tools": self.tools_description,
                    "tool_names": self.tool_names_str,
                }
            )

            # Format intermediate steps for frontend display
            formatted_steps = []
            logger.info(f"🔍 DEBUG: result.get('intermediate_steps') = {result.get('intermediate_steps', [])}")
            logger.info(f"🔍 DEBUG: Length of intermediate_steps = {len(result.get('intermediate_steps', []))}")

            for step in result.get("intermediate_steps", []):
                logger.info(f"🔍 DEBUG: Processing step: {step}")
                if len(step) >= 2:
                    action, observation = step[0], step[1]
                    logger.info(f"🔍 DEBUG: Action tool: {action.tool}")
                    logger.info(f"🔍 DEBUG: Observation: {observation[:200]}")

                    # Parse observation if it's a JSON string
                    observation_data = observation
                    try:
                        import json
                        observation_data = json.loads(observation) if isinstance(observation, str) else observation
                        logger.info(f"🔍 DEBUG: Parsed observation_data has 'data': {'data' in observation_data if isinstance(observation_data, dict) else False}")
                    except (json.JSONDecodeError, TypeError):
                        observation_data = observation
                        logger.info(f"🔍 DEBUG: Could not parse observation as JSON")

                    formatted_steps.append({
                        "type": "action",
                        "tool": action.tool,
                        "input": action.tool_input,
                        "log": action.log if hasattr(action, 'log') else ""
                    })
                    formatted_steps.append({
                        "type": "observation",
                        "result": observation,  # Keep as string for display
                        "data": observation_data.get("data") if isinstance(observation_data, dict) and "data" in observation_data else None
                    })

            logger.info(f"🔍 DEBUG: Total formatted_steps created: {len(formatted_steps)}")

            # Parse VIZ_HINT from raw output
            raw_output = result["output"]
            clean_output, visualization_hint = _parse_viz_hint(raw_output)

            # Generate schema-aware follow-up suggestions
            suggestions = []
            try:
                suggestions = generate_follow_up_suggestions(
                    user_query=user_input,
                    agent_response=clean_output,
                    role=self.role,
                    region=self.region,
                    llm=self.llm,
                )
            except Exception as sugg_err:
                logger.warning(f"Suggestion generation skipped: {sugg_err}")

            response = {
                "success": True,
                "query": user_input,
                "response": clean_output,
                "role": self.role,
                "region": self.region,
                "intermediate_steps": formatted_steps,
                "visualization_hint": visualization_hint,
                "suggestions": suggestions,
            }

            logger.info("Agent execution completed successfully")
            return response

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                "success": False,
                "query": user_input,
                "error": str(e),
                "role": self.role,
                "region": self.region,
            }

    async def stream_run(self, user_input: str, include_rag_context: bool = True):
        """
        Execute a user query with streaming output (for real-time display).

        Args:
            user_input: User's natural language query
            include_rag_context: Whether to include RAG context

        Yields:
            Chunks of the agent's thought process and final answer
        """
        logger.info(f"Streaming execution for: '{user_input[:100]}...'")

        queue = asyncio.Queue()
        loop = asyncio.get_running_loop()
        callback = StreamingCallback(queue, loop)

        # Get RAG context
        context = ""
        if include_rag_context:
            context = get_context_for_query(user_input)

        # We need to preserve agent execution context variables inside the thread/task
        from backend.app.core.auth import current_user_var
        from backend.app.agent.tools import dry_run_var
        user_val = current_user_var.get()
        dry_run_val = dry_run_var.get()

        async def run_agent():
            try:
                # Set context variables in this async task
                current_user_var.set(user_val)
                dry_run_var.set(dry_run_val)

                # Execute agent with callback (VIZ_HINT parsed inside StreamingCallback)
                result = await self.agent_executor.ainvoke(
                    {
                        "input": user_input,
                        "context": context,
                        "tools": self.tools_description,
                        "tool_names": self.tool_names_str,
                    },
                    config={"callbacks": [callback]}
                )

                # Generate follow-up suggestions after agent completes
                # Use run_in_executor to avoid blocking the event loop
                raw_output = result.get("output", "")
                clean_output, _ = _parse_viz_hint(raw_output)  # already streamed by callback

                try:
                    suggestions = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: generate_follow_up_suggestions(
                            user_query=user_input,
                            agent_response=clean_output,
                            role=self.role,
                            region=self.region,
                            llm=self.llm,
                        )
                    )
                    if suggestions:
                        await queue.put({"type": "suggestions", "suggestions": suggestions})
                except Exception as sugg_err:
                    logger.warning(f"Streaming suggestion generation failed: {sugg_err}")

            except Exception as e:
                logger.error(f"Error in streaming agent execution: {e}")
                await queue.put({"type": "error", "content": str(e)})
            finally:
                # Signal the generator that execution is done (AFTER suggestions)
                await queue.put(None)

        # Start execution in a background task
        agent_task = asyncio.create_task(run_agent())

        # Yield events as they arrive
        while True:
            event = await queue.get()
            if event is None:
                break
            yield event

        # Wait for task completion
        await agent_task

    def get_planning_steps(self, user_input: str) -> List[str]:
        """
        Extract the planning steps from agent's reasoning.

        Args:
            user_input: User's query

        Returns:
            List of planning steps
        """
        result = self.run(user_input)

        if not result.get("success"):
            return []

        # Extract intermediate steps
        steps = []
        for step in result.get("intermediate_steps", []):
            if len(step) >= 2:
                action, observation = step[0], step[1]
                steps.append(f"Action: {action.tool} | Input: {action.tool_input}")
                steps.append(f"Result: {observation[:200]}...")

        return steps


# ================================
# Helper Functions
# ================================
def create_agent(role: str = "viewer", region: Optional[str] = None, **kwargs) -> CognitiveAgent:
    """
    Factory function to create a cognitive agent.

    Args:
        role: Database role
        region: Region for manager role
        **kwargs: Additional arguments for CognitiveAgent

    Returns:
        CognitiveAgent instance
    """
    return CognitiveAgent(role=role, region=region, **kwargs)


def test_agent_query(query: str, role: str = "viewer", region: Optional[str] = None) -> Dict[str, Any]:
    """
    Quick test function for agent queries.

    Args:
        query: User query
        role: Database role
        region: Region for manager

    Returns:
        Agent response dictionary
    """
    agent = create_agent(role=role, region=region, verbose=True)
    return agent.run(query)


# ================================
# Export public API
# ================================
__all__ = [
    "CognitiveAgent",
    "create_agent",
    "test_agent_query",
]
