#include <Arduino.h>
#include <Wire.h>
#include <ArduinoWebsockets.h>
#include <ArduinoJson.h>
#include <WiFi.h>

//General Debugging
int DPS_counter = 0;
bool SerialPrintOn = true;
bool wifiOn = false;

// WiFi credentials
const char* ssid = "Hertog Lan";
const char* password = "66203810";

// WebSocket server details (Blender addon)
const char* websocket_server_host = "192.168.1.213"; // Change to your computer's IP
const int websocket_server_port = 8765;

// Gyro reading
float elapsedTime, currentTime, previousTime = 0;
float gyroAngle1[3], gyroAngle2[3];

//Moving average filter
const int MA_n = 8;
int16_t MA_gyroX1[MA_n], MA_gyroY1[MA_n], MA_gyroZ1[MA_n];
int16_t MA_gyroX2[MA_n], MA_gyroY2[MA_n], MA_gyroZ2[MA_n];
int MA_index = 0;

// Using namespace for websockets library
using namespace websockets;

// Create websocket client
WebsocketsClient client;
bool isConnected = false;
unsigned long lastConnectionAttempt = 0;
const unsigned long connectionRetryInterval = 5000; // 5 seconds between retries

void connectToServer();
void sendSensorData();
void readSensorData(int IMU, int16_t *MA_gyroX, int16_t *MA_gyroY, int16_t *MA_gyroZ, float *gyroAngle, bool lastIMU);

void setup() 
{
  Serial.begin(115200);     // Begin serial communication with 115200 baud/rate
  Wire.begin(21, 22);       // Start I2C communication through pin 21 and 22

  // Configure the Clock source of the MPU6050
  Wire.beginTransmission(0x68);       // Start communication with MPU6050 // MPU=0x68
  Wire.write(0x6B);                   // Talk to the register 6B
  Wire.write(0x03);                   // Set clock source to Z axis gyroscope reference
  Wire.endTransmission(true);         //end the transmission
  Wire.beginTransmission(0x69);       // Start communication with MPU6050 // MPU=0x69
  Wire.write(0x6B);                   
  Wire.write(0x03);                   
  Wire.endTransmission(true);         
  
  // Configure Gyro Sensitivity - Full Scale Range (default +/- 250deg/s)
  Wire.beginTransmission(0x68);
  Wire.write(0x1B);                  // Talk to the GYRO_CONFIG register (1B hex)
  Wire.write(0x00);                  //Set the register bits as 00000000 (250deg/s full scale)
  Wire.endTransmission(true);
  Wire.beginTransmission(0x69);
  Wire.write(0x1B);                  
  Wire.write(0x00);                  
  Wire.endTransmission(true);
  
  Serial.println("MPU6050 Gyroscope Test");

  pinMode(5, INPUT_PULLDOWN);
  pinMode(4, OUTPUT);

  // Connect to WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi: ");
  Serial.println(ssid);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
      delay(500);
      Serial.print(".");
      attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
      Serial.println();
      Serial.print("Connected to WiFi, IP address: ");
      Serial.println(WiFi.localIP());

      // Set up message handler
      client.onMessage([&](WebsocketsMessage message) {
        Serial.print("Got message from server: ");
        Serial.println(message.data());
      });
      
      client.onEvent([&](WebsocketsEvent event, String data) {
        if(event == WebsocketsEvent::ConnectionOpened) {
          Serial.println("Connection opened!");
          isConnected = true;
        } else if(event == WebsocketsEvent::ConnectionClosed) {
          Serial.println("Connection closed!");
          isConnected = false;
        } else if(event == WebsocketsEvent::GotPing) {
          Serial.println("Got a ping!");
        } else if(event == WebsocketsEvent::GotPong) {
          Serial.println("Got a pong!");
        }
      });

  } else {
      Serial.println();
      Serial.print("Failed to connect. Status code: ");
      Serial.println(WiFi.status());
      // WiFi status codes:
      // 0 : WL_IDLE_STATUS when WiFi is changing state
      // 1 : WL_NO_SSID_AVAIL if the SSID cannot be found
      // 3 : WL_CONNECTED if connected
      // 4 : WL_CONNECT_FAILED if password is incorrect
      // 6 : WL_DISCONNECTED if not connected to a network
  }
  
  connectToServer();    // Connect to WebSocket server
}

void loop() 
{
  // Button to reset the value of the gyro position
  if(digitalRead(5) == HIGH)
  {
    gyroAngle1[0] = 0;
    gyroAngle1[1] = 0;
    gyroAngle1[2] = 0;
    gyroAngle2[0] = 0;
    gyroAngle2[1] = 0;
    gyroAngle2[2] = 0;
    digitalWrite(4, HIGH);
  }

  // Read gyro data from first MPU6050
  readSensorData(0x68, MA_gyroX1, MA_gyroY1, MA_gyroZ1, gyroAngle1, false);
  
  // Read gyro data from second MPU6050
  readSensorData(0x69, MA_gyroX2, MA_gyroY2, MA_gyroZ2, gyroAngle2, true);

  if (wifiOn == false)
  {
    unsigned long currentTime = millis();
     if (currentTime - lastConnectionAttempt >= 1000) 
     {
        Serial.print("Data per seconde: ");
        Serial.println(DPS_counter);
        lastConnectionAttempt = currentTime;
        DPS_counter = 0;
     } 
  }
  digitalWrite(4, LOW);
}

void connectToServer() 
{
  Serial.println("Connecting to WebSocket server...");
  Serial.print("Server: ");
  Serial.print(websocket_server_host);
  Serial.print(":");
  Serial.println(websocket_server_port);

  // Check if we need to close existing connection
  if (client.available()) {
    client.close();
    delay(100);
  }
  
  // WebSocket connection with timeout
  bool connected = client.connect(websocket_server_host, websocket_server_port, "/");
  
  if (connected) {
    Serial.println("Connected to Blender WebSocket server!");
    isConnected = true;
    
    // Send initial message to test connection
    client.send("ESP32 Connected");
  } else {
    Serial.println("Failed to connect to WebSocket server");
    isConnected = false;
  }
}

void sendSensorData() 
// Function to send sensor data
{
  // Create a JSON document
  StaticJsonDocument<200> doc;
  doc["type"] = "IMU";
  doc["rot_x"] = gyroAngle1[0];
  doc["rot_y"] = gyroAngle1[1];
  doc["rot_z"] = gyroAngle1[2];
  doc["loc_x"] = 0;
  doc["loc_y"] = 0;
  doc["loc_z"] = 0;
  doc["timestamp"] = millis();
  
  // Serialize JSON to string
  String jsonOutput;
  serializeJson(doc, jsonOutput);
  
  // Send the message
  client.send(jsonOutput);
}

void readSensorData(int IMU, int16_t *MA_gyroX, int16_t *MA_gyroY, int16_t *MA_gyroZ, float *gyroAngle, bool lastIMU)
{
  // Read gyro data from MPU6050
  Wire.beginTransmission(IMU);
  Wire.write(0x43);                 // Starting with GYRO_XOUT_H register
  Wire.endTransmission(false);
  Wire.requestFrom(IMU, 6, 1);  // Request 6 bytes

  int16_t gyroX = Wire.read() << 8 | Wire.read();
  int16_t gyroY = Wire.read() << 8 | Wire.read();
  int16_t gyroZ = Wire.read() << 8 | Wire.read();

  if(MA_index < MA_n)
  {
    MA_gyroX[MA_index] = gyroX;
    MA_gyroY[MA_index] = gyroY;
    MA_gyroZ[MA_index] = gyroZ;
    if(lastIMU){MA_index++;}
  }
  else
  {
    int32_t sumX = 0;
    int32_t sumY = 0;
    int32_t sumZ = 0;
    for (int i = 0; i < MA_n; i++)
    {
      sumX += MA_gyroX[i];
      sumY += MA_gyroY[i];
      sumZ += MA_gyroZ[i];
    }
    
    int16_t offsetX = 0; 
    int16_t offsetY = 0; 
    int16_t offsetZ = 0;
    switch(IMU)
    {
      case 0x68: offsetX = 5; offsetY = 0; offsetZ = 0; break;
      case 0x69: offsetX = 0; offsetY = 1; offsetZ = 0; break;
    }
    
    int16_t gyroX_sum = sumX / MA_n;
    int16_t gyroY_sum = sumY / MA_n;
    int16_t gyroZ_sum = sumZ / MA_n;

    currentTime = millis();                             // Current time actual time read
    elapsedTime = (currentTime - previousTime) / 1000;  // Divide by 1000 to get seconds

    gyroAngle[0] = gyroAngle[0] + (gyroX_sum/131+offsetX) * elapsedTime;
    gyroAngle[1] = gyroAngle[1] + (gyroY_sum/131+offsetY) * elapsedTime;
    gyroAngle[2] = gyroAngle[2] + (gyroZ_sum/131+offsetZ) * elapsedTime;

    if(SerialPrintOn)
    {
      Serial.print("IMU ");
      Serial.print(IMU);
      Serial.print(" Gyro Angle: ");
      Serial.print(gyroAngle[0]); Serial.print(", ");
      Serial.print(gyroAngle[1]); Serial.print(", ");
      Serial.print(gyroAngle[2]); Serial.print("    ");
    }
    if(lastIMU)
    {
      if (isConnected and wifiOn)
      {
        client.poll();
        sendSensorData();
      }
      else if (wifiOn)
      {
        // Try to reconnect if enough time has passed since last attempt
        unsigned long currentTime = millis();
        if (currentTime - lastConnectionAttempt >= connectionRetryInterval) 
        {
            Serial.println("Not connected, attempting to reconnect...");
            connectToServer();
            lastConnectionAttempt = currentTime;
        } 
      }
      Serial.println();
      MA_index = 0;
      previousTime = currentTime;                         // Previous time is stored before the actual time read
      DPS_counter++;
    }
  }
}