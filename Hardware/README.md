# Drone

# Custom Flight Controller PCB

This directory contains the KiCad projects for all the drone electronics, designed at chip level (no plug-and-play modules):

*   `Kicad/FCV00` - Flight Controller
*   `Kicad/ESCV00` - 4-in-1 ESC (AM32)
*   `Kicad/RXV00` - ExpressLRS 2.4 GHz receiver
*   `Kicad/VTXV00` - 5.8 GHz analog video transmitter

See `Kicad/Readme.md` for the block diagram, component choices, library installation and the list of items to verify before ordering boards.

The flight controller specifications are below.

## Hardware Specifications

*   **Form Factor:** 30.5 x 30.5 mm mounting pattern (Standard 5-inch stack).
*   **Microcontroller:** STM32F405RGT6 (168 MHz Cortex-M4F, 1 MB flash).
*   **IMU (Gyro/Accel):** TDK InvenSense ICM-42688-P on a dedicated **SPI1** bus with its own LDO and external 32 kHz CLKIN.
*   **Barometer:** ST LPS22DF (I2C1).
*   **Blackbox:** Winbond W25Q128JV 16 MB SPI flash (SPI3).
*   **OSD:** AT7456E chip on SPI2 for analog video telemetry overlay.
*   **Power Supply (BEC):** 
    *   Input: 6S LiPo (up to 25.2V).
    *   Step-down buck converters (TI TPS54360B, 60 V rated): 5V/3A (ELRS Rx, VTx, GPS, LEDs, USB) and 10V/2A (camera / HD VTx).
    *   3.3V: two AP2112K LDOs from 5V (one dedicated to the IMU).

## Pinout & Connectivity

The PCB is designed with the following I/O in mind:
*   **8-pin ESC Connector:** Carries GND, VBAT (Input), Current Sensor (ADC in), and 4x Motor Signals (DShot/PWM out).
*   **UART 1:** ExpressLRS Receiver (CRSF Protocol).
*   **UART 2 / SPI:** Video Transmitter (VTx) control / OSD.
*   **UART 3:** GPS / Compass (for future expansions).
*   **UART 4 / UART 5 TX:** AUX port.  **UART 5 RX:** ESC telemetry.
*   **USB-C:** configuration and DFU (BOOT button).
*   **I2C:** Reserved for external barometers or slow sensors.

## Design Considerations
*   **EMI Shielding:** The IMU is placed away from high-current ESC traces to minimize electromagnetic interference.
*   **Vibration Isolation:** The board must be mounted using rubber dampeners (gummies) to protect the gyro from motor noise.
*   **Decoupling:** Ample decoupling capacitors are placed near the STM32 and IMU to ensure clean power delivery.