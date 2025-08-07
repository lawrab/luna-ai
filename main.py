import ollama
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# --- Configuration ---
LLM_MODEL = "llama3"

def is_ollama_running():
    """Check if the Ollama service is running."""
    try:
        ollama.list()
        return True
    except Exception:
        return False

def main():
    """
    The main entry point for the L.U.N.A. assistant.
    """
    print("Initializing L.U.N.A. - Logical Unified Network Assistant...")

    if not is_ollama_running():
        print("\n[ERROR] Ollama service is not running.")
        print("Please start the Ollama application or run 'ollama serve' in a new terminal.")
        return

    print(f"Using model: {LLM_MODEL}")

    llm = ChatOllama(model=LLM_MODEL)

    # This prompt template gives the AI its personality and instructions.
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful and friendly AI assistant named L.U.N.A. Keep your answers concise and clear."),
        ("user", "{input}")
    ])

    # The chain remains the same
    chain = prompt | llm

    print("\nL.U.N.A. is online. Type 'exit' to quit.")
    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() == 'exit':
                print("L.U.N.A: Goodbye!")
                break

            print("L.U.N.A: ", end="", flush=True)
            # The 'stream' method now returns message "chunks" with a 'content' attribute
            for chunk in chain.stream({"input": user_input}):
                # We access the actual text content of the chunk
                print(chunk.content, end="", flush=True)
            print() # Newline after the full response

        except KeyboardInterrupt:
            print("\nL.U.N.A: Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] An unexpected error occurred: {e}")
            break

if __name__ == "__main__":
    main()