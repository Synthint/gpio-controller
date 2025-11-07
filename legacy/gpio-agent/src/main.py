from datetime import *
import time
import lgpio
import signal
import os
import json
import uuid
import requests

class GPIO_controller:
  GPIO_PIN_NUMBERS = [4, 17, 27, 22, 5, 6, 13, 19, 26, 21, 16, 12, 25, 24, 23, 18]
  
  STATE_ON = 1
  STATE_OFF = 0

  MODE_INPUT = 1
  MODE_OUTPUT = 0

  MODE_STRING = {
    MODE_INPUT: "Input",
    MODE_OUTPUT: "Output"
  }

  STATE_STRING = {
    STATE_ON: "On",
    STATE_OFF: "Off"
  }

  GPIO_pin_states = {}
  GPIO_pin_modes = {}

  gpio_chip = None

  def __init__(self):
    self.GPIO_pin_states = {pin: self.STATE_OFF for pin in self.GPIO_PIN_NUMBERS}
    self.GPIO_pin_modes = {pin: self.MODE_INPUT for pin in self.GPIO_PIN_NUMBERS}
    self.gpio_chip = lgpio.gpiochip_open(0)
    for pin in self.GPIO_PIN_NUMBERS:
      try:
        print(f"[INFO] Claiming GPIO pin {pin} as input with pull-up")
        lgpio.gpio_claim_input(self.gpio_chip, pin, lgpio.SET_PULL_UP)
      except Exception as e:
        print(f"[ERROR] Failed to claim GPIO pin {pin}: {e}")
        
    signal.signal(signal.SIGINT, self.cleanup)
    signal.signal(signal.SIGTERM, self.cleanup)

  def validate_settings(self, pin, state = None, mode = None):
    if pin not in self.GPIO_PIN_NUMBERS:
      raise ValueError(f"Invalid GPIO pin number: {pin}")
    if state is not None and state not in [self.STATE_ON, self.STATE_OFF]:
      raise ValueError(f"Invalid state: {state}")
    if mode is not None and mode not in [self.MODE_INPUT, self.MODE_OUTPUT]:
      raise ValueError(f"Invalid mode: {mode}")
  
  def reset_pin(self, pin):
    if pin not in self.GPIO_PIN_NUMBERS:
      raise ValueError(f"Invalid GPIO pin number: {pin}")
    if self.GPIO_pin_modes[pin] == self.MODE_OUTPUT:
      lgpio.gpio_write(self.gpio_chip, pin, self.STATE_OFF)

  def cleanup(self, signal_received, frame):
    print("\n[INFO] Caught termination signal, cleaning up GPIO...")
    for pin in self.GPIO_PIN_NUMBERS:
      lgpio.gpio_write(self.gpio_chip, pin, self.STATE_OFF) 
    lgpio.gpiochip_close(self.gpio_chip)

  def set_pin_mode(self, pin, mode):
    self.validate_settings(pin, mode=mode)
    self.reset_pin(pin)

    self.GPIO_pin_modes[pin] = mode

    if mode == self.MODE_OUTPUT:
      lgpio.gpio_claim_output(self.gpio_chip, pin)
    else:
      lgpio.gpio_claim_input(self.gpio_chip, pin, lgpio.SET_PULL_UP)
  
  def get_pin_mode(self, pin):
    self.validate_settings(pin)
    return self.GPIO_pin_modes[pin]

  def set_pin_state(self, pin, state):
    self.validate_settings(pin, state=state)
    if self.GPIO_pin_modes[pin] != self.MODE_OUTPUT:
      raise ValueError(f"Cannot set state of pin {pin} to {state} because it is not in output mode.")
    
    self.GPIO_pin_states[pin] = state
    lgpio.gpio_write(self.gpio_chip, pin, state)
  
  def get_pin_state(self, pin):
    self.validate_settings(pin)
    if self.GPIO_pin_modes[pin] == self.MODE_OUTPUT:
      return self.GPIO_pin_states[pin]
    else:
      state_int = lgpio.gpio_read(self.gpio_chip, pin)
      if state_int == self.STATE_ON:
        return self.STATE_ON
      else:
        return self.STATE_OFF
  
  

  def pre_sync(func):
    def wrapper(self, *args, **kwargs):
      for pin in self.GPIO_PIN_NUMBERS:
        self.GPIO_pin_states[pin] = self.get_pin_state(pin)
      return func(self, *args, **kwargs)
    return wrapper
  
  @pre_sync
  def get_pin_string(self, pin):
    self.validate_settings(pin)
    return f"Pin {pin} is in {self.MODE_STRING[self.GPIO_pin_modes[pin]]} mode and is {self.STATE_STRING[self.GPIO_pin_states[pin]]}."


#
# Split this out better in the future
#
API_SERVER = "https://kubernetes.default.svc"
NAMESPACE = "default" # in the future pass in as an env var
TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"
CA_CERT_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt"

def load_token():
  with open(TOKEN_PATH, 'r') as f:
    return f.read().strip()

def trigger_job(job_definition: dict):
  token = load_token()
  
  job_random_suffix = str(uuid.uuid4())[:8]
  job_name = f"pass-creator-job-{job_random_suffix}"
  
  if 'metadata' not in job_definition:
    job_definition['metadata'] = {}
  job_definition['metadata']['name'] = job_name

  job_namespace = NAMESPACE
  if 'metadata' in job_definition and 'namespace' in job_definition['metadata']:
    job_namespace = job_definition['metadata']['namespace']
  
  url = f"{API_SERVER}/apis/batch/v1/namespaces/{job_namespace}/jobs"
  
  headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
  }
  
  print(f"[DEBUG] Posting job to {url} with name {job_name}")
  
  response = requests.post(
    url,
    headers=headers,
    data=json.dumps(job_definition),
    verify=CA_CERT_PATH
  )
  
  if response.status_code in (200, 201):
    print(f"[INFO] Job created successfully: {job_name}")
  else:
    print(f"[ERROR] Failed to create job: {response.status_code} {response.text}")
  



print("[INFO] Starting GPIO agent...")

JOB_DIR = "/app/jobs"
RATE_LIMIT_TIME = 30

gpio = None
try:
  gpio = GPIO_controller()
except Exception as e:
  print(f"[ERROR] Failed to initialize GPIO controller: {e}")
  time.sleep(30) # Give some time for debugging before exit. TODO: Remove in production
  
  exit(1)

recent_calls = {}

while True:
  time.sleep(0.1)
  current_time = datetime.now()
  for pin in gpio.GPIO_PIN_NUMBERS:
    try:
      state = gpio.get_pin_state(pin)
      if state == gpio.STATE_OFF: # TODO: Check for both states and look for file names like output_pin_<pin>_on_<extra text here>.json
        config_file_path = f"{JOB_DIR}/output_pin_{pin}.json"
        if os.path.exists(config_file_path):
          print(f"[INFO] Found configuration for pin {pin}, triggering job...")
          with open(config_file_path, 'r') as f:
            job_definition = json.load(f)
            print(f"[DEBUG] Job Definition: {job_definition}")

            if config_file_path in recent_calls:
              time_diff: timedelta = datetime.now() - recent_calls[config_file_path] 
              if time_diff.total_seconds() > RATE_LIMIT_TIME:
                recent_calls[config_file_path] = current_time
                trigger_job(job_definition)
              else:
                print(f"[INFO] Job at {config_file_path} cannot be triggered due to rate limit, please wait {RATE_LIMIT_TIME} seconds between jobs")
            else: 
              recent_calls[config_file_path] = current_time
              trigger_job(job_definition)
        # else:
        #   #print(f"[WARNING] No configuration found for pin {pin}, ignoring signal.")
    except Exception as e:
      print(f"[ERROR] Error processing pin {pin}: {e}")
