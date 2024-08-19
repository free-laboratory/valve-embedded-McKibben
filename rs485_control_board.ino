#include <string.h>
#include <stdlib.h>
#include <stdio.h>

#define DEVICE_ADDR 0
#define DEBUG_MODE 1

#define LF 0x0A

#define p_sense A1
#define v_in 7
#define v_out 8
#define re_de 1


#define RS485_Serial Serial1
#define USB_Serial Serial

#if DEBUG_MODE
  #define CMD_Serial USB_Serial
#else 
  #define CMD_Serial RS485_Serial
#endif

#define DEBUG_Serial USB_Serial

// ===== USB MODE VARIABLES ===== //
char cmd_from_pc[40];
int cmd_idx = 0;

double psi_inside = 0;
unsigned long prev_timestamp = 0;
unsigned long start_timestamp = 0;

double target_psi = 0;
int controller_sel = 0;

double cap_psi = 9999;

bool enable_sin_gen = false;
bool enable_square_gen = false;
bool enable_serial_print = false;
bool enable_debug_msg = false;

double sin_mag = 0.0;
double sin_period = 0.0;
double sin_offset = 0.0;

int act_state = 0;  // 0: hold 1:in 2:out

unsigned long CC0_val = 50000;

void setup() {
  analogReadResolution(12);

  pinMode(p_sense, INPUT);
  pinMode(re_de, OUTPUT);
  pinMode(v_in, OUTPUT);
  pinMode(v_out, OUTPUT);

  CMD_Serial.begin(115200);
  if (DEBUG_MODE) {
    DEBUG_Serial.begin(9600);
  }
  

  digitalWrite(re_de, LOW);

  prev_timestamp = millis();
  start_timestamp = millis();

  //************TCC1 Timer-Setup for AT-SAMD21-G18 ARM Cortex M0************
  //Divide the 48MHz system clock by 1 = 48MHz. Set division on Generic Clock Generator (GCLK) 4
  GCLK->GENDIV.reg = GCLK_GENDIV_DIV(1) | GCLK_GENDIV_ID(4);
  while (GCLK->STATUS.bit.SYNCBUSY) {};
  //Set the duty cycle to 50/50 HIGH/LOW. Enable GCLK 4. Set the clock source to 48MHz. Set clock source on GCLK 4
  GCLK->GENCTRL.reg = (0x0ul << GCLK_GENCTRL_IDC_Pos) | GCLK_GENCTRL_GENEN | GCLK_GENCTRL_SRC_DFLL48M | GCLK_GENCTRL_ID(4);
  while (GCLK->STATUS.bit.SYNCBUSY) {};
  //Enable the generic clock on GCLK4. Feed the GCLK4 to TCC0 and TCC1
  GCLK->CLKCTRL.reg = GCLK_CLKCTRL_CLKEN | GCLK_CLKCTRL_GEN_GCLK4 | GCLK_CLKCTRL_ID_TCC0_TCC1;
  while (GCLK->STATUS.bit.SYNCBUSY) {};
  //Set prescaler to 1, 48Mhz. Reload timer on next prescaler clock, use if prescaler DIV is more than 1
  TCC1->CTRLA.reg = TC_CTRLA_PRESCSYNC_PRESC | TCC_CTRLA_PRESCALER_DIV1;
  //Set the Nested Vector Interrupt Controller (NVIC) priority for TCC1 to 0 (highest)
  NVIC_SetPriority(TCC1_IRQn, 0);
  //Connect TCC1 to Nested Vector Interrupt Controller (NVIC)
  NVIC_EnableIRQ(TCC1_IRQn);
  //Enable TCC1 MC0-interrupt
  TCC1->INTENSET.reg = TCC_INTENSET_OVF | TCC_INTENSET_MC0;
  //Setup normal frequency operation on TCC1
  TCC1->WAVE.reg |= TCC_WAVE_WAVEGEN_NFRQ;
  while (TCC1->SYNCBUSY.bit.WAVE) {};
  //Set the frequency of the timer
  TCC1->PER.reg = 0x8FFFF;
  //TCC1->PER.reg = 0x1F000;
  while (TCC1->SYNCBUSY.bit.PER) {};

  //turn off the pwm
  TCC1->CC[0].reg = 0x0;
  while (TCC1->SYNCBUSY.bit.CC0) {};
  //Enable timer TCC1
  TCC1->CTRLA.bit.ENABLE = 1;
  while (TCC1->SYNCBUSY.bit.ENABLE) {};


  //turn on the pwm
  TCC1->CC[0].reg = CC0_val;
  while (TCC1->SYNCBUSY.bit.CC0) {};
}

void TCC1_Handler() {
  if (TCC1->INTFLAG.bit.OVF)  //Test if an OVF-Interrupt has occured
  {
    TCC1->INTFLAG.bit.OVF = 1;  //Clear the Interrupt-Flag
    if (act_state == 1) {
      digitalWrite(v_in, LOW);
    } else if (act_state == 2) {
      digitalWrite(v_out, LOW);
    }
  }

  if (TCC1->INTFLAG.bit.MC0)  // Test if an MC0 interrupt has occured
  {
    TCC1->INTFLAG.bit.MC0 = 1;  // Clear the interrupt flag

    // Add your interrupt code here ...
    if (act_state == 1) {
      digitalWrite(v_in, HIGH);
    } else if (act_state == 2) {
      digitalWrite(v_out, HIGH);
    }
  }
}

double psi_from_aread(int aread) {
  // ACT 1
  int aread_0 = 0;
  int aread_40 = 0;
  switch (DEVICE_ADDR) {
    case 51:
      aread_0 = 255;
      aread_40 = 1608;
      break;
    case 52:
      aread_0 = 535;
      aread_40 = 1905;
      break;
    case 53:
      aread_0 = 324;
      aread_40 = 1693;
      break;
    case 54:
      aread_0 = 800;
      aread_40 = 2160;
      break;
    case 55:
      aread_0 = 621;
      aread_40 = 2000;
      break;
    case 56:
      aread_0 = 592;
      aread_40 = 1955;
      break;
    case 57:
      aread_0 = 130;
      aread_40 = 1420;
      break;
    case 58:
      aread_0 = 574;
      aread_40 = 1829;
      break;
    case 0:
      return aread;
  }

  return ((double)(aread) - (double)(aread_0)) * 40.0 / ((double)aread_40 - (double)aread_0);
}

void bangbang(double bb_target_psi);
void pid(double pid_target_psi);
double sine_generator(double mag, int period_ms, double offset, unsigned long start_millis);
double square_generator(double mag, int period_ms, double offset, unsigned long start_millis);
void switch_state(bool false_is_outlet);

void loop() {

  psi_inside = psi_from_aread(analogRead(p_sense));

  switch (controller_sel) {
    case 0:
      // everything off
      digitalWrite(v_in, LOW);
      digitalWrite(v_out, LOW);
      break;
    case 1:
      bangbang(target_psi);
      break;
    case 2:
      // manual overide
      break;
  }

  if (enable_sin_gen) {
    target_psi = sine_generator(sin_mag, sin_period, sin_offset, start_timestamp);
  } else if (enable_square_gen) {
    target_psi = square_generator(sin_mag, sin_period, sin_offset, start_timestamp);
  }

  if (enable_serial_print && millis() - prev_timestamp > 10) {
    prev_timestamp = millis();

    DEBUG_Serial.print("target:");
    DEBUG_Serial.print(target_psi);
    DEBUG_Serial.print(", ");
    DEBUG_Serial.print("actual:");
    DEBUG_Serial.println(psi_inside);
  }



  while (CMD_Serial.available() > 0) {
    cmd_from_pc[cmd_idx] = CMD_Serial.read();
    if (cmd_from_pc[cmd_idx] == LF) {

      cmd_from_pc[cmd_idx] = 0;
      cmd_idx = -1;

      char cmd_prefix[3];
      strncpy(cmd_prefix, cmd_from_pc, 2);
      cmd_prefix[2] = 0;

      double arg1 = 0;
      double arg2 = 0;
      char* endptr;
      arg1 = strtod(cmd_from_pc + 2, &endptr);
      arg2 = strtod(endptr, &endptr);

      if ((int)arg2 != DEVICE_ADDR) {
        cmd_idx = 0;
        continue;
      }

      if (enable_debug_msg) {
        DEBUG_Serial.print("Received new command: ");
        DEBUG_Serial.print("Command ");
        DEBUG_Serial.print(cmd_prefix);
        DEBUG_Serial.print(" | Argument1= ");
        DEBUG_Serial.print(arg1);
        DEBUG_Serial.print(" | Argument2= ");
        DEBUG_Serial.println(arg2);
      }

      if (!strcmp(cmd_prefix, "it")) {
        // inflate by time
        digitalWrite(v_in, HIGH);
        digitalWrite(v_out, LOW);
        delay((int)arg1);
        digitalWrite(v_in, LOW);
        digitalWrite(v_out, LOW);
      } else if (!strcmp(cmd_prefix, "pi")) {
        CC0_val = (unsigned long)arg1;
        TCC1->CC[0].reg = CC0_val;
        while (TCC1->SYNCBUSY.bit.CC0) {};
      } else if (!strcmp(cmd_prefix, "bb")) {  // bang bang
        controller_sel = 1;
        target_psi = (double)arg1;
      } else if (!strcmp(cmd_prefix, "sm")) {  // sin magnitude and frequency
        enable_sin_gen = true;
        enable_square_gen = false;
        sin_mag = arg1;
      } else if (!strcmp(cmd_prefix, "st")) {
        sin_period = arg1;
      } else if (!strcmp(cmd_prefix, "sq")) {  // square wave magnitude and frequency
        enable_square_gen = true;
        enable_sin_gen = false;
        sin_mag = arg1;
      } else if (!strcmp(cmd_prefix, "so")) {  // sin offset
        sin_offset = arg1;
      } else if (!strcmp(cmd_prefix, "ss")) {  // stop controller
        digitalWrite(v_in, LOW);
        digitalWrite(v_out, LOW);
        controller_sel = 0;
        target_psi = 0;
        act_state = 0;
        enable_sin_gen = false;
        enable_square_gen = false;
      } else if (!strcmp(cmd_prefix, "ex")) {  // stop controller
        controller_sel = 2;
        act_state = 2;
        target_psi = 0;
        digitalWrite(v_in, LOW);
        digitalWrite(v_out, HIGH);
      } else if (!strcmp(cmd_prefix, "in")) {  // stop controller
        controller_sel = 2;
        act_state = 1;
        target_psi = 0;
        digitalWrite(v_in, HIGH);
        digitalWrite(v_out, LOW);
      } else if (!strcmp(cmd_prefix, "sp")) {
        if (arg1 > 0) {
          enable_serial_print = true;
        } else {
          enable_serial_print = false;
        }
      } else if (!strcmp(cmd_prefix, "db")) {
        if (arg1 > 0) {
          enable_debug_msg = true;
        } else {
          enable_debug_msg = false;
        }
      } else if (!strcmp(cmd_prefix, "ti")) {
        act_state = 0;
        for (int i = 0; i < 100; i++) {
          digitalWrite(v_in, HIGH);
          delay(10);
          digitalWrite(v_in, LOW);
          delay(10);
        }
      } else if (!strcmp(cmd_prefix, "to")) {
        act_state = 0;
        for (int i = 0; i < 100; i++) {
          digitalWrite(v_out, HIGH);
          delay(10);
          digitalWrite(v_out, LOW);
          delay(10);
        }
      } else {
        //
      }
    }
    cmd_idx++;
  }
}

void switch_state(int sw_act_state) {
  switch (sw_act_state) {
    case 0:
      act_state = 0;
      digitalWrite(v_in, LOW);
      digitalWrite(v_out, LOW);
      break;
    case 1:
      act_state = 1;
      digitalWrite(v_out, LOW);
      break;
    case 2:
      act_state = 2;
      digitalWrite(v_in, LOW);
      break;
  }
}

void bangbang(double bb_target_psi) {
  if (bb_target_psi > cap_psi) {
    bb_target_psi = cap_psi;
  }
  if (psi_inside > bb_target_psi) {
    switch_state(2);
    // TCC1->CC[0].reg = CC0_val;
    // while (TCC1->SYNCBUSY.bit.CC0) {};
  } else if (psi_inside == bb_target_psi) {
    switch_state(0);
  } else {
    switch_state(1);
    // TCC1->CC[0].reg = CC0_val;
    // while (TCC1->SYNCBUSY.bit.CC0) {};
  }
}

void pid(double pid_target_psi) {
}

double sine_generator(double mag, int period_ms, double offset, unsigned long start_millis) {
  unsigned long curr_t = (millis() - start_millis) % period_ms;
  return offset + mag * sin(((double)curr_t / (double)period_ms) * (2.0 * 3.14159));
}

double square_generator(double mag, int period_ms, double offset, unsigned long start_millis) {
  unsigned long curr_t = (millis() - start_millis) % period_ms;
  if (curr_t <= period_ms / 2) {
    return offset;
  } else {
    return offset + mag;
  }
}
