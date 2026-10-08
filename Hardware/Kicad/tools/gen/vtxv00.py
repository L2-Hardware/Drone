"""VTXV00 - analog 5.8 GHz video transmitter: RTC6705 + RFPA5542 + STM32F031G6U6 / GD32F130G6U6.

MCU pin-out follows OpenVTx target "Generic_GD32F130" (EWRF E7082VM clone):
  UART PA9 (single-wire SmartAudio/Tramp/MSP), RTC6705 bit-banged SPI: SS PB3, CLK PA15, MOSI PB4,
  LEDs PA4 red / PA3 green / PA2 blue, PA_EN ("VREF") PA0, PDET ("VPD") PA1, RTC_BIAS PWM PB5, button PA6.
"""
import parts as P
import project
from schgen import Board

B = Board("VTXV00", "5.8GHz Video Transmitter", "V00",
          comments=["RTC6705 FM video modulator + Qorvo RFPA5542 PA (up to ~400 mW), OpenVTx-compatible MCU",
                    "Connector matches FCV00 'VTX' port (10V 5V GND VIDEO TX RX)",
                    "4-layer, 50 ohm coplanar RF trace, heatsink/thermal vias under the PA"])
B.root_notes.append(
    "VTXV00 - 5.8 GHz ANALOG VTX\n"
    "Firmware: OpenVTx (target Generic_GD32F130 when populated with GD32F130G6U6) or custom firmware on STM32F031G6U6.\n"
    "Power control loop (from OpenVTx): PB5 PWM -> RC -> emitter follower -> RTC6705 BUFVDD, closed loop on RFPA5542 PDET.\n"
    "RF values (RTC6705 output match, attenuator pad, loop filters, harmonic filter) are START VALUES - tune on the bench.\n"
    "Legal: 25 mW EIRP licence-free in the EU (5.8 GHz SRD); higher power needs an amateur radio licence.\n")

# ============================================================================ CONTROL
s = B.sheet("Control", "control.kicad_sch")
s.note("CONTROL: 5V in -> RFPA5542 (via 3A ferrite), 3.3V LDO for MCU + RTC6705.\n"
       "MCU = STM32F031G6U6 footprint/pin-out (GD32F130G6U6 drop-in for OpenVTx).  SWD pads for first flashing.")
s.add("eConnector:JST_SH_SM06B-SRSS-TB", "FC", pins={"1": "NC", "2": "+5V", "3": "GND", "4": "VIDEO_IN", "5": "FC_TX",
                                                      "6": "FC_RX", "MP": "NC"})
s.C("22uF 10V", "+5V", fp=P.C0805)
s.C("100nF", "+5V")
s.FB("120R 3A", "+5V", "+5V_PA", fp=P.FB0603, fields={"MPN": "BLM18KG121TN1D", "Manufacturer": "Murata"})
s.C("22uF 10V", "+5V_PA", fp=P.C0805)
s.add("eLinearReg:AP2112K-3.3TRG1", pins={"VIN": "+5V", "EN": "+5V", "GND": "GND", "VOUT": "+3V3"})
s.C("1uF 16V", "+5V")
s.C("4.7uF 10V", "+3V3", fp=P.C0603)
s.add("eMCU:STM32F031G6U6", pins={
    "VDD": "+3V3", "VDDA": "+3V3", "VSS": "GND", "BOOT0": "BOOT0", "NRST": "NRST", "PF0": "NC", "PF1": "NC",
    "PA0": "PA_EN", "PA1": "VPD", "PA2": "LED_B", "PA3": "LED_G", "PA4": "LED_R", "PA5": "NC", "PA6": "BUTTON",
    "PA7": "NC", "PA8": "NC", "PA9": "UART_SA", "PA10": "UART_RX", "PA13": "SWDIO", "PA14": "SWCLK",
    "PA15": "RTC_CLK", "PB0": "NC", "PB1": "NC", "PB3": "RTC_LE", "PB4": "RTC_DATA", "PB5": "RTC_BIAS_PWM",
    "PB6": "NC", "PB7": "NC"})
s.C("100nF", "+3V3")
s.C("100nF", "+3V3")
s.C("1uF", "+3V3")
s.R("10k", "BOOT0", "GND")
s.C("100nF", "NRST")
s.R("100R", "FC_TX", "UART_SA")
s.R("100R", "FC_RX", "UART_RX")
for col, net in (("RED", "LED_R"), ("GREEN", "LED_G"), ("BLUE", "LED_B")):
    s.R("1k", net, f"{net}_A")
    s.LED(col, f"{net}_A", "GND")
s.R("10k", "BUTTON", "+3V3")
s.add("eSwitch:SW_Push", "BAND/CH", pins={"1": "BUTTON", "2": "GND"}, fields={"MPN": "B3U-1000P", "Manufacturer": "Omron"})
for n in ("SWDIO", "SWCLK", "NRST", "+3V3", "GND"):
    s.TP(n, P.TP10)
# output power control (OpenVTx RTC_BIAS)
s.R("10k", "RTC_BIAS_PWM", "BIAS_RC")
s.C("1uF", "BIAS_RC")
s.add("eTransistor:MMBT3904", pins={"B": "BIAS_RC", "C": "+3V3_RF", "E": "RTC_BUFVDD"})
s.C("100nF", "RTC_BUFVDD")

# ============================================================================ RF
s = B.sheet("RF", "rf.kicad_sch")
s.note("RF: RTC6705 (SPI mode, SPI_SE high, 8 MHz crystal) PAOUT1 (+2 dBm) -> 10 dB pi pad -> RFPA5542 (33 dB gain, ~25 dBm out) -> LPF -> u.FL\n"
       "RFPA5542: VCC 5V, R(VCC2) 0R (15R for better VSWR ruggedness), PA_EN 1nF, PDET 10pF -> MCU ADC (VPD).\n"
       "Video is DC-coupled into VT_MOD (75R input); C footprint available for AC coupling.  Audio PLLs unused.")
s.FB("120R@100MHz", "+3V3", "+3V3_RF", fp=P.FB0603, fields={"MPN": "BLM18PG121SN1D"})
s.C("10uF 10V", "+3V3_RF", fp=P.C0603)
s.add("eRFModule:RTC6705", pins={
    "VDD33_DIG": "+3V3_RF", "V2D5_PLL": "+3V3_RF", "AVDD_6": "+3V3_RF", "AVDD_6.5": "+3V3_RF", "VDD3V3": "+3V3_RF",
    "VDDVT": "+3V3_RF", "PAVDD": "+3V3_RF", "VCOVDD": "+3V3_RF", "LDD2V5": "+3V3_RF", "BUFVDD": "RTC_BUFVDD",
    "GND": "GND", "RFGND": "GND", "EP": "GND",
    "SPI_SE": "+3V3_RF", "S": "NC", "BX": "NC", "SPIDATA/CS0": "RTC_DATA", "SPILE/CS1": "RTC_LE", "SPICLK/CS2": "RTC_CLK",
    "VT_MOD": "VT_MOD", "RF_VT2": "RF_VT2", "AVT1": "AVT1", "ACP1": "ACP1", "AOUT1": "NC", "AVT2": "AVT2", "ACP2": "ACP2",
    "AOUT2": "NC", "REG1D8": "REG1D8", "REG1D8_1": "REG1D8_1", "XTAL1": "RTC_X1", "XTAL2": "RTC_X2",
    "CP": "RTC_CP", "VT": "RTC_VT", "PAOUT1": "RTC_RFOUT", "PAOUT2": "RTC_PAOUT2"})
for _ in range(6):
    s.C("100nF", "+3V3_RF")
s.C("1nF", "+3V3_RF")
s.C("1nF", "+3V3_RF")
s.C("1uF", "REG1D8")
s.C("1uF", "REG1D8_1")
s.add("eCrystal:Crystal_GND24", "8MHz 12pF", P.XTAL3225, {"1": "RTC_X1", "3": "RTC_X2", "2": "GND", "4": "GND"},
      fields={"MPN": "X322508MLB4SI", "Manufacturer": "Yangxing"})
s.C("18pF NP0", "RTC_X1")
s.C("18pF NP0", "RTC_X2")
# synthesizer loop filter (start values)
s.C("1nF", "RTC_CP")
s.R("4.7k", "RTC_CP", "LF_RC")
s.C("10nF", "LF_RC")
s.R("1k", "RTC_CP", "RTC_VT")
s.C("470pF", "RTC_VT")
# audio PLL loop filters (audio unused)
s.R("10k", "ACP1", "AVT1")
s.C("10nF", "AVT1")
s.R("10k", "ACP2", "AVT2")
s.C("10nF", "AVT2")
s.C("100nF", "RF_VT2")
# video input
s.R("0R", "VIDEO_IN", "VT_MOD")
s.R("75R", "VIDEO_IN", "GND", dnp=True)
s.C("10uF (AC option)", "VIDEO_IN", "VT_MOD", fp=P.C0603, dnp=True)
# RTC6705 output -> pi attenuator -> PA
s.R("0R (high pwr)", "RTC_PAOUT2", "RTC_RFOUT", dnp=True)
s.L("DNP (feed opt.)", "RTC_RFOUT", "+3V3_RF", fp=P.L0402, dnp=True)
s.C("10pF NP0", "RTC_RFOUT", "ATT_IN", fp=P.C0402)
s.R("97.6R", "ATT_IN", "GND")
s.R("71.5R", "ATT_IN", "ATT_OUT")
s.R("97.6R", "ATT_OUT", "GND")
s.C("10pF NP0", "ATT_OUT", "PA_IN", fp=P.C0402)
s.add("eAmplifier:RFPA5542", pins={"VCC1": "+5V_PA", "VCC2": "PA_VCC2", "VCC3": "+5V_PA", "GND": "GND", "EP": "GND",
                                    "RFIN": "PA_IN", "PA_EN": "PA_EN", "RFOUT": "PA_OUT", "PDET": "VPD"})
s.C("2.2uF", "+5V_PA", fp=P.C0402)
s.C("2.2uF", "+5V_PA", fp=P.C0402)
s.R("0R", "+5V_PA", "PA_VCC2", fp=P.R0402)
s.C("2.2uF", "PA_VCC2", fp=P.C0402)
s.C("1nF", "PA_EN")
s.C("10pF NP0", "VPD")
s.C("10pF NP0", "PA_OUT", "RF_F1", fp=P.C0402)
s.C("DNP", "RF_F1", fp=P.C0402, dnp=True)
s.L("0R / tune", "RF_F1", "RF_ANT", fp=P.L0402)
s.C("DNP", "RF_ANT", fp=P.C0402, dnp=True)
s.add("eConnector:Conn_Coaxial", "U.FL", P.UFL, {"1": "RF_ANT", "2": "GND"}, fields={"MPN": "U.FL-R-SMT-1(10)", "Manufacturer": "Hirose"})

NETCLASSES = ([project.netclass("Default", 0.15), project.netclass("RF_50R", 0.3, clearance=0.2),
               project.netclass("PA_Power", 0.6)],
              [("/RF/RF_*", "RF_50R"), ("/RF/PA_IN", "RF_50R"), ("/RF/PA_OUT", "RF_50R"), ("/RF/ATT_*", "RF_50R"),
               ("/RF/RTC_RFOUT", "RF_50R"), ("+5V_PA", "PA_Power"), ("+5V", "PA_Power")])

# 20x20 mm M2 mounting pattern (placed by pcbgen)
for _ in range(4):
    B.sheets[0].add("eMechanical:MountingHole", "M2", P.MH_M2, {})
