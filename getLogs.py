import pandas as pd
import os
import requests
import csv
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from icecream import ic


# Carica la configurazione Kubernetes
config.load_kube_config()

    # Crea il client Kubernetes
v1 = client.CoreV1Api()

def get_pod_logs(pod_name, namespace='my-app'):
    """Ottieni i log di un pod specificato."""
    try:
        logs = v1.read_namespaced_pod_log(pod_name, namespace=namespace)
        return logs
    except ApiException as e:
        print(f"Errore nel prelevare i log del pod {pod_name}: {e}")
        return None


def send_patient_data(data):
    """Invia una richiesta HTTP POST con i dati del paziente."""
    response = requests.get("http://localhost:31209/emergency-department/api-v1/admissions/patients", json=data)
    print("http response " + str(response))


def initialize_logs_df():
    """Crea e ritorna un DataFrame vuoto per i log."""
    return pd.DataFrame()


def collect_logs_from_pods(pods):
    """Raccoglie i log da una lista di pod."""
    logs_df = initialize_logs_df()
    for pod in pods:
        logs = get_pod_logs(pod)
        if logs:
            # Pulizia dei log e aggiunta al DataFrame
            cleaned_logs = f'"{logs.replace(",", " ")})"'
            logs_df[pod] = [cleaned_logs]
        else:
            logs_df[pod] = ["this pod is not available"]
    return logs_df


def update_unavailable_pods(logs_df, pods_list):
    """Aggiorna il DataFrame con lo stato dei pod non disponibili."""
    columns = logs_df.columns
    for pod in pods_list:
        if not any(pod in column for column in columns):
            logs_df[pod] = "pod unavailable"
    return logs_df

def update_unavailable_pods_statuses(pods_list, references):
    """Aggiorna il DataFrame con lo stato dei pod non disponibili."""
    for reference in references:
        if not any(reference in pod for pod in pods_list):
            pods_list[reference] = "Unavailable"
    return pods_list

def save_logs_to_csv(logs_df, file_index):
    """Salva il DataFrame dei log nel file CSV."""
    csv_filename = f'pod_logs_{file_index}.csv'
    try:
        # Se il file esiste, carica e concatena i dati
        existing_df = pd.read_csv(csv_filename)
        logs_df = pd.concat([existing_df, logs_df], axis=1)
    except FileNotFoundError:
        # Se il file non esiste, continua senza modificarlo
        pass
    
    if not logs_df.empty:
        # Salva i dati nel CSV
        logs_df.to_csv(csv_filename, index=False, quoting=csv.QUOTE_MINIMAL)
        print(f"Log salvati con successo nel file {csv_filename}")
    else:
        print("Nessun log disponibile per essere salvato.")


# Main
def main():
    # Impostazioni iniziali
    dir = os.listdir("datasets")
    files_count = len([f for f in dir if os.path.isfile(os.path.join("datasets", f))])
    
    # Dati del paziente
    patient_data = {
        "code": "WHITE",
        "description": "23423424234",
        "type": "C02",
        "patient": {
            "fc": "234",
            "name": "234",
            "surname": "234",
            "city": "234",
            "address": "234",
            "age": "234"
        }
    }
    
    # Invia i dati del paziente
    send_patient_data(patient_data)

    # Spiegazione dell'errore
    explanation = "The database of the service doesn't contain the right tables for the resources, so the service cannot retrieve them correctly causing the problem"

    
    # Ottieni la lista dei pod
    pods = v1.list_namespaced_pod("my-app")
    pods = [pod.metadata.name for pod in pods.items if "mysql" not in pod.metadata.name]

    # Colleziona i log dai pod
    logs_df = collect_logs_from_pods(pods)

    # Aggiungi la spiegazione e la domanda
    logs_df["ground_truth"] = explanation
    logs_df["question"] = "it seems like for some reason i cannot allocate resources from the web app, the list showed is empty"

    # Lista di pod da verificare
    pods_list = [
        "emergency-service-manager-application",
        "api-gateway",
        "admission-manager",
        "gui",
        "wait-estimator"
    ]
    
    # Aggiorna i pod non disponibili
    logs_df = update_unavailable_pods(logs_df, pods_list)


    # recupera status dei pod
    pods = v1.list_namespaced_pod("my-app")

    # Analizzare e stampare lo status di ogni pod
    pod_statuses={}
    for pod in pods.items:
        pod_statuses[pod.metadata.name] = pod.status.phase
    
    # aggiorna lo stato dei pod non disponibili 
    pod_statuses = str(update_unavailable_pods_statuses(pod_statuses, pods_list))
    ic(pod_statuses)
    # aggiugi lo stato dei pod ai dati creati:
    logs_df["pod_statuses"] = pod_statuses
    

    # Salva i log nel file CSV
    save_logs_to_csv(logs_df, files_count + 1)


# Avvia il main
if __name__ == "__main__":
    main()
