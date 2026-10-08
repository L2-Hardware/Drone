"""ESCV00 - 4-in-1 ESC for AM32 firmware.

Per channel: STM32F051K8U6 (or pin-compatible AT32F421K8U7) + DRV8300D 3-phase gate driver + 6x BSZ018N04LS6.
Pin-out follows AM32 HARDWARE_GROUP_F0_B / HARDWARE_GROUP_AT_B + AT_045 (same pins on both MCUs):
  input PB4 (TIM3_CH1), phase A: PA10 high / PB1 low, B: PA9 / PB0, C: PA8 / PA7,
  comparator: PA0 = phase A, PA4 = phase B, PA5 = phase C, PA1 = virtual neutral (COMP1 INP),
  VBAT ADC PA6 (10k/1k divider, AM32 default VOLTAGE_DIVIDER 110), telemetry TX PB6 (USART1).
"""
import parts as P
import project
from schgen import Board

B = Board("ESCV00", "4-in-1 ESC", "V00",
          comments=["4x (STM32F051K8U6 / AT32F421K8U7 + DRV8300D + 6x BSZ018N04LS6), AM32 firmware",
                    "2S-6S, 30.5x30.5 mm pattern, 6-layer 2oz recommended",
                    "Total current shunt 0.25 mOhm + INA181A3 -> 25 mV/A to FC"])
B.root_notes.append(
    "ESCV00 - 4-IN-1 ESC (AM32)\n"
    "Channel sheet is used 4 times (CH1..CH4 -> MOTOR1..4, M1_x..M4_x).\n"
    "Flash the AM32 bootloader once per MCU via the SWD pads (SWDIO/SWCLK/NRST + 3V3/GND),\n"
    "then update firmware over the signal wire (Betaflight passthrough / AM32 configurator).\n"
    "AM32 target: F051 -> HARDWARE_GROUP_F0_B, AT32F421 -> HARDWARE_GROUP_AT_B + HARDWARE_GROUP_AT_045\n"
    "  (identical to the TBS_6S_4IN1_F421 pin-out). Set DEAD_TIME to suit the DRV8300 + BSZ018N04LS6.\n"
    "Current: 4x 1 mOhm 2512 in parallel (0.25 mOhm) x INA181A3 (100 V/V) = 25 mV/A  -> Betaflight ibata_scale 250\n"
    "Battery voltage to FC: VBAT on connector pin 1 (FC measures it itself).\n")

# ============================================================================ CHANNEL (x4)
ch = B.sheet("Channel", "channel.kicad_sch",
             instances=[{"name": f"CH{i}", "ref_base": i * 100,
                         "portmap": {"SIG_IN": f"MOTOR{i}", "TLM": "ESC_TLM", "PH_A": f"M{i}_A", "PH_B": f"M{i}_B",
                                     "PH_C": f"M{i}_C"}} for i in (1, 2, 3, 4)],
             ports=["SIG_IN", "TLM", "PH_A", "PH_B", "PH_C"], globals_=["ESC_VBAT_SENSE"])
ch.note("ESC CHANNEL: MCU (AM32) -> DRV8300D (bootstrap diodes integrated, MODE/DT open = non-inverted, fixed dead time)\n"
        "Back-EMF sense: phase dividers 20k/2.2k to PA0/PA4/PA5, virtual neutral 3x 20k + 750R to PA1.  Gate R 4.7R.")
ch.add("eMCU:STM32F051K8U6", pins={
    "VDD": "+3V3", "VDDA": "VDDA", "NRST": "NRST", "BOOT0": "BOOT0", "PF0": "NC", "PF1": "NC", "VSS": "GND",
    "PA0": "SENSE_A", "PA1": "SENSE_N", "PA2": "NC", "PA3": "NC", "PA4": "SENSE_B", "PA5": "SENSE_C",
    "PA6": "ESC_VBAT_SENSE", "PA7": "C_LO", "PA8": "C_HI", "PA9": "B_HI", "PA10": "A_HI", "PA11": "NC", "PA12": "NC",
    "PA13": "SWDIO", "PA14": "SWCLK", "PA15": "NC", "PB0": "B_LO", "PB1": "A_LO", "PB2": "NC", "PB3": "NC",
    "PB4": "SIG_MCU", "PB5": "NC", "PB6": "TLM_MCU", "PB7": "NC", "PB8": "NC"})
ch.C("100nF", "+3V3")
ch.C("100nF", "+3V3")
ch.C("1uF", "+3V3")
ch.FB("120R@100MHz", "+3V3", "VDDA", fp=P.FB0402, fields={"MPN": "BLM15PX121SN1D"})
ch.C("1uF", "VDDA")
ch.C("100nF", "VDDA")
ch.R("10k", "BOOT0", "GND")
ch.C("100nF", "NRST")
ch.R("100R", "SIG_IN", "SIG_MCU")
ch.R("1k", "TLM_MCU", "TLM")
for n in ("SWDIO", "SWCLK", "NRST"):
    ch.TP(n, P.TP10)
ch.add("eInterface:DRV8300DRGER", pins={
    "GVDD": "+10V", "GND": "GND", "EP": "GND", "MODE": "NC", "DT": "NC",
    "INHA": "A_HI", "INLA": "A_LO", "INHB": "B_HI", "INLB": "B_LO", "INHC": "C_HI", "INLC": "C_LO",
    "BSTA": "BST_A", "GHA": "GHA_DRV", "SHA": "PH_A", "GLA": "GLA_DRV",
    "BSTB": "BST_B", "GHB": "GHB_DRV", "SHB": "PH_B", "GLB": "GLB_DRV",
    "BSTC": "BST_C", "GHC": "GHC_DRV", "SHC": "PH_C", "GLC": "GLC_DRV"})
ch.C("10uF 25V", "+10V", fp=P.C0805)
ch.C("100nF", "+10V")
for ph in "ABC":
    ch.C("1uF 25V X7R", f"BST_{ph}", f"PH_{ph}", fp=P.C0603)
    ch.R("4.7R", f"GH{ph}_DRV", f"GH_{ph}")
    ch.R("4.7R", f"GL{ph}_DRV", f"GL_{ph}")
    ch.add("eTransistor:BSZ018N04LS6", pins={"G": f"GH_{ph}", "D": "VBAT", "S": f"PH_{ph}"})
    ch.add("eTransistor:BSZ018N04LS6", pins={"G": f"GL_{ph}", "D": f"PH_{ph}", "S": "GND"})
    ch.R("20k", f"PH_{ph}", f"SENSE_{ph}")
    ch.R("2.2k", f"SENSE_{ph}", "GND")
    ch.R("20k", f"PH_{ph}", "SENSE_N")
ch.R("750R", "SENSE_N", "GND")
ch.C("10uF 50V X7R", "VBAT", fp=P.C1206)
ch.C("10uF 50V X7R", "VBAT", fp=P.C1206)
ch.C("100nF 50V", "VBAT", fp=P.C0603)

# ============================================================================ POWER / IO
s = B.sheet("Power", "power.kicad_sch")
s.note("POWER: battery pads, current shunt (low side), 10V gate-driver rail (LMR16006Y, 2.1 MHz), 3.3V LDO for the 4 MCUs.\n"
       "Add a 470-1000uF 35V low-ESR electrolytic on the battery leads (not on the PCB).\n"
       "LMR16006: Vout = 0.765V x (1 + 121k/10k) = 10.0V.  Shunt: BAT- pad -> 4x 1mOhm -> board GND.")
s.TP("VBAT", P.PAD5x8, "BAT+")
s.TP("BAT_N", P.PAD5x8, "BAT-")
for _ in range(4):
    s.R("1mR 3W", "GND", "BAT_N", fp=P.R2512, fields={"MPN": "WSLP2512R0010FEA", "Manufacturer": "Vishay"})
s.R("10R", "GND", "ISNS_P")
s.R("10R", "BAT_N", "ISNS_N")
s.C("100nF", "ISNS_P", "ISNS_N")
s.add("eAmplifier:INA181A3IDBVR", pins={"V+": "+3V3", "GND": "GND", "+": "ISNS_P", "-": "ISNS_N", "REF": "GND", "~": "CURR_OUT"})
s.C("100nF", "+3V3")
s.R("1k", "CURR_OUT", "ESC_CURR")
s.C("10nF", "ESC_CURR")
# shared battery sense for the 4 MCUs (AM32 low-voltage cut-off / telemetry)
s.R("10k 1%", "VBAT", "ESC_VBAT_SENSE")
s.R("1k 1%", "ESC_VBAT_SENSE", "GND")
s.C("100nF", "ESC_VBAT_SENSE")
# 10 V gate driver rail
s.add("eConverterDCDC:LMR16006YDDCR", pins={"VIN": "VBAT", "~{SHDN}": "EN_10V", "GND": "GND", "CB": "CB_10V",
                                             "SW": "SW_10V", "FB": "FB_10V"})
s.R("100k", "VBAT", "EN_10V")
s.C("2.2uF 50V", "VBAT", fp=P.C0805)
s.C("100nF 50V", "VBAT", fp=P.C0603)
s.C("100nF", "CB_10V", "SW_10V")
s.D("D_Schottky", "PMEG6010CEH", "GND", "SW_10V", P.D_SOD123F, fields={"MPN": "PMEG6010CEH,115"})
s.L("10uH SWPA3012S-100MT", "SW_10V", "+10V", fp=P.L_SWPA3012, fields={"MPN": "SWPA3012S100MT", "Manufacturer": "Sunlord"})
s.R("121k 1%", "+10V", "FB_10V")
s.R("10k 1%", "FB_10V", "GND")
s.C("10uF 25V", "+10V", fp=P.C0805)
s.C("10uF 25V", "+10V", fp=P.C0805)
# 3.3 V
s.add("eLinearReg:MCP1703AT-3302E_MB", pins={"VI": "+10V", "GND": "GND", "VO": "+3V3"})
s.C("1uF 25V", "+10V", fp=P.C0603)
s.C("4.7uF 10V", "+3V3", fp=P.C0603)
s.R("1k", "+3V3", "LED_PWR_A")
s.LED("GREEN", "LED_PWR_A", "GND")
for n in ("+3V3", "GND", "+10V"):
    s.TP(n, P.TP15)
# FC connector
s.add("eConnector:JST_SH_SM08B-SRSS-TB", "FC", pins={"1": "VBAT", "2": "GND", "3": "ESC_CURR", "4": "ESC_TLM", "5": "MOTOR1",
                                                      "6": "MOTOR2", "7": "MOTOR3", "8": "MOTOR4", "MP": "NC"})
s.R("10k", "ESC_TLM", "+3V3")
# motor pads
for m in (1, 2, 3, 4):
    for ph in "ABC":
        s.TP(f"M{m}_{ph}", P.PAD3x5, f"M{m}{ph}")
for _ in range(4):
    s.add("eMechanical:MountingHole", "M3", P.MH_M3, {})

NETCLASSES = (
    [project.netclass("Default", 0.15), project.netclass("Power", 1.0, clearance=0.2, via_d=0.6, via_drill=0.3),
     project.netclass("Gate", 0.25), project.netclass("Rail", 0.4)],
    [("VBAT", "Power"), ("GND", "Power"), ("BAT_N", "Power"), ("M?_?", "Power"), ("/CH?/GH_?", "Gate"),
     ("/CH?/GL_?", "Gate"), ("+10V", "Rail"), ("+3V3", "Rail")],
)
