import time
import lgpio
import signal
import time
import os
import importlib.util
import re
from collections import defaultdict
from typing import Callable, Dict, List
import json
import uuid
import time
from kubernetes import client, config
from kubernetes.client.rest import ApiException

class GPIO_controller:
  GPIO_PIN_NUMBERS = [4, 17, 27, 22, 5, 6, 13, 19, 26, 21, 20, 16, 12, 25, 24, 23, 18]
  
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
      lgpio.gpio_claim_input(self.gpio_chip, pin)
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
      lgpio.gpio_claim_input(self.gpio_chip, pin)
  
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
JOB_NS = "default"
def trigger_job(job_definition: Dict):
  
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
  if 'metadata' not in job_definition:
    job_definition['metadata'] = {}
  job_definition['metadata']['name'] = job_name

  #override job namespace
  job_definition['metadata']['namespace'] = JOB_NS


  try:
      api_response = batch_v1.create_namespaced_job(
          body=job_definition,
          namespace="default"
      )
      print(f"Job created. Status='{api_response.status}'")
  except ApiException as e:
      print(f"Exception when creating job: {e}")



print("[INFO] Starting GPIO agent...")

JOB_DIR = "/app/jobs"

gpio = GPIO_controller()

while True:
  for pin in gpio.GPIO_PIN_NUMBERS:
    try:
      state = gpio.get_pin_state(pin)
      if state == gpio.STATE_ON:
        config_file_path = f"{JOB_DIR}/output_pin_{pin}.json"
        if os.path.exists(config_file_path):
          print(f"[INFO] Found configuration for pin {pin}, triggering job...")
          with open(config_file_path, 'r') as f:
            job_definition = json.load(f)
            print(f"[DEBUG] Job Definition: {job_definition}")
            trigger_job(job_definition)
          # Reset the pin after handling
          gpio.set_pin_state(pin, gpio.STATE_OFF)
        else:
          print(f"[WARNING] No configuration found for pin {pin}, ignoring signal.")
    except Exception as e:
      print(f"[ERROR] Error processing pin {pin}: {e}")
