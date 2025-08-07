# luna/agent.py
"""
Contains the core LunaAgent class that orchestrates the assistant's logic.
"""
import json
from . import prompts, tools
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

class LunaAgent:
    def __init__(self, llm):
        """
        Initializes the agent with a language model.
        """
        # The agent's brain is its language model
        self.llm = llm

        # The agent's instruction set and personality
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", prompts.create_system_prompt()),
            ("user", "{input}")
        ])

        # The full processing chain
        self.chain = prompt_template | self.llm | StrOutputParser()

    def process_input(self, user_input: str) -> str:
        """
        Processes a single line of user input and returns the agent's response.
        """
        response_text = self.chain.invoke({"input": user_input})

        try:
            # Attempt to parse the response as a JSON tool call
            tool_call = json.loads(response_text)

            if isinstance(tool_call, dict) and "tool_name" in tool_call:
                return self._execute_tool(tool_call)
            else:
                # It was JSON, but not a valid tool call
                return response_text

        except json.JSONDecodeError:
            # Not a JSON response, so it's a regular chat message
            return response_text

    def _execute_tool(self, tool_call: dict) -> str:
        """Executes a tool call and returns the result."""
        tool_name = tool_call.get("tool_name")
        tool_args = tool_call.get("tool_args", {})

        if tool_name in tools.AVAILABLE_TOOLS:
            print(f"L.U.N.A:  Okay, running the `{tool_name}` tool...")
            tool_function = tools.AVAILABLE_TOOLS[tool_name]
            return tool_function(**tool_args)
        else:
            return f"I tried to use a tool named '{tool_name}' but I don't have it."