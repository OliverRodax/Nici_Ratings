import RPi.GPIO as GPIO
import time
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# Button GPIO pins (BCM numbering)
BUTTON_PINS = [17, 27, 22]

# Button names
BUTTON_NAMES = ["Gefallen", "Mittelmäßig", "Nicht gefallen"]

# Persistent storage file
DATA_FILE = "button_counts.json"
PAST_DATA_DIR = "past_data"

# Debounce delay in seconds
DEBOUNCE_DELAY = 5.0

# Button counts
button_counts = [0, 0, 0]
last_press_time = 0.0


# --- Persistence ---

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

def archive_counts():
    """Save current counts to past_data/ before resetting."""
    os.makedirs(PAST_DATA_DIR, exist_ok=True)
    # Find next available filename (data1.json, data2.json, ...)
    index = 1
    while os.path.exists(os.path.join(PAST_DATA_DIR, f"data{index}.json")):
        index += 1
    archive_path = os.path.join(PAST_DATA_DIR, f"data{index}.json")
    try:
        with open(archive_path, "w") as f:
            json.dump({
                "counts": button_counts,
                "labels": BUTTON_NAMES,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, ensure_ascii=False, indent=2)
        print(f"Archived counts to {archive_path}")
    except Exception as e:
        print(f"Failed to archive counts: {e}")


# --- HTML generation ---

def generate_html():
    return f"""<!DOCTYPE html>
<html>
<head>
  <title>Raspberry Pi Button Counter</title>
  <meta charset="utf-8">
  <script>
    async function updateCounts() {{
      try {{
        const res = await fetch('/data');
        const data = await res.json();
        data.counts.forEach((count, i) => {{
          document.getElementById('count-' + i).textContent = count + ' presses';
        }});
      }} catch (e) {{}}
    }}
    setInterval(updateCounts, 2000);
  </script>
</head>
<body>
  <h1>Raspberry Pi Button Press Counts</h1>
  <ul>
    {"".join(f'<li>{BUTTON_NAMES[i]}: <span id="count-{i}">{button_counts[i]} presses</span></li>' for i in range(3))}
  </ul>
</body>
</html>"""


# --- Web server ---

class RequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        global button_counts

        if self.path == "/":
            html = generate_html()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))

        elif self.path == "/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"counts": button_counts}).encode("utf-8"))

        elif self.path == "/reset":
            archive_counts()
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
        GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def button_loop():
    global last_press_time
    print("Listening for button presses...")
    try:
        while True:
            now = time.time()
            if now - last_press_time >= DEBOUNCE_DELAY:
                for i, pin in enumerate(BUTTON_PINS):
                    if GPIO.input(pin) == GPIO.LOW:
                        button_counts[i] += 1
                        last_press_time = now
                        save_counts()
                        print(f"Button {i + 1} ({BUTTON_NAMES[i]}) pressed. Count: {button_counts[i]}")
                        break
            time.sleep(0.05)
    except KeyboardInterrupt:
        pass


# --- Main ---

if __name__ == "__main__":
    load_counts()
    setup_gpio()

    server_thread = Thread(target=start_server, daemon=True)
    server_thread.start()

    try:
        button_loop()
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up. Exiting.")