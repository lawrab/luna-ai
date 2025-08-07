# luna/main.py
"""
The main command-line entry point for running the L.U.N.A. assistant.
"""
import ollama
# NEW: Import our new speech module
from . import config, speech
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

    llm = ChatOllama(model=config.LLM_MODEL)
    agent = LunaAgent(llm)

    print("\nL.U.N.A. is online.")
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() == 'exit':
                speech.speak("Goodbye!")
                break

            # Get the response from the agent
            response = agent.process_input(user_input)

            # Print the response to the console so we can still see it
            print(f"L.U.N.A: {response}")
            speech.speak(response)

        except KeyboardInterrupt:
            speech.speak("Goodbye!")
            break
        except Exception as e:
            error_message = f"An unexpected error occurred: {e}"
            print(f"\n[ERROR] {error_message}")
            speech.speak("I'm sorry, an error occurred.")
            break

if __name__ == "__main__":
    main()