
from kubernetes import client, config
from kubernetes.client.rest import ApiException

config.load_kube_config()
v1 = client.CoreV1Api()
pods = [
    "emergency-service-manager-application-745c85fddd-cqcpz",
    "api-gateway-69ffb6658-pdzh5",
    "admission-manager-7ff99748c7-gg92m",
    "gui-85fd68d5cc-td67j",
    "wait-estimator-application-8487dcf4b6-6kscx"]

# delete solo i pod che non sono database
value = v1.list_namespaced_pod("my-app")
for pod in value.items:
    if "mysql" not in pod.metadata.name:
        v1.delete_namespaced_pod(pod.metadata.name, "my-app") 