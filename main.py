import RPi.GPIO as GPIO
import time
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# Wi-Fi is handled by the OS on Raspberry Pi - no code needed

# Button GPIO pins (BCM numbering)
BUTTON_PINS = [17, 27, 22]  # Change as per your wiring

# Button names
BUTTON_NAMES = ["Gefallen", "Mittelmäßig", "Nicht gefallen"]

# Persistent storage file (replaces EEPROM)
DATA_FILE = "button_counts.json"

# Debounce delay in seconds
DEBOUNCE_DELAY = 5.0

# Button counts
button_counts = [0, 0, 0]
last_press_time = 0.0


# --- Persistence (replaces EEPROM) ---

def load_counts():
    global button_counts
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                button_counts = data.get("counts", [0, 0, 0])
                print(f"Loaded counts: {button_counts}")
        except Exception as e:
            print(f"Failed to load counts: {e}")
    else:
        save_counts()

def save_counts():
    try:
        with open(DATA_FILE, "w") as f:
            json.dump({"counts": button_counts}, f)
    except Exception as e:
        print(f"Failed to save counts: {e}")


# --- HTML generation ---

def generate_html():
    items = ""
    for i, name in enumerate(BUTTON_NAMES):
        items += f"<li>{name}: {button_counts[i]} presses</li>"
    return f"""<!DOCTYPE html>
<html>
<head><title>Raspberry Pi Button Counter</title></head>
<body>
  <h1>Raspberry Pi Button Press Counts</h1>
  <ul>{items}</ul>
  <br>
  <a href="/reset"><button>Reset All Counts</button></a>
</body>
</html>"""


# --- Web server ---

class RequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass  # Suppress default access logs

    def do_GET(self):
        if self.path == "/":
            html = generate_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/reset":
            global button_counts
            button_counts = [0, 0, 0]
            save_counts()
            print("All button counts reset to 0")
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()

def start_server():
    httpd = HTTPServer(("0.0.0.0", 80), RequestHandler)
    print("HTTP server started on port 80")
    httpd.serve_forever()


# --- GPIO button handling ---

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    for pin in BUTTON_PINS:
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Pull-up, press = LOW

def button_loop():
    global last_press_time
    print("Listening for button presses...")
    try:
        while True:
            now = time.time()
            if now - last_press_time >= DEBOUNCE_DELAY:
                for i, pin in enumerate(BUTTON_PINS):
                    if GPIO.input(pin) == GPIO.LOW:  # Button pressed
                        button_counts[i] += 1
                        last_press_time = now
                        save_counts()
                        print(f"Button {i + 1} ({BUTTON_NAMES[i]}) pressed. Count: {button_counts[i]}")
                        break  # Only one press per debounce window
            time.sleep(0.05)  # 50ms polling interval
    except KeyboardInterrupt:
        pass


# --- Main ---

if __name__ == "__main__":
    load_counts()
    setup_gpio()

    # Run web server in background thread
    server_thread = Thread(target=start_server, daemon=True)
    server_thread.start()

    try:
        button_loop()
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up. Exiting.")