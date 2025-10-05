K8S_TOOL_DEFINITION = {
    "type": "function",
    "function": {
        "name": "execute_kubernetes_query",
        "description": "Execute a read-only query on a Kubernetes cluster to list or describe resources like pods, deployments, or services.",
        "parameters": {
            "type": "object",
            "properties": {
                "resource_type": {
                    "type": "string",
                    "description": "The type of K8s resource to query (e.g., 'pod', 'deployment', 'service')."
                },
                "namespace": {
                    "type": "string",
                    "description": "The Kubernetes namespace to query. Defaults to 'default' if not specified."
                },
                "name": {
                    "type": "string",
                    "description": "Optional: The specific name of the resource to describe."
                }
            },
            "required": ["resource_type"]
        }
    }
}