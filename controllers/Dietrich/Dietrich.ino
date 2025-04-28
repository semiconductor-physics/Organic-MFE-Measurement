#include <ADS1256.h>
#include <SPI.h>

#define SPISPEED 5000000
#define BAUD_RATE 250000
#define DEBUG_PRINT(X) if(debug) {Serial.println(X);}

enum state {IDN, IN, RST, SET, CONTINUOUS_IN, IDLE};
state currentState = IDLE;

const int DRDY_PIN = 27;
const float CLOCK_SPEED = 7.68;
const float ADC_V_REF = 2.5;
const bool USE_RESET_PIN = true;
const int SCK_PIN = 5;
const int MISO_PIN = 19;
const int MOSI_PIN = 18;
const int ADC_CS_PIN = 32;
const int DAC_CS_PIN = 21;

bool adsBufferEnabled = false;
char dRate, gain;
bool debug = true;

SPIClass spi(HSPI);
ADS1256 adc(DRDY_PIN, CLOCK_SPEED, ADC_V_REF, USE_RESET_PIN, spi, SCK_PIN, MISO_PIN, MOSI_PIN, ADC_CS_PIN);

long cycles = 0;
unsigned long start_time, run_time;
float debug_first, debug_last;
float inVals[3]; // 01, 23, 45

bool sendingData = false;
String cmd;
String args;


void setDAC(int channelNR, long dacValue) {
  int DACctrl = 0b00010000;
  if(channelNR==1) DACctrl = 0b00100100;

  if(dacValue < 0 || dacValue > 65535) dacValue = 0; // range check

  if(channelNR == 0 || channelNR == 1)
  {
    SPI.beginTransaction(SPISettings(SPISPEED, MSBFIRST, SPI_MODE1));
    digitalWrite(DAC_CS_PIN, LOW);
    SPI.transfer(DACctrl);
    SPI.transfer(dacValue >> 8);
    SPI.transfer(dacValue & 0xFF);
    digitalWrite(DAC_CS_PIN, HIGH);
    SPI.endTransaction();      
  }
}

void resetDAC() {
  setDAC(0, 0);
  setDAC(1, 0);
}

void setAdcParameters(char dRate, char gain) {
  adc.begin(dRate, gain, false);
  delay(200);   
}

void resetDAC_ADC() {
  dRate = ADS1256_DRATE_7500SPS;
  gain = ADS1256_GAIN_1;
  adc.begin(dRate, gain, adsBufferEnabled);
  delay(200);
  adc.setChannel(0,1);
  resetDAC();
}

void getAdcVals() {
  adc.waitDRDY();
  adc.setChannel(2,3);
  inVals[0] = adc.readCurrentChannel();

  adc.waitDRDY();
  adc.setChannel(4,5);
  inVals[1] = adc.readCurrentChannel();

  adc.waitDRDY();
  adc.setChannel(0,1);
  inVals[2] = adc.readCurrentChannel();
}

void handleIDN() {
  Serial.println("Here is Heinrich with 24 Bit ADC and 16 Bit DAC");
}

void resetVals() {
  inVals[0] = 0;
  inVals[1] = 0;
  inVals[2] = 0;
}

void handleReset() {
  resetDAC_ADC();
  resetVals();
  DEBUG_PRINT("Reset ADC");
}

void handleIn() {
  getAdcVals();
  if (debug) {
    Serial.print(inVals[0],6);
    Serial.print(inVals[1], 6);
    Serial.println(inVals[2], 6);
  } else {
    Serial.write((byte *)inVals, 3 * sizeof(float));
  }

}

void handleSet() {
  int delimIdx = args.indexOf(' ');
  if (delimIdx) {
    String setting = args.substring(0, delimIdx);
    args = args.substring(delimIdx);
    if (setting == "DRATE") {
      dRate = args.toInt();
      setAdcParameters(dRate, gain);
      DEBUG_PRINT("Set drate to " + String(dRate));
    }
    else if (setting == "GAIN") {
      gain = args.toInt();
      setAdcParameters(dRate, gain);
      DEBUG_PRINT("Set gain to " + String(gain));
    }
    else if (setting == "DEBUG") {
      debug = (bool)args.toInt();
    } else {
      DEBUG_PRINT("Invalid setting: "+ setting);
    }

  } else {
    DEBUG_PRINT("No arguments given");
  }
  args = "";
}

void handleContinuousIn() {
  getAdcVals();
  if(debug) {
    Serial.print(inVals[0],6);
    Serial.print(",");
    Serial.print(inVals[1], 6);
    Serial.print(",");
    Serial.println(inVals[2], 6);
    delay(10);
  } else {
    Serial.write((byte *)inVals, 3 * sizeof(float)); //3 floats which 4 bytes each
  }
  if (cycles==0) {
    debug_first = inVals[0];
  }
  cycles++;
}

void recieveCmd() {
  if (!Serial.available()) {
    return;
  }
  String serialInput = Serial.readStringUntil('\n');
  serialInput.toUpperCase();
  serialInput.trim();
  int delimIdx = serialInput.indexOf(' ');
  if (delimIdx) {
    cmd = serialInput.substring(0, delimIdx);
    args = serialInput.substring(delimIdx+1);
  } else {
    cmd = serialInput;
    args = "";
  }
  if(cmd == "IDN") {
    currentState = IDN;
  } else if(cmd == "RST") {
    currentState = RST;
  } else if(cmd == "IN") {
    currentState = IN;
  } else if(cmd == "SET") {
    currentState = SET;
  } else if(cmd == "START") {
    cycles = 0;
    start_time = millis();
    currentState = CONTINUOUS_IN;
  } else if(cmd == "STOP") {
    currentState = IDLE;
    debug_last = inVals[2];
    run_time = millis() - start_time;
  } else if(cmd =="NUM") {
    Serial.print(cycles);
    Serial.print(", firstfloat: ");
    Serial.print(debug_first, 8);
    Serial.print(", last_float: ");
    Serial.print(debug_last, 8);
    Serial.print(", run time: ");
    Serial.println(run_time);

    currentState = IDLE;
  } else {
    currentState = IDLE;
  }
  
}

void setup() {
  pinMode(DAC_CS_PIN, OUTPUT);
  digitalWrite(DAC_CS_PIN, HIGH);
  Serial.begin(BAUD_RATE);
  delay(10);
  resetDAC_ADC();
}

void loop() {
  switch (currentState) {
    case IDN:
      handleIDN();
      currentState = IDLE;
      break;
    case RST:
      handleReset();
      currentState = IDLE;
      break;
    case IN:
      handleIn();
      currentState = IDLE;
      break;
    case SET:
      handleSet();
      currentState = IDLE;
      break;
    case CONTINUOUS_IN:
      handleContinuousIn();
      recieveCmd();
      break;
    case IDLE:
      recieveCmd();
      break;
    default:
      currentState = IDLE;
      break;
  }

}
