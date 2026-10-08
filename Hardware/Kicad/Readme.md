# KiCad projects - drone electronics

## Libraries

All projects use the official library **[L2-Hardware/Kicad_Libs](https://github.com/L2-Hardware/Kicad_Libs)**
through the folder `Hardware/Kicad/KiCad_Libs` (ignored by git). The projects' `sym-lib-table` / `fp-lib-table`
point to `${KIPRJMOD}/../KiCad_Libs/<eLib>/...`.

Setup (once per PC):

```
cd C:\git\PCB
git clone https://github.com/L2-Hardware/Kicad_Libs.git      (-> C:\git\PCB\Kicad_Libs)
cd C:\git\PCB\Drone\Hardware\Kicad
bring_libs.bat                                                  (junction KiCad_Libs -> C:\git\PCB\Kicad_Libs)
```

### Adding new components: `KiCad_Libs_ToAdd/`

New parts that are not yet in the official library go into `KiCad_Libs_ToAdd/`, using the same layout
(`<eLib>/datasheet`, `<eLib>.3dshapes`, `<eLib>.pretty`, `<eLib>.kicad_sym` with only the new symbols).

1. `merge_libs.bat --clean`
   - appends the new symbols to `KiCad_Libs/<eLib>/<eLib>.kicad_sym` (a `.bak` is kept; existing names are skipped)
   - copies footprints, STEP models and datasheets (existing files are not overwritten, unless `--force`)
   - empties `KiCad_Libs_ToAdd` (only its README stays)
2. Open the touched libraries once in the Symbol Editor and save (upgrades them to your KiCad version),
   delete the `.bak` files, then commit + push in `C:\git\PCB\Kicad_Libs`.
3. Commit the emptied `KiCad_Libs_ToAdd` in this repo.

The schematics and PCBs embed their symbols and footprints, so they open even before the merge;
3D models (`${KIPRJMOD}/../KiCad_Libs/<eLib>/<eLib>.3dshapes/...`) show once the parts are in the official library.

Current content of `KiCad_Libs_ToAdd` (drone boards): footprints and 3D models from the official KiCad libraries,
symbols generated from the KiCad symbol pin tables where available, otherwise from the vendor datasheet
(those carry a `Verify` field). It also contains generic symbols (`R`, `C`, `L`, `LED`, power symbols ...):
if the official library already has symbols with the same names they are skipped by the merge.

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
* `<NAME>_BOM.csv` - grouped BOM with manufacturer part numbers for the active parts
* `RXV00/RXV00_hardware.json` - ExpressLRS hardware layout for the receiver

## Validation done
* Every schematic was exported with `kicad-cli`. KiCad's connectivity matches the intended netlist exactly (no
  merged or split nets).
* Every symbol pin maps to a footprint pad. Every footprint pad that needs a net has one.
* All symbol libraries load in KiCad.
* Files are written in the KiCad 7 format. KiCad 8/9 open them and upgrade them on save. Run ERC in KiCad once
  after opening: the KiCad 7 command line has no ERC.

## Verify before ordering boards
Parts whose pin table was typed from a datasheet carry a `Verify` field. Check them against the latest datasheet:

| Part | What to check |
|---|---|
| AT7456E | Uses the MAX7456 pinout. Check the HTSSOP exposed-pad size. |
| SX1281 | Pin table from Semtech DS rev 3.x. RF matching values are starting points (tune with a VNA). |
| RTC6705 | Pin table from `datasheet/RTC6705-RichWave.pdf`. The exposed-pad size is not given (QFN-40 6x6, EP 4.6 assumed). Loop filter, output match and the BUFVDD power-control path are starting points. |
| DRV8300DRGER | Pin table from the TI datasheet. Check the RGE exposed-pad size. |
| ICM-42688-P | Pin table from the KiCad IIM-42652 symbol (same LGA-14 package). Check the RESV pins. |
| BSZ018N04LS6 | NexFET SON3.3 land pattern reused. Compare with Infineon's PG-TSDSON-8 FL footprint. |
| TPS54360B | The compensation network is a starting point. Run TI WEBENCH for the final values. |

Passive, crystal and LED part numbers are suggestions: confirm them (stock, load capacitance, voltage rating) at
your distributor or assembler.

## Next steps
1. Merge `KiCad_Libs_ToAdd` into the official library (above), open each project, run ERC.
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
`tools/gen/` holds the scripts that produced the `KiCad_Libs_ToAdd` parts, schematics, BOMs and PCB set-up:
`build.py` (libraries + schematics + BOM), `check.py` (connectivity check) and `pcbgen.py` (PCB set-up).
**Re-running them overwrites the project files.** They are a starting point: once you start editing in KiCad,
KiCad is the master.
