import os
import requests
import json
from k8s_tool_definition import K8S_TOOL_DEFINITION
from cerebras.cloud.sdk import Cerebras

from dotenv import load_dotenv 

load_dotenv()

client = Cerebras(api_key=os.getenv("CEREBRAS_API_KEY", "YOUR_API_KEY_HERE"))

# --- Configuration ---
# Replace with your actual Cerebras API endpoint and key
CEREBRAS_API_URL = "https://api.cerebras.com/v1/chat/completions" # Note: This is a hypothetical URL
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "YOUR_API_KEY_HERE")

# Configuration for your local FastAPI tool server
TOOL_SERVER_URL = "http://localhost:8000/execute_k8s"
TOOL_API_KEY = api_key=os.getenv("TOOL_API_KEY")

# --- System Prompt ---
# This prompt guides the LLM on its role and how to use tools.
SYSTEM_PROMPT = """
You are a helpful and highly intelligent DevOps assistant. Your role is to answer questions about a Kubernetes cluster.
When a user asks a question, you must use the provided 'execute_kubernetes_query' tool to get the necessary information.
Do not make up answers. If the tool provides an error or empty result, state that you couldn't find the information.
After the tool is called and you get the result, formulate a clear, human-readable answer for the user.
"""

def run_agent_query(user_prompt: str):
    """
    Manages the full conversation loop with the Cerebras LLM and the Kubernetes tool.
    """
    if not CEREBRAS_API_KEY or not TOOL_API_KEY:
        print("Error: Ensure CEREBRAS_API_KEY and TOOL_API_KEY environment variables are set.")
        return

    print(f"👤 User: {user_prompt}\n")

    # The conversation history starts with the system prompt and the user's first message.
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt}
    ]

    headers = {
        "Authorization": f"Bearer {CEREBRAS_API_KEY}",
        "Content-Type": "application/json"
    }

    # === First call to Cerebras API to see if a tool is needed ===
    payload = {
        "model": "Cerebras-GPT-13B", # Or the model you are using
        "messages": messages,
        "tools": [K8S_TOOL_DEFINITION],
        "tool_choice": "auto" # Let the model decide when to call the tool
    }

    try:
        
        chat_completion = client.chat.completions.create(
            model="gpt-oss-120b",
            messages=messages,
            tools=[K8S_TOOL_DEFINITION],
            tool_choice="auto"
        )
        
        llm_response=chat_completion.model_dump()
        response_message = llm_response['choices'][0]['message']
        messages.append(response_message) # Add LLM's response to history

    except requests.exceptions.RequestException as e:
        print(f"🔥 Error calling Cerebras API: {e}")
        return

    # === Check if the LLM wants to call our tool ===
    if response_message.get("tool_calls"):
        tool_call = response_message["tool_calls"][0]
        function_name = tool_call["function"]["name"]
        
        if function_name == "execute_kubernetes_query":
            print("🤖 LLM wants to call the Kubernetes tool...")
            
            # --- Execute the tool call ---
            tool_args = json.loads(tool_call["function"]["arguments"])
            print(f"   Calling function with args: {tool_args}")

            tool_headers = {
                "X-API-Key": TOOL_API_KEY,
                "Content-Type": "application/json",
                "accept": "application/json"
            }

            try:
                tool_response = requests.post(TOOL_SERVER_URL, headers=tool_headers, json=tool_args)
                tool_response.raise_for_status()
                tool_result = tool_response.json()
                print(f"✅ Tool executed successfully.\n")
            except requests.exceptions.RequestException as e:
                print(f"🔥 Error calling tool server: {e}")
                tool_result = {"error": str(e)}

            # --- Send the tool's result back to the LLM ---
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": function_name,
                "content": json.dumps(tool_result) # Content must be a string
            })

            # === Second call to Cerebras API to get the final answer ===
            print("🗣️ Sending tool result back to LLM for final response...")
            payload["messages"] = messages # Update payload with full history

            try:
                chat_completion = client.chat.completions.create(
                    model="gpt-oss-120b",
                    messages=messages,
                    tools=[K8S_TOOL_DEFINITION],
                    tool_choice="auto"
                )
                
                final_response=chat_completion.model_dump()
                final_message = final_response['choices'][0]['message']['content']
                print(f"\n💬 DevOps Assistant:\n{final_message}")

            except requests.exceptions.RequestException as e:
                print(f"🔥 Error on second call to Cerebras API: {e}")
                return
    else:
        # The LLM answered directly without using a tool
        final_message = response_message['content']
        print(f"\n💬 DevOps Assistant:\n{final_message}")


if __name__ == "__main__":
    # Example usage of the agent
    prompt = "Can you list the pods in the 'kube-system' namespace for me?"
    run_agent_query(prompt)

    print("\n" + "="*50 + "\n")

    prompt_with_name = "Describe the pod named 'my-app-pod-12345' in the 'production' namespace."
    # run_agent_query(prompt_with_name) # Uncomment to try another query
