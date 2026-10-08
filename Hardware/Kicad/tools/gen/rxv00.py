"""RXV00 - ExpressLRS 2.4 GHz receiver: ESP32-C3FH4 + SX1281.

GPIO map = ELRS "Generic C3 2400" layout (ExpressLRS/targets RX/Generic C3 2400.json):
  radio_busy 3, radio_dio1 1, radio_miso 5, radio_mosi 4, radio_nss 7, radio_rst 2, radio_sck 6,
  serial_rx 20, serial_tx 21, button 9.  LED: plain LED on GPIO8 (active low) -> see RXV00_hardware.json
"""
import json
import os

import parts as P
import project
from schgen import Board

B = Board("RXV00", "ELRS 2.4GHz Receiver", "V00",
          comments=["ESP32-C3FH4 + SX1281, ExpressLRS 3.5+ (Unified_ESP32C3_2400_RX)",
                    "Connector matches FCV00 'RX' port (5V GND TX RX), u.FL antenna",
                    "2-layer or 4-layer 0.8mm, controlled 50 ohm RF trace"])
B.root_notes.append(
    "RXV00 - EXPRESSLRS 2.4 GHz RECEIVER\n"
    "Firmware: ELRS Unified_ESP32C3_2400_RX, upload RXV00_hardware.json (in this folder) as hardware layout.\n"
    "First flash: USB pads (GPIO18/19, ESP32-C3 native USB) or UART pads with BOOT (GPIO9) held low.\n"
    "Later updates: WiFi or Betaflight passthrough.\n"
    "RF matching component values are START VALUES - tune with a VNA (SX1281 PA / LNA_IN of ESP32-C3).\n")

# ============================================================================ MCU + POWER
s = B.sheet("MCU", "mcu.kicad_sch")
s.note("ESP32-C3FH4 (4MB flash in package) + 3.3V LDO.  GPIO2/GPIO8/GPIO9 are strapping pins: GPIO2 is pulled high by the\n"
       "SX1281 NRESET internal pull-up, GPIO8 high via LED/10k, GPIO9 = BOOT button.  40 MHz crystal.")
s.add("eConnector:JST_SH_SM04B-SRSS-TB", "FC", pins={"1": "+5V", "2": "GND", "3": "RX_IN", "4": "TX_OUT", "MP": "NC"})
for n, lbl in (("+5V", "5V"), ("GND", "GND"), ("RX_IN", "RX"), ("TX_OUT", "TX")):
    s.TP(n, P.TP15, lbl)
s.C("4.7uF 10V", "+5V", fp=P.C0603)
s.add("eLinearReg:AP2112K-3.3TRG1", pins={"VIN": "+5V", "EN": "+5V", "GND": "GND", "VOUT": "+3V3"})
s.C("10uF 10V", "+3V3", fp=P.C0603)
s.C("100nF", "+3V3")
s.add("eMCU:ESP32-C3FH4", pins={
    "VDD3P3": "+3V3", "VDD3P3_RTC": "+3V3", "VDD3P3_CPU": "+3V3", "VDDA": "+3V3", "VDD_SPI": "VDD_SPI",
    "CHIP_EN": "CHIP_EN", "XTAL_P": "XTAL_P", "XTAL_N": "XTAL_N", "LNA_IN": "WIFI_RF", "GND": "GND",
    "XTAL_32K_P/GPIO0": "NC", "XTAL_32K_N/GPIO1": "RADIO_DIO1", "GPIO2": "RADIO_RST", "GPIO3": "RADIO_BUSY",
    "MTMS/GPIO4": "RADIO_MOSI", "MTDI/GPIO5": "RADIO_MISO", "MTCK/GPIO6": "RADIO_SCK", "MTDO/GPIO7": "RADIO_NSS",
    "GPIO8": "LED_N", "GPIO9": "BOOT", "GPIO10": "NC", "GPIO18/USB_D-": "USB_DM", "GPIO19/USB_D+": "USB_DP",
    "U0RXD/GPIO20": "RX_IN", "U0TXD/GPIO21": "TX_OUT",
    "SPIHD": "NC", "SPIWP": "NC", "SPICS0": "NC", "SPICLK": "NC", "SPID": "NC", "SPIQ": "NC"})
for _ in range(4):
    s.C("100nF", "+3V3")
s.C("1uF", "+3V3")
s.C("1uF", "VDD_SPI")
s.R("10k", "CHIP_EN", "+3V3")
s.C("1uF", "CHIP_EN")
s.add("eCrystal:Crystal_GND24", "40MHz 10pF", P.XTAL2016, {"1": "XTAL_P", "3": "XTAL_N", "2": "GND", "4": "GND"},
      fields={"MPN": "X201640MLB4SI", "Manufacturer": "Yangxing"})
s.C("12pF NP0", "XTAL_P")
s.C("12pF NP0", "XTAL_N")
s.R("10k", "BOOT", "+3V3")
s.add("eSwitch:SW_Push", "BOOT", pins={"1": "BOOT", "2": "GND"}, fields={"MPN": "B3U-1000P", "Manufacturer": "Omron"})
s.R("10k", "LED_N", "+3V3")
s.R("1k", "+3V3", "LED_A")
s.LED("BLUE", "LED_A", "LED_N")
s.TP("USB_DP", P.TP10, "D+")
s.TP("USB_DM", P.TP10, "D-")
# WiFi antenna (used for ELRS WiFi updates only)
s.C("DNP", "WIFI_RF", fp=P.C0402, dnp=True)
s.L("0R / tune", "WIFI_RF", "WIFI_ANT", fp=P.L0402)
s.C("DNP", "WIFI_ANT", fp=P.C0402, dnp=True)
s.add("eAntenna:Antenna_Chip", "2450AT18A100", pins={"1": "WIFI_ANT"}, fields={"MPN": "2450AT18A100E", "Manufacturer": "Johanson"})

# ============================================================================ RADIO
s = B.sheet("Radio", "radio.kicad_sch")
s.note("SX1281: DC-DC mode (15uH on DCC_SW), 52 MHz crystal (internal load caps), VR_PA feeds RFIO through a choke.\n"
       "RF chain: RFIO -> DC block -> 3rd-order low-pass (1pF / 4.7nH / 1pF, fc ~3.3 GHz) -> u.FL.  START VALUES - tune.")
s.FB("120R@100MHz", "+3V3", "+3V3_RF", fp=P.FB0402, fields={"MPN": "BLM15PX121SN1D"})
s.C("10uF 10V", "+3V3_RF", fp=P.C0603)
s.add("eRFModule:SX1281IMLTRT", pins={
    "VBAT": "+3V3_RF", "VBAT_IO": "+3V3_RF", "VDD_IN": "VREG", "DCC_FB": "VREG", "DCC_SW": "DCC_SW", "VR_PA": "VR_PA",
    "XTA": "XTA", "XTB": "XTB", "GND": "GND", "EP": "GND", "RFIO": "RFIO",
    "~{NSS}": "RADIO_NSS", "SCK": "RADIO_SCK", "MOSI": "RADIO_MOSI", "MISO": "RADIO_MISO",
    "~{NRESET}": "RADIO_RST", "BUSY": "RADIO_BUSY", "DIO1": "RADIO_DIO1", "DIO2": "NC", "DIO3": "NC"})
s.C("100nF", "+3V3_RF")
s.C("100nF", "+3V3_RF")
s.L("15uH", "DCC_SW", "VREG", fp=P.L0805, fields={"MPN": "LQM21PN150MC0", "Manufacturer": "Murata"})
s.C("470nF", "VREG")
s.C("47pF NP0", "VR_PA")
s.C("470nF", "VR_PA")
s.L("47nH (tune)", "VR_PA", "RFIO", fp=P.L0402, fields={"MPN": "LQW15AN47NJ00", "Manufacturer": "Murata"})
s.add("eCrystal:Crystal_GND24", "52MHz 8pF", P.XTAL2016, {"1": "XTA", "3": "XTB", "2": "GND", "4": "GND"},
      fields={"MPN": "X201652MOB4SI", "Manufacturer": "Yangxing", "Note": "SX1280 reference: 52 MHz, +/-10ppm"})
s.R("10k", "RADIO_NSS", "+3V3_RF")
s.C("10pF NP0", "RFIO", "RF1", fp=P.C0402)
s.C("1pF NP0", "RF1", fp=P.C0402)
s.L("4.7nH", "RF1", "RF2", fp=P.L0402, fields={"MPN": "LQP15MN4N7B02", "Manufacturer": "Murata"})
s.C("1pF NP0", "RF2", fp=P.C0402)
s.add("eConnector:Conn_Coaxial", "U.FL", P.UFL, {"1": "RF2", "2": "GND"}, fields={"MPN": "U.FL-R-SMT-1(10)", "Manufacturer": "Hirose"})

NETCLASSES = ([project.netclass("Default", 0.15), project.netclass("RF_50R", 0.3, clearance=0.2)],
              [("/Radio/RF?", "RF_50R"), ("/Radio/RFIO", "RF_50R"), ("/MCU/WIFI_*", "RF_50R")])

HARDWARE_JSON = {
    "serial_rx": 20, "serial_tx": 21,
    "radio_busy": 3, "radio_dio1": 1, "radio_miso": 5, "radio_mosi": 4, "radio_nss": 7, "radio_rst": 2, "radio_sck": 6,
    "power_min": 0, "power_high": 0, "power_max": 0, "power_default": 0, "power_control": 0, "power_values": [13],
    "power_lna_gain": 0,
    "led_red": 8, "led_red_invert": True,
    "button": 9,
}
_d = os.path.join(project.KICAD_DIR, "RXV00")
os.makedirs(_d, exist_ok=True)
json.dump(HARDWARE_JSON, open(os.path.join(_d, "RXV00_hardware.json"), "w"), indent=4)
