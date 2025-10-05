import json
from typing import Dict, Any, Union

# Import Kubernetes client components, though they are skipped in demo_mode
try:
    from kubernetes import client, config
    from kubernetes.client.exceptions import ApiException
except ImportError:
    # Allows the function to be defined even if kubernetes client isn't installed
    # as long as we only run in demo_mode
    print("Warning: 'kubernetes' library not found. Live execution will fail.")
    pass 

def get_api_map_from_csv(filepath: str = "tools/resources.csv"):
    """
    Reads the resource mapping from a CSV file and returns a dict:
    {resource: (api_client_instance, method_suffix)}
    """
    import csv
    v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()
    api_map = {}
    with open(filepath, mode='r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            api_version = row['api_version']
            if api_version == 'v1':
                api_client = v1
            elif api_version == 'apps_v1':
                api_client = apps_v1
            else:
                continue
            api_map[row['resource']] = (api_client, row['method_suffix'])
    return api_map




def execute_k8s_query(
    resource_type: str,
    namespace: str = "default",
    name: str = None,
    cluster_context: str = None, # Note: This parameter is unused in the current logic
    demo_mode: bool = False
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
        cluster_context (str, optional): The name of the cluster context defined in the kubeconfig file. Omit for the current default cluster.
        demo_mode (bool): If True, skips API call and returns mock data for testing.
        
    Returns:
        dict: A dictionary with 'status' ('success' or 'error') and the 'data', which contains the raw resource(s) in JSON format.
    """
    

    if demo_mode:
        # Implement demo logic here if needed, for now it will just pass through
        pass

    method_name = "" # Initialize for use in the final except block
    try:
        # 1. Load configuration (ideally, do this once outside the function)
        config.load_kube_config(config_file="tmp/uploads/config")

        resource_map = get_api_map_from_csv()
        resource_type_lower = resource_type.lower()

        if resource_type_lower not in resource_map:
            return {'status': 'error', 'data': f"Unsupported resource type: '{resource_type}'."}

        api_client, method_suffix = resource_map[resource_type_lower]

        # 2. Determine method name and arguments concisely 👈 REFINED LOGIC
        action = "read" if name else "list"
        method_name = f"{action}_namespaced_{method_suffix}"
        
        # Prepare arguments dynamically
        kwargs = {'namespace': namespace}
        if name:
            kwargs['name'] = name

        # 3. Get and execute the function
        func = getattr(api_client, method_name)
        result_obj = func(**kwargs)

        # 4. Serialize to dict and return
        return {'status': 'success', 'data': result_obj.to_dict()}

    except ApiException as e:
        # 👈 CORRECTION 1: Handle Kubernetes API errors
        error_body = json.loads(e.body)
        return {'status': 'error', 'data': f"Kubernetes API Error: {error_body.get('message')}"}

    except AttributeError:
        # 👈 CORRECTION 2: Handle incorrect method names
        return {'status': 'error', 'data': f"Internal Tool Error: Could not find method '{method_name}'. Check the API map."}
        
    except Exception as e:
        # 👈 CORRECTION 3: Handle all other unexpected errors
        return {'status': 'error', 'data': f"An unexpected error occurred: {str(e)}"}




# ----------------------------------------------------------------------
# PRIVATE HELPER FUNCTION FOR DEMO RESPONSES
# ----------------------------------------------------------------------

def _handle_demo_response(resource_type: str, namespace: str, name: str) -> Dict[str, Union[str, Dict[str, Any]]]:
    """Provides mock Kubernetes API responses for demo mode."""
    resource_type_lower = resource_type.lower()
    
    if name and name == "non-existent-resource":
        # Simulate a 404 Not Found error
        return {
            'status': 'error', 
            'data': "Kubernetes API Error: Status 404. Reason: Resource 'non-existent-resource' of type 'pod' not found in namespace 'default'."
        }

    # --- DEMO FOR A SINGLE POD (read_namespaced_pod) ---
    if resource_type_lower == 'pod' and name:
        return {
            'status': 'success',
            'data': {
                'apiVersion': 'v1',
                'kind': 'Pod',
                'metadata': {'name': name, 'namespace': namespace, 'labels': {'app': 'demo-app'}},
                'spec': {'containers': [{'name': 'main', 'image': 'nginx:1.21.6', 'ports': [{'containerPort': 80}]}]},
                'status': {'phase': 'Running', 'hostIP': '192.168.1.10', 'containerStatuses': [{'ready': True, 'restartCount': 0}]}
            }
        }
    
    # --- DEMO FOR LIST OF PODS (list_namespaced_pod) ---
    elif resource_type_lower == 'pod':
        return {
            'status': 'success',
            'data': {
                'apiVersion': 'v1',
                'kind': 'PodList',
                'items': [
                    {'metadata': {'name': 'app-1-xyz', 'labels': {'app': 'demo-app'}}, 'status': {'phase': 'Running'}},
                    {'metadata': {'name': 'app-2-abc', 'labels': {'app': 'demo-app'}}, 'status': {'phase': 'Running'}},
                    {'metadata': {'name': 'db-a-123', 'labels': {'app': 'database'}}, 'status': {'phase': 'Running'}}
                ]
            }
        }

    # --- DEMO FOR A SINGLE SERVICE (read_namespaced_service) ---
    elif resource_type_lower == 'service' and name:
        return {
            'status': 'success',
            'data': {
                'apiVersion': 'v1',
                'kind': 'Service',
                'metadata': {'name': name, 'namespace': namespace},
                'spec': {'type': 'LoadBalancer', 'ports': [{'port': 80, 'targetPort': 8080}]},
                'status': {'loadBalancer': {'ingress': [{'ip': '34.100.200.50'}]}}
            }
        }

    # --- DEMO FOR LIST OF DEPLOYMENTS (list_namespaced_deployment) ---
    elif resource_type_lower == 'deployment':
        return {
            'status': 'success',
            'data': {
                'apiVersion': 'apps/v1',
                'kind': 'DeploymentList',
                'items': [
                    {'metadata': {'name': 'frontend'}, 'status': {'replicas': 3, 'readyReplicas': 3, 'unavailableReplicas': 0}},
                    {'metadata': {'name': 'backend'}, 'status': {'replicas': 2, 'readyReplicas': 1, 'unavailableReplicas': 1}}
                ]
            }
        }
        
    # --- DEFAULT ERROR FOR UNSUPPORTED DEMO RESOURCE ---
    else:
        return {
            'status': 'error', 
            'data': f"Demo mode does not have mock data for '{resource_type}' or the combination requested."
        }

# --- Example Usage for Testing Demo Mode ---
if __name__ == "__main__":
    
    print("==================================================")
    print("             LLM TOOL DEMO MODE TESTS")
    print("==================================================")

    # 1. Test: Single Pod Lookup (Success Case)
    print("\n--- TEST 1: Get Single Pod Details ---")
    pod_result = execute_k8s_query(resource_type='Pod', name='auth-service-pod-1', demo_mode=True)
    print(f"Status: {pod_result['status']}")
    print(f"Pod Phase: {pod_result['data'].get('status', {}).get('phase', 'N/A')}")
    print(f"Image Used: {pod_result['data'].get('spec', {}).get('containers', [{}])[0].get('image', 'N/A')}")
    
    # 2. Test: List Pods (List Case)
    print("\n--- TEST 2: List All Pods in Namespace ---")
    list_result = execute_k8s_query(resource_type='pod', demo_mode=True)
    print(f"Status: {list_result['status']}")
    print(f"Total Pods in Demo: {len(list_result['data'].get('items', []))}")

    # 3. Test: Resource Not Found (Error Case)
    print("\n--- TEST 3: Non-Existent Resource (Simulated 404 Error) ---")
    error_result = execute_k8s_query(resource_type='Pod', name='non-existent-resource', demo_mode=True)
    print(f"Status: {error_result['status']}")
    print(f"Error Message: {error_result['data']}")
    
    # 4. Test: List Deployments (Example of AppsV1 API)
    print("\n--- TEST 4: Get Deployment Status ---")
    deployment_result = execute_k8s_query(resource_type='deployment', demo_mode=True)
    print(f"Status: {deployment_result['status']}")
    first_deploy_status = deployment_result['data']['items'][0]['status']
    print(f"Frontend Deployment Replicas: {first_deploy_status['readyReplicas']} / {first_deploy_status['replicas']}")
    
    
    
    # pod_result=execute_k8s_query(resource_type='Pod',namespace='kube-system')
    # print(pod_result)
