# luna/main.py
"""
The main entry point for the L.U.N.A. assistant application.

This module is responsible for orchestrating the application's components.
"""
import ollama
import json
from . import config, prompts, tools
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def is_ollama_running():
    """Check if the Ollama service is running."""
    try:
        ollama.list()
        return True
    except Exception:
        return False

def main():
    print("Initializing L.U.N.A. - Logical Unified Network Assistant...")

    if not is_ollama_running():
        print("\n[ERROR] Ollama service is not running.")
        return

    LLM_MODEL = config.LLM_MODEL
    print(f"Using model: {LLM_MODEL}")

    llm = ChatOllama(model=LLM_MODEL)

    # Use the prompt from our dedicated prompts module
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", prompts.create_system_prompt()),
        ("user", "{input}")
    ])

    chain = prompt_template | llm | StrOutputParser()

    print("\nL.U.N.A. is online.")
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() == 'exit':
                print("L.U.N.A: Goodbye!")
                break

            response_text = chain.invoke({"input": user_input})

            try:
                tool_call = json.loads(response_text)

                if isinstance(tool_call, dict) and "tool_name" in tool_call:
                    tool_name = tool_call.get("tool_name")
                    tool_args = tool_call.get("tool_args", {})

                    # Use the tools from our dedicated tools module
                    if tool_name in tools.AVAILABLE_TOOLS:
                        print(f"L.U.N.A:  Okay, running the `{tool_name}` tool...")
                        tool_function = tools.AVAILABLE_TOOLS[tool_name]
                        result = tool_function(**tool_args)
                        print(f"L.U.N.A: {result}")
                    else:
                        print(f"L.U.N.A: I tried to use a tool named '{tool_name}' but I don't have it.")
                else:
                    print(f"L.U.N.A: {response_text}")

            except json.JSONDecodeError:
                print(f"L.U.N.A: {response_text}")

        except KeyboardInterrupt:
            print("\nL.U.N.A: Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred: {e}")
            break

if __name__ == "__main__":
    main()