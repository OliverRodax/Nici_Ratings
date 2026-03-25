#include <WiFi.h>
#include <WebServer.h>
#include <EEPROM.h>

// Wi-Fi credentials
const char *ssid = "Oliver Iphone";
const char *password = "123456788";

// Web server on port 80
WebServer server(80);

// Button pins
const int buttonPins[3] = {12, 13, 14}; // change as per your wiring

// EEPROM addresses
const int eepromAddr[3] = {0, 4, 8}; // store int (4 bytes) per button

// Button counts
int buttonCounts[3] = {0, 0, 0};

// Last button press time
unsigned long lastPressTime = 0;
const unsigned long debounceDelay = 5000; // 5 seconds

// HTML page template
String generateHTML()
{
  String html = "<!DOCTYPE html><html><head><title>ESP32 Button Counter</title></head><body>";
  html += "<h1>ESP32 Button Press Counts</h1><ul>";
  for (int i = 0; i < 3; i++)
  {
    String buttonName = "";
    switch (i)
    {
    case 0:
      buttonName = "Gefallen";
      break;
    case 1:
      buttonName = "Mittelmäßig";
      break;
    case 2:
      buttonName = "Nicht gefallen";
      break;
    }
    html += "<li>" + buttonName + ": " + String(buttonCounts[i]) + " presses</li>";
  }
  html += "</ul></body></html>";
  return html;
}

// Handle root page
void handleRoot()
{
  server.send(200, "text/html", generateHTML());
}
void resetCounts()
{
  for (int i = 0; i < 3; i++)
  {
    buttonCounts[i] = 0;
    EEPROM.put(eepromAddr[i], buttonCounts[i]);
  }
  EEPROM.commit();
  Serial.println("All button counts reset to 0");
  server.sendHeader("Location", "/"); // redirect to main page
  server.send(303);                   // 303 See Other
}
void setup()
{
  Serial.begin(115200);
  delay(1000);

  // Initialize EEPROM (12 bytes for 3 integers)
  EEPROM.begin(12);
  // resetCounts();
  // Load stored counts
  for (int i = 0; i < 3; i++)
  {
    EEPROM.get(eepromAddr[i], buttonCounts[i]);
  }

  // Initialize button pins
  for (int i = 0; i < 3; i++)
  {
    pinMode(buttonPins[i], INPUT_PULLUP); // assuming buttons connect to GND when pressed
  }

  // Connect to Wi-Fi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nConnected!");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // Define web routes
  server.on("/", handleRoot);
  server.begin();
  Serial.println("HTTP server started");
}

void loop()
{
  server.handleClient();

  // Read buttons with 5-second cooldown
  unsigned long now = millis();
  if (now - lastPressTime >= debounceDelay)
  {
    for (int i = 0; i < 3; i++)
    {
      if (digitalRead(buttonPins[i]) == LOW)
      { // button pressed
        buttonCounts[i]++;
        lastPressTime = now;

        // Save to EEPROM
        EEPROM.put(eepromAddr[i], buttonCounts[i]);
        EEPROM.commit();

        Serial.printf("Button %d pressed. Count: %d\n", i + 1, buttonCounts[i]);
        break; // only allow one button press per 5 seconds
      }
    }
  }
}