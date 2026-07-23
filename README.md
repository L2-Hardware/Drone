# Drone

# Custom 5-Inch Quadcopter Project

Welcome to the main repository of our custom-built 5-inch FPV drone. This project is a collaborative effort to design, build, and program a high-performance quadcopter completely from scratch, bridging custom mechanical engineering with bespoke hardware and software design.

## Project Overview

Instead of relying on off-the-shelf Flight Controllers (FC) or pre-compiled firmware like Betaflight/ArduPilot, this project aims to build the core systems from the ground up to deeply understand drone flight dynamics, sensor fusion, and real-time embedded systems.

The project is divided into three main domains:
*   **Mechanics & Frame:** Custom 5-inch carbon fiber frame designed from scratch (designed by [Friend's Name]).
*   **Hardware (FC PCB):** A custom-designed Flight Controller board based on the STM32 architecture.
*   **Firmware (MCU):** A custom RTOS-based flight control software written in C/C++.

## System Architecture

*   **Power & Propulsion:** 6S LiPo Battery, Commercial 4-in-1 ESC (e.g., Hobbywing/T-Motor running BLHeli_32), and 4x Brushless Motors (2207/2306).
*   **Radio Control:** ExpressLRS (ELRS) 2.4GHz receiver communicating via CRSF protocol for ultra-low latency.
*   **Video System (FPV):** Isolated video transmission system (Analog 5.8GHz VTx / Digital HD System) triggered by the custom FC.
*   **Brain:** Custom STM32 Flight Controller (See `/Hardware` and `/Firmware` folders).

## Repository Structure

*   `/Mechanics` - 3D models, CAD files, and CNC routing paths for the frame.
*   `/Hardware` - KiCad/Altium project files for the Flight Controller PCB.
*   `/Firmware` - STM32 source code, RTOS configuration, and PID algorithms.

## Status
*Active Development* - Currently designing the FC PCB and prototyping the RTOS task scheduler.