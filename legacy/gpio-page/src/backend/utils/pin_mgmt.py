import time
import lgpio
import signal
import sys
import inspect


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
  
  

  