import uuid
import time

JOB = {
  "apiVersion": "batch/v1",
  "kind": "Job",
  "metadata": {
    "name": "pass-creator-job",
    "namespace": "default"
  },
  "spec": {
    "template": {
      "spec": {
        "containers": [
          {
            "name": "pass-creator",
            "image": "cerosyn/pass-creator:0.0.1",
            "env": [
              {
                "name": "LOGIN_URL",
                "valueFrom": {
                  "secretKeyRef": {
                    "name": "parking-pass-credentials-and-config",
                    "key": "LOGIN_URL"
                  }
                }
              },
              {
                "name": "PARKING_PASS_URL",
                "valueFrom": {
                  "secretKeyRef": {
                    "name": "parking-pass-credentials-and-config",
                    "key": "PARKING_PASS_URL"
                  }
                }
              },
              {
                "name": "EMAIL",
                "valueFrom": {
                  "secretKeyRef": {
                    "name": "parking-pass-credentials-and-config",
                    "key": "EMAIL"
                  }
                }
              },
              {
                "name": "PASSWORD",
                "valueFrom": {
                  "secretKeyRef": {
                    "name": "parking-pass-credentials-and-config",
                    "key": "PASSWORD"
                  }
                }
              },
              {
                "name": "VEHICLE_MAKE",
                "valueFrom": {
                  "secretKeyRef": {
                    "name": "parking-pass-credentials-and-config",
                    "key": "VEHICLE_MAKE"
                  }
                }
              },
              {
                "name": "VEHICLE_MODEL",
                "valueFrom": {
                  "secretKeyRef": {
                    "name": "parking-pass-credentials-and-config",
                    "key": "VEHICLE_MODEL"
                  }
                }
              },
              {
                "name": "VEHICLE_LICENSE_PLATE",
                "valueFrom": {
                  "secretKeyRef": {
                    "name": "parking-pass-credentials-and-config",
                    "key": "VEHICLE_LICENSE_PLATE"
                  }
                }
              },
              {
                "name": "CREATE_PASS",
                "value": "false"
              },
              {
                "name": "PRINT_SERVER_URL",
                "value": "http://akri-printer-ef4aec-svc.akri.svc.cluster.local:8000/print"
              }
            ]
          }
        ],
        "restartPolicy": "Never"
      }
    },
    "backoffLimit": 2
  }
}

def trigger_job():
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException
    # Load the kube config from within the cluster
    print(f"[DEBUG] Triggering Kubernetes job at {time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("[DEBUG] Loading incluster config")
    try:
        config.load_incluster_config()
        print("[DEBUG] Loaded incluster config successfully")
    except Exception as e:
        print(f"[ERROR] Failed to load incluster config: {e}")

    batch_v1 = client.BatchV1Api()


    job_random_suffix = str(uuid.uuid4())[:8]
    print(f"[DEBUG] Apply suffix: {job_random_suffix} to job name")



    # Create a unique job name
    job_name = f"pass-creator-job-{job_random_suffix}"
    JOB['metadata']['name'] = job_name

    try:
        api_response = batch_v1.create_namespaced_job(
            body=JOB,
            namespace="default"
        )
        print(f"Job created. Status='{api_response.status}'")
    except ApiException as e:
        print(f"Exception when creating job: {e}")

def handle_event(pin: int, state: str):
    print(f"[INFO] Event detected on pin {pin}, state: {state}")
    if state == "on":
        print("[INFO] Triggering Kubernetes job for parking pass creation.")
        trigger_job()