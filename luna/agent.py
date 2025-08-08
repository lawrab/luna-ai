# luna/agent.py
"""
Contains the core LunaAgent class that orchestrates the assistant's logic.
"""
import json
import asyncio
from . import prompts, tools, events
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class LunaAgent:
    def __init__(self, llm):
        """
        Initializes the agent with a language model.
        """
        self.llm = llm
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", prompts.create_system_prompt()),
            ("user", "{input}")
        ])
        self.chain = prompt_template | self.llm | StrOutputParser()

    async def process_input(self, user_input: str):
        """
        Processes user input and publishes the result as an event asynchronously.
        """
        response_text = await self.chain.ainvoke({"input": user_input})

        try:
            tool_call = json.loads(response_text)
            if isinstance(tool_call, dict) and "tool_name" in tool_call:
                # Execute tool as an asyncio task to avoid blocking the main loop
                asyncio.create_task(self._execute_tool(tool_call))
            else:
                events.publish("agent_response", response_text)

        except json.JSONDecodeError:
            events.publish("agent_response", response_text)

    async def _execute_tool(self, tool_call: dict):
        """Executes a tool and publishes its result asynchronously."""
        tool_name = tool_call.get("tool_name")
        tool_args = tool_call.get("tool_args", {})

        if tool_name in tools.AVAILABLE_TOOLS:
            events.publish("tool_started", tool_name)
            tool_function = tools.AVAILABLE_TOOLS[tool_name]
            result = await tool_function(**tool_args) # Await the async tool function
            events.publish("tool_finished", result)
        else:
            events.publish("error", f"Attempted to use an unknown tool: {tool_name}")
