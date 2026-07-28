# Drone

# Custom Flight Controller PCB

This directory contains the schematic and PCB layout files for the custom Flight Controller (FC). The board is designed to interface safely and efficiently with a commercial 4-in-1 ESC while providing robust power and data routing for all drone peripherals.

## Hardware Specifications

*   **Form Factor:** 30.5 x 30.5 mm mounting pattern (Standard 5-inch stack).
*   **Microcontroller:** STM32F405 / STM32G473 (with FPU for fast floating-point math).
*   **IMU (Gyro/Accel):** Invensense ICM-42688-P or Bosch BMI270, connected via high-speed **SPI** for minimal latency.
*   **OSD (Optional):** AT7456E chip connected via SPI for analog video telemetry overlay.
*   **Power Supply (BEC):** 
    *   Input: 6S LiPo (up to 25.2V).
    *   Step-down Buck Converters: 5V (for ELRS Rx, VTx, LEDs) and 3.3V (for STM32 and IMU) with strict LC filtering.

## Pinout & Connectivity

The PCB is designed with the following I/O in mind:
*   **8-pin ESC Connector:** Carries GND, VBAT (Input), Current Sensor (ADC in), and 4x Motor Signals (DShot/PWM out).
*   **UART 1:** ExpressLRS Receiver (CRSF Protocol).
*   **UART 2 / SPI:** Video Transmitter (VTx) control / OSD.
*   **UART 3:** GPS / Compass (for future expansions).
*   **I2C:** Reserved for external barometers or slow sensors.

## Design Considerations
*   **EMI Shielding:** The IMU is placed away from high-current ESC traces to minimize electromagnetic interference.
*   **Vibration Isolation:** The board must be mounted using rubber dampeners (gummies) to protect the gyro from motor noise.
*   **Decoupling:** Ample decoupling capacitors are placed near the STM32 and IMU to ensure clean power delivery.