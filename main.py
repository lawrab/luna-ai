import ollama
import subprocess
import json
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

LLM_MODEL = "llama3"

# --- Tools ---
def send_desktop_notification(title: str, message: str):
    """Sends a desktop notification to the user."""
    try:
        subprocess.run(['notify-send', title, message], check=True)
        return f"Successfully sent notification with title '{title}'."
    except FileNotFoundError:
        return "Error: `notify-send` command not found. Is libnotify installed?"
    except Exception as e:
        return f"Error sending notification: {e}"

AVAILABLE_TOOLS = {
    "send_desktop_notification": send_desktop_notification
}

# --- Main Assistant Logic ---

def create_system_prompt():
    """Creates the system prompt with tool descriptions."""
    # CORRECTED: All curly braces in the example JSON are now escaped with double braces.
    return """You are a helpful and friendly AI assistant named L.U.N.A. You have access to the following tools.

To use a tool, you MUST respond with a JSON object ONLY, and no other text.
The JSON object must have a 'tool_name' and a 'tool_args' key.
The 'tool_args' object must contain the arguments for the function.

Here are the available tools:
- tool_name: 'send_desktop_notification'
  - description: Sends a desktop notification to the user. Use this to alert the user about something important or upon their request.
  - tool_args:
    - title (string, required): The title of the notification.
    - message (string, required): The main body/message of the notification.

Example of a tool call:
User: "remind me to take a break in 5 minutes"
Assistant:
{{
    "tool_name": "send_desktop_notification",
    "tool_args": {{
        "title": "Reminder",
        "message": "Time to take a break!"
    }}
}}

If you are not calling a tool, just respond as a friendly AI assistant.
"""

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

    # --- Configuration for which Ollama model to use ---
    LLM_MODEL = "llama3"
    print(f"Using model: {LLM_MODEL}")
    # ---------------------------------------------------

    llm = ChatOllama(model=LLM_MODEL)
    
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", create_system_prompt()),
        ("user", "{input}")
    ])
    
    chain = prompt_template | llm | StrOutputParser()

    print("\nL.U.N.A. is online. Let's try tools the robust way!")
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
                    
                    if tool_name in AVAILABLE_TOOLS:
                        print(f"L.U.N.A:  Okay, running the `{tool_name}` tool...")
                        tool_function = AVAILABLE_TOOLS[tool_name]
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