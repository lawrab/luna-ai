# luna/main.py
"""
The main command-line entry point for running the L.U.N.A. assistant.
"""
import ollama
from . import config
from .agent import LunaAgent
from langchain_ollama import ChatOllama

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

    print(f"Using model: {config.LLM_MODEL}")

    # 1. Initialize the LLM
    llm = ChatOllama(model=config.LLM_MODEL)

    # 2. Create an instance of our agent
    agent = LunaAgent(llm)

    print("\nL.U.N.A. is online.")
    # 3. Start the chat loop
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() == 'exit':
                print("L.U.N.A: Goodbye!")
                break

            # 4. Get the response from the agent
            response = agent.process_input(user_input)
            print(f"L.U.N.A: {response}")

        except KeyboardInterrupt:
            print("\nL.U.N.A: Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred: {e}")
            break

if __name__ == "__main__":
    main()