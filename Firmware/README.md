# Drone

# Flight Controller Firmware

This directory contains the custom flight control software running on the STM32 microcontroller. The firmware is built around **FreeRTOS** to ensure strict deterministic execution of the critical flight loop while handling slower background tasks like telemetry and RC link parsing.

## Core Architecture (FreeRTOS)

To prevent communication protocols from blocking the flight stabilization, the firmware is divided into prioritized RTOS tasks:

1.  **High-Priority Flight Loop (1kHz - 4kHz):** 
    *   Reads IMU data via SPI.
    *   Applies Digital Low-Pass & Notch Filters to remove motor vibration noise.
    *   Computes Attitude Estimation (Mahony/Madgwick quaternion filters).
    *   Calculates the PID control output for Roll, Pitch, and Yaw.
    *   Mixes outputs and sends DShot commands to the 4-in-1 ESC.
2.  **Medium-Priority RC Task (250Hz / 500Hz):** 
    *   Parses incoming CRSF packets from the ExpressLRS receiver via UART.
    *   Maps stick inputs to desired angles/rates.
3.  **Low-Priority Telemetry & Video Task (10Hz):** 
    *   Reads battery voltage and current consumption.
    *   Sends record Start/Stop commands to the FPV camera.
    *   Updates OSD data.

## Flight Dynamics

*   **Attitude Estimation:** Fusing accelerometer and gyroscope data to calculate the drone's absolute orientation in 3D space.
*   **PID Controller:** Custom Proportional-Integral-Derivative loops tuned for 5-inch freestyle/racing dynamics.
*   **Motor Protocol:** Utilizing **DShot600** (Digital Shot) to send precise, noise-free throttle values to the ESC.

## Development Setup

*   **Toolchain:** GCC ARM Embedded / STM32CubeIDE.
*   **HAL:** STM32 Hardware Abstraction Layer (HAL) / LL drivers.
*   **RTOS:** FreeRTOS (CMSIS-V2).

### How to Build
1. Clone the repository.
2. Open the `.ioc` file in STM32CubeMX / STM32CubeIDE.
3. Generate code and compile using the standard ARM GCC toolchain.
4. Flash via ST-Link using SWD interface.