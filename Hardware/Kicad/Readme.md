# KiCad projects - drone electronics

## Libraries

If you want a local copy of Kicad Libraries for each board project, inside the KiCad directory run:

git submodule add https://github.com/Loredati-svg/Kicad_Library.git
git commit -m "Added Kicad Libs submodule"
git push

If you don't want a local copy of the libraries for each project but you are ok with having a single local copy of it in a different folder and want to link to it from the board project folder, just run the "bring_libs.bat".
This will create a junction link.

### Part convention (same as B0_EE)

All the parts used by the four boards are in the shared [Kicad_Libs](https://github.com/L2-Hardware/Kicad_Libs)
(`${KIPRJMOD}/../KiCad_Libs/<eLib>`). Every real part is named after its manufacturer part number, and the
symbol, footprint, 3D model and datasheet all carry that name:

```
<eLib>.kicad_sym             symbol      <eLib>:STM32F405RGT6
<eLib>.pretty/               footprint   STM32F405RGT6.kicad_mod
<eLib>.3dshapes/             3D model    STM32F405RGT6.step
datasheet/                   datasheet   STM32F405RGT6.pdf  (README.md: manufacturer and full ordering code)
```

Symbols carry the five standard fields only: Reference, Value (= part name), Footprint, Datasheet
(`${KIPRJMOD}/../KiCad_Libs/<eLib>/datasheet/<part>.pdf`) and Description. Plain passives without a part number
(R, C, LED, L) keep the generic symbol with the value and a package footprint. Test points, mounting holes and
solder jumpers are copper only: no 3D model and not in the BOM.

Where the parts come from:
* **Footprints**: official KiCad libraries, renamed after the part. **3D models**: STEP from KiCad 10.
* **Symbols**: generated in a single style. Pin tables come from the official KiCad symbol of the same part where
  KiCad has one. Otherwise they come from the vendor datasheet (see "Verify before ordering boards").

## Boards

| Project | Board | Size / layers | Main parts |
|---|---|---|---|
| `FCV00` | Flight controller | 36x36 mm, 30.5 mm M3 pattern (4 mm holes for grommets), 4 layers | STM32F405RGT6, ICM-42688-P, LPS22DF, AT7456E OSD, W25Q128JV, 2x TPS54360B (5V 3A / 10V 2A), 2x AP2112K-3.3, USB-C |
| `ESCV00` | 4-in-1 ESC (AM32) | 42x42 mm, 30.5 mm M3 pattern, 6 layers 2 oz recommended | 4x (STM32F051K8U6 or AT32F421K8U7 + DRV8300D + 6x BSZ018N04LS6), 0.25 mOhm shunt + INA181A3, LMR16006 10V gate rail |
| `RXV00` | ExpressLRS 2.4 GHz receiver | 22x14 mm, 4 layers | ESP32-C3FH4 + SX1281, u.FL |
| `VTXV00` | 5.8 GHz analog VTX | 27x27 mm, 20x20 mm M2 pattern, 4 layers | RTC6705 + RFPA5542 (~25 dBm), STM32F031G6U6 / GD32F130G6U6 (OpenVTx) |

```
 6S LiPo ──XT60──► ESCV00 ──(JST-SH 8: VBAT GND CURR TLM M1..M4)──► FCV00 ──(JST-SH 4: 5V GND TX RX)──► RXV00 ── 2.4 GHz antenna
                   │  4x BLDC motors                                  │  ├─(JST-SH 6: 10V 5V GND VIDEO TX RX)──► VTXV00 ── 5.8 GHz antenna
                   └──────────────────────────────────────────────────┘  ├─(JST-SH 3: PWR GND VIDEO)◄── analog FPV camera (bought)
                                                                         ├─ GPS / compass port, AUX UART port, LED strip, buzzer
                                                                         └─ USB-C (configuration / DFU)
```

The connectors are pin-matched, so the harnesses are 1:1 JST-SH cables. Power the FC from the ESC harness only,
not from separate battery wires. Otherwise part of the motor return current flows through the JST ground wire
and bypasses the current shunt.

Bought parts that are not designed here: motors, battery, camera, propellers, antennas, frame.

### Each project contains
* `<NAME>.kicad_sch` - hierarchical schematic (root page = overview + design notes, one sub-sheet per block)
* `<NAME>.kicad_pcb` - board outline, mounting holes, layer count, GND plane on In1, every footprint loaded with
  its nets and linked to its symbol (footprints are parked next to the outline, grouped by sheet)
* `<NAME>.kicad_pro` - net classes (power / gate / RF 50 ohm / USB ...) and JLCPCB-compatible minimum rules
* `<NAME>_BOM.csv` - grouped BOM exported from the schematic with `kicad-cli` (Value = part number for real parts)
* `RXV00/RXV00_hardware.json` - ExpressLRS hardware layout for the receiver

## Validation done
* Every schematic was exported with `kicad-cli`. KiCad's connectivity matches the intended netlist exactly (no
  merged or split nets).
* Every symbol pin maps to a footprint pad. Every footprint pad that needs a net has one.
* KiCad 10 `kicad-cli`: no symbol/footprint library mismatch in ERC or DRC, and schematic/PCB parity is clean
  (fields, footprints, BOM/DNP attributes).

## Verify before ordering boards
Parts whose pin table was typed from a datasheet. Check them against the latest datasheet:

| Part | What to check |
|---|---|
| AT7456E | Uses the MAX7456 pinout. Check the HTSSOP exposed-pad size. |
| SX1281IMLTRT | Pin table from Semtech DS rev 3.x. RF matching values are starting points (tune with a VNA). |
| RTC6705 | Pin table from `eRFModule/datasheet/RTC6705.pdf`. The exposed-pad size is not given (QFN-40 6x6, EP 4.6 assumed). Loop filter, output match and the BUFVDD power-control path are starting points. |
| DRV8300DRGER | Pin table from the TI datasheet. Check the RGE exposed-pad size. |
| ICM-42688-P | Pin table from the KiCad IIM-42652 symbol (same LGA-14 package). Check the RESV pins. |
| BSZ018N04LS6ATMA1 | NexFET SON3.3 land pattern reused. Compare with Infineon's PG-TSDSON-8 FL footprint. |
| TPS54360BDDAR | The compensation network is a starting point. Run TI WEBENCH for the final values. |
| X201652MOB4SI | SX1280 reference crystal: 52 MHz, +/-10 ppm. |

Part numbers that could not be found in the manufacturer catalogue: confirm or replace them before ordering.

| Part | Note |
|---|---|
| X322508MLB4SI, X201640MLB4SI, X201652MOB4SI | Not listed by YXC/LCSC. The stored datasheet is the YXC SMD3225 / SMD2016 series sheet. |
| LQM21PN150MC0 | Not in the Murata LQM21PN range (which stops below 15 uH). No datasheet stored. |
| WSLP2512R0010FEA | 1 mOhm WSLP2512: check availability; the stored datasheet is the Vishay WSLP series sheet. |
| SWPA3012S100MT, PMEG3020EH | Datasheet not stored (the vendor site blocks downloads): the Datasheet field links to it. |

Passive, crystal and LED part numbers are suggestions: confirm them (stock, load capacitance, voltage rating) at
your distributor or assembler.

## Next steps
1. Open each project, run ERC.
2. PCB: place the parts (connectors on the edges, IMU away from the bucks, short power loops), then route.
   Use 50 ohm coplanar lines on RXV00/VTXV00 and a full GND plane under the RF parts. On ESCV00, use wide
   polygons for VBAT/phases and thermal vias. Run DRC.
3. Order from JLCPCB / PCBWay: gerbers + BOM + placement file, assembly (ESC 6 layers 2 oz).
4. Bring-up order: power rails, then SWD/DFU, then each sensor, then radio links.

## Firmware notes
* **FCV00**: pin map on the root sheet (gyro SPI1 + external 32 kHz CLKIN on PB0, OSD SPI2, flash SPI3,
  motors TIM8 CH1-4 on PC6-PC9).
* **ESCV00**: AM32. With F051, use `HARDWARE_GROUP_F0_B`. With AT32F421, use `HARDWARE_GROUP_AT_B` +
  `HARDWARE_GROUP_AT_045` (same pinout as `TBS_6S_4IN1_F421`). Flash the bootloader per MCU through the SWD pads
  once.
* **RXV00**: ExpressLRS `Unified_ESP32C3_2400_RX` + `RXV00_hardware.json` (based on "Generic C3 2400").
* **VTXV00**: OpenVTx `Generic_GD32F130` pinout (populate GD32F130G6U6), or your own firmware on the STM32F031.
  Up to 25 mW EIRP is licence-free in the EU. Higher power needs an amateur radio licence.

## Regenerating
`tools/gen/` holds the scripts that produced the libraries, schematics, BOMs and PCB set-up:
`build.py` (libraries + schematics + BOM), `check.py` (connectivity check) and `pcbgen.py` (PCB set-up).
**Re-running them overwrites the project files.** They are a starting point: once you start editing in KiCad,
KiCad is the master. They still produce the old generic part names, so do not re-run them on these boards.
