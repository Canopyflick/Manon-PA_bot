# features/agent/loop.py

import json
import logging
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from LLMs.config import llms
from features.agent.tools import create_agent_tools
from features.agent.prompts import AGENT_SYSTEM_PROMPT
from utils.helpers import BERLIN_TZ
from utils.session_avatar import PA

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 5


def _extract_text(response) -> str:
    """
    Extract plain text from an AIMessage response.
    Handles: str content, None, and list-of-content-blocks
    (e.g. [{"type": "text", "text": "..."}] from Anthropic-style models).
    """
    if response is None:
        return ""
    content = response.content
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        # List of content blocks — extract text parts
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "\n".join(parts)
    return str(content)


async def run_agent_loop(
    user_message: str,
    user_id: int,
    chat_id: int,
    first_name: str,
) -> str:
    """
    Run the agentic tool-calling loop for 'other' messages.
    Returns the final plain-text response string.
    """
    now = datetime.now(BERLIN_TZ)
    weekday = now.strftime("%A")

    # 1. Build tools with user context injected
    tools = create_agent_tools(user_id, chat_id)

    # 2. Bind tools to the LLM (OpenRouter smart, fallback to OpenAI)
    llm = llms.get("openrouter_smart", llms["smart"])
    llm_with_tools = llm.bind_tools(tools)

    # 3. Build initial messages
    system_text = AGENT_SYSTEM_PROMPT.format(
        weekday=weekday,
        now=now.strftime("%Y-%m-%d %H:%M:%S"),
        PA=PA,
        first_name=first_name,
    )
    messages = [
        SystemMessage(content=system_text),
        HumanMessage(content=user_message),
    ]

    # 4. Agent loop
    tool_map = {t.name: t for t in tools}
    tool_log = []
    response = None

    for iteration in range(MAX_ITERATIONS):
        response: AIMessage = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        logger.info(
            f"🤖 Agent iter {iteration+1}: "
            f"tool_calls={len(response.tool_calls) if response.tool_calls else 0}, "
            f"content_type={type(response.content).__name__}, "
            f"content_preview={str(response.content)[:200]!r}"
        )

        # No tool calls → we have the final answer
        if not response.tool_calls:
            break

        # Process each tool call
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_call_id = tc["id"]

            log_entry = {
                "iteration": iteration + 1,
                "timestamp": datetime.now(BERLIN_TZ).isoformat(),
                "tool": tool_name,
                "args": tool_args,
            }

            try:
                tool_fn = tool_map.get(tool_name)
                if tool_fn is None:
                    result_str = f"Unknown tool: {tool_name}"
                else:
                    result_str = await tool_fn.ainvoke(tool_args)
                log_entry["result"] = result_str[:500] if len(str(result_str)) > 500 else result_str
                log_entry["error"] = None
            except Exception as e:
                result_str = f"Tool error: {e}"
                log_entry["result"] = None
                log_entry["error"] = str(e)
                logger.error(f"Agent tool error: {tool_name}({tool_args}) -> {e}")

            tool_log.append(log_entry)
            messages.append(
                ToolMessage(content=str(result_str), tool_call_id=tool_call_id)
            )
    else:
        # Hit max iterations — force a final text-only response
        messages.append(
            HumanMessage(content=(
                "[System: Maximum tool iterations reached. "
                "Please give your final response now without using any more tools.]"
            ))
        )
        response = await llm.ainvoke(messages)  # plain LLM, no tools bound

    # 5. Log the full tool trace
    if tool_log:
        logger.info(
            f"🔧 Agent tool trace (user={user_id}, chat={chat_id}):\n"
            + json.dumps(tool_log, indent=2, default=str)
        )

    # 6. Extract final text (handles str, None, and list-of-content-blocks)
    final_text = _extract_text(response)
    if not final_text.strip():
        logger.warning(
            f"⚠️ Agent loop produced empty response. "
            f"raw content type={type(response.content).__name__ if response else 'NoResponse'}, "
            f"raw content={response.content!r if response else 'N/A'}"
        )
        final_text = f"I wasn't able to come up with a response {PA}"

    return final_text
