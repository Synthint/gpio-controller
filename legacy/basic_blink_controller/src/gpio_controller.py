import time
import lgpio
import signal
import sys

LED = 4

# Open GPIO chip and claim the pin
h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, LED)

# Function to clean up GPIO on exit
def cleanup(signal_received, frame):
    print("\n[INFO] Caught termination signal, cleaning up GPIO...")
    lgpio.gpio_write(h, LED, 0)  # Ensure the LED is turned off
    lgpio.gpiochip_close(h)  # Close GPIO chip
    sys.exit(0)  # Exit gracefully

# Register signal handlers for SIGINT (Ctrl+C) and SIGTERM (Pod deletion)
signal.signal(signal.SIGINT, cleanup)  # Handles Ctrl+C
signal.signal(signal.SIGTERM, cleanup)  # Handles Kubernetes pod deletion or `docker stop`

try:
    while True:
        lgpio.gpio_write(h, LED, 1)
        time.sleep(5)
        lgpio.gpio_write(h, LED, 0)
        time.sleep(10)
except Exception as e:
    print(f"[ERROR] {e}")
    cleanup(None, None)  # Ensure cleanup runs on unexpected errors
