# luna/agent.py
"""
Contains the core LunaAgent class that orchestrates the assistant's logic.
"""
import json
import threading
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

    def process_input(self, user_input: str):
        """
        Processes user input and publishes the result as an event.
        """
        response_text = self.chain.invoke({"input": user_input})

        try:
            tool_call = json.loads(response_text)
            if isinstance(tool_call, dict) and "tool_name" in tool_call:
                # Execute tool in a separate thread to avoid blocking the main loop
                tool_thread = threading.Thread(target=self._execute_tool, args=(tool_call,))
                tool_thread.start()
            else:
                events.publish("agent_response", response_text)

        except json.JSONDecodeError:
            events.publish("agent_response", response_text)

    def _execute_tool(self, tool_call: dict):
        """Executes a tool and publishes its result."""
        tool_name = tool_call.get("tool_name")
        tool_args = tool_call.get("tool_args", {})

        if tool_name in tools.AVAILABLE_TOOLS:
            events.publish("tool_started", tool_name)
            tool_function = tools.AVAILABLE_TOOLS[tool_name]
            result = tool_function(**tool_args)
            events.publish("tool_finished", result)
        else:
            events.publish("error", f"Attempted to use an unknown tool: {tool_name}")
