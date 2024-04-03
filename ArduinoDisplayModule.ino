#include <LiquidCrystal.h>
#include <ArduinoJson.h>

String deviceType = "LCD";
String version = "1.0";

const int rs = 12, en = 11, d4 = 5, d5 = 4, d6 = 3, d7 = 2;
LiquidCrystal lcd(rs, en, d4, d5, d6, d7);
const int lcdWidth = 16;
const int lcdHeight = 2;
unsigned long timestamp = 0;
const unsigned long heartbeatTimeout = 120000;
unsigned long lastDisconnectedTime = 0;
const unsigned long disconnectedRefreshInterval = 60000;

String messageArray[lcdHeight] = {
  "",
  ""
};

unsigned long lastReceivedTime = 0;
const unsigned long timeout = 1000 * 120;

String centerMessage(String message) {
  String paddedMessage = "";
  if (message.length() < lcdWidth) {
    int missingSpaces = (int) (lcdWidth - message.length())/2;

    for (int i = 0; i < missingSpaces; i++) {
        paddedMessage += ' ';
    }
  }
  return paddedMessage += message;
}

void printLCD() {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(messageArray[0]);
  lcd.setCursor(0, 1);
  lcd.print(messageArray[1]);
}

void disconnected() {
  messageArray[0] = centerMessage("WAITING FOR");
  messageArray[1] = centerMessage("CONNECTION...");
  printLCD();
}

bool sendStatus(String status) {
  StaticJsonDocument<256> jsonStatus;
  jsonStatus["S"] = status;
  return sendMessage(jsonStatus);
}

bool sendResponse (String response) {
  StaticJsonDocument<256> jsonResponse;
  jsonResponse["R"] = response;
  return sendMessage(jsonResponse);
}

bool sendMessage(StaticJsonDocument<256> json) {
  if (Serial.availableForWrite() > 0) {
    String jsonString;
    serializeJson(json, jsonString);
    jsonString += "\n";
    // Serial.print(jsonString);
    Serial.print(jsonString.c_str());
    // Serial.println(jsonString.length());
    // Serial.write(jsonString);
    return true;
  } else {
    return false;
  }
}


void setup() {
  lcd.begin(lcdWidth, lcdHeight);
  disconnected();
  Serial.begin(115200);
  while (!Serial) {
    ;
  }
}

void loop() {
  String message = "";
  String command = "";

  if (Serial.available() > 0) {
    lastReceivedTime = millis();
    message = Serial.readStringUntil('\n');
    StaticJsonDocument<256> jsonDoc;
    DeserializationError error = deserializeJson(jsonDoc, message);
    if (!error) {
      if (jsonDoc.containsKey("C")) {
        command = jsonDoc["C"].as<String>();
        if (command == "P") {
          if (jsonDoc.containsKey("L1") &&  jsonDoc.containsKey("L2")) {
            messageArray[0] = jsonDoc["L1"].as<String>();
            messageArray[1] = jsonDoc["L2"].as<String>();
            printLCD();
            if (sendStatus("done")) {
              command = "";
            }
          } else {
            if (sendStatus("ER3")) {
              command = "";
            }
          }
        } else if (command == "G") {
          if (jsonDoc.containsKey("E")) {
            String element = jsonDoc["E"].as<String>();
			if (element == "devicetype") {
              if (sendResponse(deviceType)) {
                command = "";
              }
            } else if (element == "version") {
              if (sendResponse(version)) {
                command = "";
              }
            } else {
              if (sendStatus("E5")) {
                command = "";
              }
            }
          } else {
            if (sendStatus("E4")) {
              command = "";
            }
          }
        } else if (command == "S") {
          if (jsonDoc.containsKey("E")) {
            if (jsonDoc.containsKey("V")) {
              String element = jsonDoc["E"].as<String>();
              String value = jsonDoc["V"].as<String>();
              if (element == "donothing") {
                String donothing;
                donothing = value;
                if (sendStatus("done")) {
                  command = "";
                }
              } else {
                if (sendStatus("E7")) {
                  command = "";
                }
              }
            } else {
              if (sendStatus("E6")) {
                command = "";
              }
            }
          } else {
            if (sendStatus("E4")) {
              command = "";
            }
          }
        } else {
          if (sendStatus("unknown")) {
            command = "";
          }
        }
      } else {
        if (sendStatus("ER2")) {
          command = "";
        }
      }
    } else {
        if (sendStatus("ER1")) {
          command = "";
        }
    }
  } else {
    //if (millis() - lastReceivedTime > timeout) {
	if (millis() - lastReceivedTime > heartbeatTimeout) {
      //disconnected();
      //lastReceivedTime = millis();
	  if (millis() - lastDisconnectedTime > disconnectedRefreshInterval) {
		disconnected();
		lastDisconnectedTime = millis();
	  }
    }
  }
}