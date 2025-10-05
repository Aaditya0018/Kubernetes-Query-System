import os
from langchain_cerebras import ChatCerebras
from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain import hub
from langchain_core.tools import tool
from tools import kubconnect
from typing import Dict, Any, Union, Optional
from pydantic import BaseModel
from langchain_core.messages import AIMessage, HumanMessage

from dotenv import load_dotenv 

load_dotenv()

class KubernetesResourceInput(BaseModel):
    resource_type: str
    namespace: str = "default"
    name: Optional[str] = None # <--- This is the fix. It allows string or None.

@tool("get_kubernetes_resource", args_schema=KubernetesResourceInput)
def get_kubernetes_resource(
    resource_type: str, 
    namespace: str = "default", 
    name: Optional[str] = None
) -> Dict[str, Union[str, Dict[str, Any]]]:
    """
    REQUIRED TOOL: Use this function to query the state of Kubernetes resources.
    
    This tool connects directly to the Kubernetes API to retrieve detailed 
    information about a specific resource type (e.g., 'pod', 'service', 'deployment').
    
    The output is a structured Python dictionary (JSON) containing all fields 
    (status, metadata, spec) of the requested resource(s).
    
    Args:
        resource_type (str): The specific kind of resource. Use lowercase (e.g., 'pod', 'service', 'deployment').
        namespace (str, optional): The namespace to search in. Defaults to 'default'.
        name (str, optional): The name of a single resource (e.g., 'my-app-pod-1'). If omitted, lists ALL resources of the type in the namespace.
        
    Returns:
        dict: A dictionary with 'status' ('success' or 'error') and the 'data', which contains the raw resource(s) in JSON format.
    """
    
    return kubconnect.execute_k8s_query(resource_type,namespace,name)


class KubernetesSREAgent:
    """
    A stateful agent that maintains a conversation session to diagnose
    Kubernetes issues.
    """
    def __init__(self):
        """
        Initializes the agent, tools, and conversation memory one time.
        """
        print("--- Initializing SRE Agent ---")
        llm = ChatCerebras(
            model="gpt-oss-120b",
            temperature=0,
            api_key=os.getenv("CEREBRAS_API_KEY", "YOUR_API_KEY_HERE")
        )

        tools = [get_kubernetes_resource]

        # Your detailed system prompt remains the same
        
        sys_prompt="""
    You are an expert Kubernetes Site Reliability Engineer (SRE) and a master of diagnostics. Your primary mission is to help users resolve issues within their Kubernetes cluster by methodically investigating the situation using the tools at your disposal.

    # PRIMARY DIRECTIVE
    Your ability to function depends entirely on using the get_kubernetes_resource tool correctly. The most critical parameter is resource_type, and you are strictly limited to the values in the "Allowed resource_type Values" list below.

    # TOOLS

        * You have one tool: get_kubernetes_resource

        * Description: Fetches details for a specific Kubernetes resource or lists all resources of a given type within a namespace.

        * Arguments:

            - resource_type (string, required): The type of Kubernetes resource to query. YOU MUST USE A VALUE FROM THE "ALLOWED resource_type VALUES" LIST.

            - namespace (string, required): The Kubernetes namespace to search in.

            - name (string, optional): The specific name of the resource. If you omit this, the tool lists ALL resources of the specified type.

    # ALLOWED resource_type VALUES
        YOU MUST CHOOSE ONE OF THE FOLLOWING EXACT, CASE-SENSITIVE STRINGS. DO NOT USE PLURAL FORMS, GUESS, OR INVENT A RESOURCE TYPE. ANY DEVIATION WILL CAUSE A FAILURE.

        pod

        service

        deployment

        statefulset

        replicaset

        configmap

        secret

        persistentvolume

        persistentvolumeclaim

        ingress

        networkpolicy

        job

        cronjob

        namespace

        node

        serviceaccount

        resourcequota

        limitrange

        endpoint

        event

        horizontalpodautoscaler

        role

        rolebinding

        clusterrole

        clusterrolebinding

        storageclass

        volumeattachment

        csidriver

        csinode

        csistoragecapacity

        lease

        priorityclass

        runtimeclass

        customresourcedefinition

        apiservice

    # DIAGNOSTIC WORKFLOW & GUIDING PRINCIPLES

        1. Analyze the Request: Identify key entities in the user's report (e.g., application names, namespaces, error descriptions like "crashing" or "can't connect").

        2. Form a Hypothesis: Based on the report, form a primary hypothesis.

            - "app is crashing" -> Suspect pod, deployment, or replicaset.

            - "can't connect" -> Suspect service, ingress, or networkpolicy.

            - "configuration error" -> Suspect configmap or secret.

            - For any recent failure -> Always check for event resources first.

        3. Investigate Iteratively: Use the tool to test your hypothesis.

            - Start Broad: List all resources of a suspected type first (e.g., list all pod in the namespace).

            - Narrow Down: Analyze the output. If a specific resource looks suspicious (e.g., a pod in CrashLoopBackOff), query it directly by name.

            - Pivot: If your initial hypothesis is wrong (e.g., all pods are healthy), form a new one and investigate that (e.g., check the service).

        4. Synthesize and Conclude: Once you have gathered sufficient evidence to pinpoint the root cause, stop using tools and provide your final answer.

        5. Adhere to Limits: Your investigation is limited to a maximum of 10 tool calls. If you cannot determine a definitive root cause within this limit, you must stop. In your final answer, summarize your findings, state what you were able to rule out, and provide your best possible diagnosis based on the partial evidence.



    # RESPONSE FORMAT

    When you have finished, provide the answer in the following format:

    # Final Answer:

        - Diagnosis: A clear and concise summary of the problem's root cause.

        - Evidence: The specific findings from the tools that support your diagnosis.

        - Recommendation: Actionable steps the user should take to fix the issue.

    """

        # 1. THE PROMPT NOW INCLUDES A PLACEHOLDER FOR CHAT HISTORY
        prompt = ChatPromptTemplate.from_messages([
            ("system", sys_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        agent = create_tool_calling_agent(llm, tools, prompt)

        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=15,
            handle_parsing_errors=True
        )

        # 2. INITIALIZE AN EMPTY CHAT HISTORY FOR THE SESSION
        self.chat_history = []
        print("--- Agent is ready. A new session has started. ---")

    def chat(self, user_question: str) -> str:
        """
        Runs a single turn of the conversation.
        """
        print(f"\n> USER: {user_question}")

        # 3. PASS THE CURRENT CHAT HISTORY TO THE AGENT
        response = self.agent_executor.invoke({
            "input": user_question,
            "chat_history": self.chat_history
        })

        # 4. UPDATE THE CHAT HISTORY WITH THE LATEST INTERACTION
        self.chat_history.append(HumanMessage(content=user_question))
        self.chat_history.append(AIMessage(content=response["output"]))

        print(f"\n< AI: {response['output']}")
        return response["output"]

    def start_new_session(self):
        """
        Resets the chat history to start a new, clean conversation.
        """
        print("\n" + "="*50)
        print("--- Starting new session. Chat history has been cleared. ---")
        print("="*50 + "\n")
        self.chat_history = []


# --- HOW TO USE THE STATEFUL AGENT ---
if __name__ == "__main__":
    # Create the agent instance ONCE
    sre_agent = KubernetesSREAgent()

    # --- First Conversation Thread ---
    # Ask the first question
    sre_agent.chat("The web-app in the app-test namespace is not working. Can you check the pods?")

    # Ask a follow-up question. The agent will remember the context (namespace and app name).
    sre_agent.chat("Okay, that pod looks bad. What about the service associated with it?")
    
    # Ask another follow-up
    sre_agent.chat("Thanks. Now check the related deployment.")

    # --- Start a completely new conversation ---
    sre_agent.start_new_session()

    sre_agent.chat("I have a different problem now. Can you list all namespaces in the cluster?")








