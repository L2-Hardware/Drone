"""FCV00 - flight controller: STM32F405 + ICM-42688-P + LPS22DF + AT7456E OSD + W25Q128 blackbox.

30.5 x 30.5 mm mounting pattern, 36 x 36 mm board, 6S input.
"""
import parts as P
from schgen import Board

B = Board("FCV00", "Flight Controller", "V00",
          comments=["STM32F405RGT6 / ICM-42688-P / LPS22DF / AT7456E / W25Q128JV",
                    "Input 2S-6S (VBAT max 25.2V). 5V 3A + 10V 2A bucks, 2x 3.3V LDO",
                    "30.5x30.5 mm pattern, 4-layer 1.6mm"])

B.root_notes.append(
    "FCV00 - FLIGHT CONTROLLER\n"
    "MCU pin map (STM32F405RGT6)\n"
    "  SPI1 PA5/PA6/PA7  CS PA4  INT PC4  CLKIN PB0 -> ICM-42688-P (gyro)\n"
    "  SPI2 PB13/PB14/PB15  CS PB12        -> AT7456E (OSD)\n"
    "  SPI3 PB3/PB4/PB5  CS PA15           -> W25Q128 (blackbox)\n"
    "  I2C1 PB8/PB9                        -> LPS22DF baro + GPS compass\n"
    "  USART1 PB6/PB7 -> ELRS RX     USART2 PA2/PA3 -> VTX (MSP/SmartAudio)\n"
    "  USART3 PB10/PB11 -> GPS       UART4 PA0/PA1 -> AUX\n"
    "  UART5 PC12 (AUX TX) / PD2 (ESC telemetry RX)\n"
    "  MOTOR1..4 PC6..PC9 = TIM8 CH1..CH4 (DShot / bidir DShot)\n"
    "  LED strip PA8 (TIM1 CH1)   Buzzer PC5   LEDs PC14/PC15\n"
    "  ADC: VBAT PC2 (x11 divider), CURRENT PC1, USB VBUS detect PA9\n")

# ============================================================================ POWER
s = B.sheet("Power", "power.kicad_sch")
s.note("POWER: VBAT (2S-6S) -> TPS54360B 5V/3A (USB + LDOs + RX + GPS) and 10V/2A (VTX / HD / camera)\n"
       "TPS54360B: fsw = 101756 / RT[k]^1.008 kHz -> RT 121k = ~800 kHz.  Vout = 0.8V x (1 + Rtop/Rbot)\n"
       "5V: 53.6k/10.2k = 5.00V, L 6.8uH.  10V: 115k/10k = 10.0V, L 10uH.  EN UVLO 470k/100k = start ~6.8V\n"
       "Compensation values are starting points - verify with TI WEBENCH / datasheet section 8.2")
s.TP("VBAT", P.PAD3x5, "BAT+")
s.TP("GND", P.PAD3x5, "BAT-")
s.D("D_TVS", "SMAJ28A", "GND", "VBAT", P.D_SMA, fields={"MPN": "SMAJ28A", "Description": "TVS 28V standoff, 400W"})
s.C("10uF 50V X7R", "VBAT", fp=P.C1206)
s.C("10uF 50V X7R", "VBAT", fp=P.C1206)
s.C("100nF 50V", "VBAT", fp=P.C0603)
# battery voltage sense (x11)
s.R("10k 1%", "VBAT", "VBAT_ADC")
s.R("1k 1%", "VBAT_ADC", "GND")
s.C("100nF", "VBAT_ADC")
# shared buck enable / UVLO
s.R("470k", "VBAT", "BUCK_EN")
s.R("100k", "BUCK_EN", "GND")

for v, rtop, rbot, L, cout, rc, cc, chf in (("5V", "53.6k 1%", "10.2k 1%", "6.8uH SRP5030T-6R8M", "22uF 16V X5R", "16.9k", "6.8nF", "47pF"),
                                            ("10V", "115k 1%", "10k 1%", "10uH SRP5030T-100M", "22uF 25V X5R", "24.9k", "4.7nF", "33pF")):
    net = "+" + v
    s.add("eConverterDCDC:TPS54360BDDAR", pins={"VIN": "VBAT", "EN": "BUCK_EN", "RT/CLK": f"RT_{v}", "COMP": f"COMP_{v}",
                                                "GND": "GND", "GNDPAD": "GND", "BOOT": f"BOOT_{v}", "SW": f"SW_{v}", "FB": f"FB_{v}"})
    s.C("2.2uF 50V", "VBAT", fp=P.C0805)
    s.C("100nF 50V", "VBAT", fp=P.C0603)
    s.R("121k 1%", f"RT_{v}", "GND")
    s.R(rc, f"COMP_{v}", f"COMP_{v}_RC")
    s.C(cc, f"COMP_{v}_RC")
    s.C(chf, f"COMP_{v}")
    s.C("100nF 50V", f"BOOT_{v}", f"SW_{v}", fp=P.C0603)
    s.D("D_Schottky", "PMEG6045ETP", "GND", f"SW_{v}", P.D_SOD128,
        fields={"MPN": "PMEG6045ETPX", "Description": "Schottky 60V 4.5A SOD-128 (catch diode)"})
    s.L(L, f"SW_{v}", net, fp=P.L_SRP5030, fields={"MPN": L.split()[1], "Manufacturer": "Bourns"})
    s.R(rtop, net, f"FB_{v}")
    s.R(rbot, f"FB_{v}", "GND")
    s.C(cout, net, fp=P.C0805 if v == "5V" else P.C1206)
    s.C(cout, net, fp=P.C0805 if v == "5V" else P.C1206)
    s.C("100nF", net)

# USB power path: VBUS -> +5V through a Schottky (FC configurable on USB only)
s.D("D_Schottky", "PMEG3020EH", "VBUS", "+5V", P.D_SOD123F, fields={"MPN": "PMEG3020EH,115", "Description": "Schottky 30V 2A"})
# 3.3V rails
for net in ("+3V3", "+3V3_GYRO"):
    s.add("eLinearReg:AP2112K-3.3TRG1", pins={"VIN": "+5V", "EN": "+5V", "GND": "GND", "VOUT": net})
    s.C("1uF 16V", "+5V")
    s.C("4.7uF 10V", net, fp=P.C0603)
    s.C("100nF", net)
s.R("1k", "+3V3", "LED_PWR_A")
s.LED("RED", "LED_PWR_A", "GND", fields={"MPN": "KT-0603R"})

# ============================================================================ MCU
s = B.sheet("MCU", "mcu.kicad_sch")
s.note("MCU: STM32F405RGT6 168 MHz, HSE 8 MHz.  BOOT0 button = DFU over USB-C.  SWD on test pads.")
mcu = {
    "VBAT": "+3V3", "VDD": "+3V3", "VDDA": "VDDA", "NRST": "NRST", "BOOT0": "BOOT0", "PH0": "OSC_IN", "PH1": "OSC_OUT",
    "VCAP_1": "VCAP1", "VCAP_2": "VCAP2", "VSSA": "GND", "VSS": "GND",
    "PA0": "UART4_TX", "PA1": "UART4_RX", "PA2": "UART2_TX", "PA3": "UART2_RX", "PA4": "GYRO_CS", "PA5": "SPI1_SCK",
    "PA6": "SPI1_MISO", "PA7": "SPI1_MOSI", "PA8": "LED_STRIP", "PA9": "USB_VBUS_DET", "PA10": "NC", "PA11": "USB_DM",
    "PA12": "USB_DP", "PA13": "SWDIO", "PA14": "SWCLK", "PA15": "FLASH_CS",
    "PB0": "GYRO_CLKIN", "PB1": "PWM5", "PB2": "BOOT1", "PB3": "SPI3_SCK", "PB4": "SPI3_MISO", "PB5": "SPI3_MOSI",
    "PB6": "UART1_TX", "PB7": "UART1_RX", "PB8": "I2C1_SCL", "PB9": "I2C1_SDA", "PB10": "UART3_TX", "PB11": "UART3_RX",
    "PB12": "OSD_CS", "PB13": "SPI2_SCK", "PB14": "SPI2_MISO", "PB15": "SPI2_MOSI",
    "PC0": "NC", "PC1": "CURR_ADC", "PC2": "VBAT_ADC", "PC3": "NC", "PC4": "GYRO_INT1", "PC5": "BUZZER",
    "PC6": "MOTOR1", "PC7": "MOTOR2", "PC8": "MOTOR3", "PC9": "MOTOR4", "PC10": "NC", "PC11": "NC", "PC12": "UART5_TX",
    "PC13": "NC", "PC14": "LED0", "PC15": "LED1", "PD2": "UART5_RX"}
s.add("eMCU:STM32F405RGT6", pins=mcu)
for _ in range(5):
    s.C("100nF", "+3V3")
s.C("4.7uF 10V", "+3V3", fp=P.C0603)
s.FB("600R@100MHz", "+3V3", "VDDA", fp=P.FB0402, fields={"MPN": "BLM15AG601SN1D"})
s.C("1uF", "VDDA")
s.C("100nF", "VDDA")
s.C("2.2uF", "VCAP1")
s.C("2.2uF", "VCAP2")
s.add("eCrystal:Crystal_GND24", "8MHz 12pF", P.XTAL3225, {"1": "OSC_IN", "3": "OSC_OUT", "2": "GND", "4": "GND"},
      fields={"MPN": "X322508MLB4SI", "Manufacturer": "Yangxing"})
s.C("18pF NP0", "OSC_IN")
s.C("18pF NP0", "OSC_OUT")
s.R("10k", "BOOT0", "GND")
s.add("eSwitch:SW_Push", "BOOT", pins={"1": "+3V3", "2": "BOOT0"}, fields={"MPN": "B3U-1000P", "Manufacturer": "Omron"})
s.R("10k", "BOOT1", "GND")
s.C("100nF", "NRST")
for n in ("SWDIO", "SWCLK", "NRST", "+3V3", "GND"):
    s.TP(n, P.TP10)
for led, col in (("LED0", "BLUE"), ("LED1", "GREEN")):
    s.R("1k", "+3V3", f"{led}_A")
    s.LED(col, f"{led}_A", led)
# USB-C
s.add("eConnector:USB_C_GCT_USB4105-GF-A", pins={"VBUS": "VBUS", "CC1": "USB_CC1", "CC2": "USB_CC2", "D+": "USB_DP",
                                                  "D-": "USB_DM", "SBU1": "NC", "SBU2": "NC", "GND": "GND", "SHIELD": "GND"})
s.R("5.1k", "USB_CC1", "GND")
s.R("5.1k", "USB_CC2", "GND")
s.add("eDiodes:USBLC6-2SC6", pins={"I/O1": "USB_DP", "I/O2": "USB_DM", "VBUS": "VBUS", "GND": "GND"})
s.C("1uF 16V", "VBUS")
s.R("10k", "VBUS", "USB_VBUS_DET")
s.R("20k", "USB_VBUS_DET", "GND")

# ============================================================================ SENSORS
s = B.sheet("Sensors", "sensors.kicad_sch")
s.note("SENSORS: ICM-42688-P on dedicated SPI1 + own LDO (+3V3_GYRO). INT2/CLKIN driven by PB0 (TIM3) for external 32 kHz clock.\n"
       "LPS22DF baro on I2C1 (addr 0x5C, SA0=0). W25Q128JV blackbox flash on SPI3.")
s.add("eSensor:ICM-42688-P", pins={"VDD": "+3V3_GYRO", "VDDIO": "+3V3_GYRO", "AP_CS": "GYRO_CS", "AP_SCL/AP_SCLK": "SPI1_SCK",
                                    "AP_SDA/AP_SDIO/AP_SDI": "SPI1_MOSI", "AP_SDO/AP_AD0": "SPI1_MISO", "GND": "GND",
                                    "INT1/INT": "GYRO_INT1", "INT2/FSYNC/CLKIN": "GYRO_CLKIN"})
s.C("100nF", "+3V3_GYRO")
s.C("1uF", "+3V3_GYRO")
s.C("100nF", "+3V3_GYRO")
s.R("10k", "GYRO_CS", "+3V3_GYRO")
s.add("eSensor:LPS22DF", pins={"VDD": "+3V3", "Vdd_IO": "+3V3", "SCL": "I2C1_SCL", "SDA": "I2C1_SDA", "SA0": "GND",
                                "~{CS}": "+3V3", "INT_DRDY": "NC", "GND_IO": "GND", "GND": "GND"})
s.C("100nF", "+3V3")
s.R("2.2k", "I2C1_SCL", "+3V3")
s.R("2.2k", "I2C1_SDA", "+3V3")
s.add("eMemory:W25Q128JVSIQ", pins={"VCC": "+3V3", "~{CS}": "FLASH_CS", "CLK": "SPI3_SCK", "DI(IO0)": "SPI3_MOSI",
                                     "DO(IO1)": "SPI3_MISO", "IO2": "FLASH_WP", "IO3": "FLASH_HOLD", "GND": "GND"})
s.C("100nF", "+3V3")
s.R("10k", "FLASH_CS", "+3V3")
s.R("10k", "FLASH_WP", "+3V3")
s.R("10k", "FLASH_HOLD", "+3V3")

# ============================================================================ OSD
s = B.sheet("OSD", "osd.kicad_sch")
s.note("OSD: AT7456E (MAX7456 compatible) on SPI2, supplied at 3.3V (spec 3.15-5.25V) so SPI levels match the MCU.\n"
       "Camera video: 75R termination + 100nF AC coupling into VIN. VOUT drives the VTX input (75R) directly; SAG tied to VOUT.\n"
       "R (DNP) = OSD bypass for debugging.")
s.add("eDisplay:AT7456E", pins={"DVDD": "+3V3_OSD", "AVDD": "+3V3_OSD", "PVDD": "+3V3_OSD", "DGND": "GND", "AGND": "GND",
                                "PGND": "GND", "EP": "GND", "~{CS}": "OSD_CS", "SCLK": "SPI2_SCK", "SDIN": "SPI2_MOSI",
                                "SDOUT": "SPI2_MISO", "~{RESET}": "OSD_RST", "CLKIN": "OSD_XI", "XFB": "OSD_XO",
                                "CLKOUT": "NC", "~{LOS}": "NC", "~{VSYNC}": "NC", "~{HSYNC}": "NC", "VIN": "OSD_VIN",
                                "VOUT": "VID_OUT", "SAG": "VID_OUT"})
s.FB("600R@100MHz", "+3V3", "+3V3_OSD", fp=P.FB0603, fields={"MPN": "BLM18AG601SN1D"})
s.C("10uF 10V", "+3V3_OSD", fp=P.C0603)
for _ in range(3):
    s.C("100nF", "+3V3_OSD")
s.R("10k", "OSD_RST", "+3V3_OSD")
s.C("100nF", "OSD_RST")
s.add("eCrystal:Crystal_GND24", "27MHz 12pF", P.XTAL3225, {"1": "OSD_XI", "3": "OSD_XO", "2": "GND", "4": "GND"},
      fields={"MPN": "X322527MOB4SI", "Manufacturer": "Yangxing"})
s.C("18pF NP0", "OSD_XI")
s.C("18pF NP0", "OSD_XO")
s.R("75R 1%", "CAM_VIDEO", "GND")
s.C("100nF", "CAM_VIDEO", "OSD_VIN")
s.R("0R", "CAM_VIDEO", "VID_OUT", dnp=True)

# ============================================================================ CONNECTORS
s = B.sheet("Connectors", "connectors.kicad_sch")
s.note("CONNECTORS (JST-SH 1.0 mm)\n"
       "J ESC 8p: VBAT GND CURR TLM M1 M2 M3 M4 (matches ESCV00)   J RX 4p: 5V GND TX RX (matches RXV00)\n"
       "J VTX 6p: 10V 5V GND VIDEO TX RX (matches VTXV00)   J CAM 3p: PWR GND VIDEO (PWR = 5V or 10V by solder jumper)\n"
       "J GPS 6p: 5V GND TX RX SCL SDA     J AUX 6p: 5V GND UART4_TX UART4_RX UART5_TX PWM5")
s.add("eConnector:JST_SH_SM08B-SRSS-TB", "ESC", pins={"1": "VBAT", "2": "GND", "3": "ESC_CURR", "4": "UART5_RX", "5": "MOTOR1",
                                                       "6": "MOTOR2", "7": "MOTOR3", "8": "MOTOR4", "MP": "NC"})
s.R("1k", "ESC_CURR", "CURR_ADC")
s.C("100nF", "CURR_ADC")
s.add("eConnector:JST_SH_SM04B-SRSS-TB", "RX", pins={"1": "+5V", "2": "GND", "3": "UART1_TX", "4": "UART1_RX", "MP": "NC"})
s.add("eConnector:JST_SH_SM06B-SRSS-TB", "VTX", pins={"1": "+10V", "2": "+5V", "3": "GND", "4": "VID_OUT", "5": "UART2_TX",
                                                       "6": "UART2_RX", "MP": "NC"})
s.add("eConnector:JST_SH_SM03B-SRSS-TB", "CAM", pins={"1": "CAM_PWR", "2": "GND", "3": "CAM_VIDEO", "MP": "NC"})
s.add("eJumpers:SolderJumper_3", "CAM 5V|10V", pins={"1": "+5V", "2": "CAM_PWR", "3": "+10V"})
s.C("10uF 25V", "CAM_PWR", fp=P.C0805)
s.add("eConnector:JST_SH_SM06B-SRSS-TB", "GPS", pins={"1": "+5V", "2": "GND", "3": "UART3_TX", "4": "UART3_RX", "5": "I2C1_SCL",
                                                       "6": "I2C1_SDA", "MP": "NC"})
s.add("eConnector:JST_SH_SM06B-SRSS-TB", "AUX", pins={"1": "+5V", "2": "GND", "3": "UART4_TX", "4": "UART4_RX", "5": "UART5_TX",
                                                       "6": "PWM5", "MP": "NC"})
# LED strip + buzzer pads
s.R("33R", "LED_STRIP", "LED_DOUT")
s.TP("LED_DOUT", P.TP20, "LED")
s.TP("+5V", P.TP20, "5V")
s.TP("GND", P.TP20, "GND")
s.add("eTransistor:2N7002", pins={"G": "BUZZER_G", "S": "GND", "D": "BUZZER_N"})
s.R("1k", "BUZZER", "BUZZER_G")
s.R("100k", "BUZZER_G", "GND")
s.D("D", "1N4148W", "BUZZER_N", "+5V", P.D_SOD123, fields={"MPN": "1N4148W"})
s.TP("+5V", P.TP20, "BZ+")
s.TP("BUZZER_N", P.TP20, "BZ-")
for i in range(4):
    s.add("eMechanical:MountingHole", "M3 (grommet)", P.MH_M4, {})



import project  # noqa: E402

NETCLASSES = (
    [project.netclass("Default", 0.15), project.netclass("Power", 0.6, clearance=0.2, via_d=0.6, via_drill=0.3),
     project.netclass("Rail", 0.4), project.netclass("USB", 0.2, dp_w=0.2, dp_gap=0.15), project.netclass("Video", 0.25)],
    [("VBAT", "Power"), ("/Power/SW_*", "Power"), ("+5V", "Power"), ("+10V", "Power"), ("+3V3*", "Rail"),
     ("USB_D?", "USB"), ("VID_OUT", "Video"), ("CAM_VIDEO", "Video"), ("/OSD/OSD_VIN", "Video")],
)
