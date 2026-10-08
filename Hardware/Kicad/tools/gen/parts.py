"""Part database for the drone electronics (FCV00 / ESCV00 / RXV00 / VTXV00).

Each part lives in one of the user's eXxx libraries. For every part we record:
  - where the pin table comes from ("kicad:<lib>:<sym>" = official KiCad library,
    "datasheet" = typed in from the vendor datasheet, see PIN_SOURCE notes)
  - footprint (copied from the official KiCad footprint library)
  - 3D model (STEP from the official KiCad 3D library)
"""
import re

from symlib import kicad_pins

PARTS = {}


class Part:
    def __init__(self, lib, name, ref, kind="ic", pins=None, left=None, right=None, fp=None,
                 fp_src=None, model=None, fields=None, verify=None, top=None, bottom=None, npins=None):
        self.lib, self.name, self.ref, self.kind = lib, name, ref, kind
        self.pins = pins or []
        self.left, self.right, self.top, self.bottom = left or [], right or [], top, bottom
        self.fp = fp            # footprint name inside eXxx.pretty (None for generic passives)
        self.fp_src = fp_src    # "<KiCadLib>:<footprint>" source
        self.model = model      # "<Lib>.3dshapes/<file>.step" in kicad-packages3D, or None
        self.fields = fields or {}
        self.verify = verify    # text describing what must be double-checked against the datasheet
        self.npins = npins
        if verify:
            self.fields["Verify"] = verify
        PARTS[name] = self

    @property
    def lib_id(self):
        return f"{self.lib}:{self.name}"

    @property
    def fp_id(self):
        return f"{self.lib}:{self.fp}" if self.fp else ""


def nums(pins, *patterns):
    """Pin numbers whose name matches any regex pattern (in the given order)."""
    out = []
    for pat in patterns:
        hit = [p[0] for p in pins if p[1] == pat] or [p[0] for p in pins if re.fullmatch(pat, p[1])]
        out += [h for h in hit if h not in out]
    return out


def port_sort(pins, port):
    ps = [p for p in pins if re.fullmatch(rf"P{port}\d+", p[1])]
    ps.sort(key=lambda p: int(p[1][2:]))
    return [p[0] for p in ps]


def fp_of(src):
    return src.split(":", 1)[1]


def model_of(src):
    lib, name = src.split(":", 1)
    return f"{lib.replace('.pretty', '')}.3dshapes/{name}.step"


def ic(lib, name, ref, pins, left, right, fp_src, fields, verify=None, model=True, fp_name=None):
    return Part(lib, name, ref, "ic", pins, left, right, fp=fp_name or fp_of(fp_src), fp_src=fp_src,
                model=model_of(fp_src) if model is True else model, fields=fields, verify=verify)


def F(mfr, mpn, desc, ds="", **kw):
    d = {"Manufacturer": mfr, "MPN": mpn, "Description": desc, "Datasheet": ds}
    d.update(kw)
    return d


# =============================================================================== MCUs
p = kicad_pins("MCU_ST_STM32F4", "STM32F405RGTx")
ic("eMCU", "STM32F405RGT6", "U", p,
   nums(p, "VBAT", "VDD", "VDDA") + [None] + nums(p, "NRST", "BOOT0", "PH0", "PH1") + [None]
   + nums(p, "VCAP_1", "VCAP_2") + [None] + nums(p, "VSSA", "VSS") + [None] + port_sort(p, "D"),
   port_sort(p, "A") + [None] + port_sort(p, "B") + [None] + port_sort(p, "C"),
   "Package_QFP:LQFP-64_10x10mm_P0.5mm",
   F("STMicroelectronics", "STM32F405RGT6", "ARM Cortex-M4F MCU 168MHz, 1MB Flash, 192KB RAM, LQFP-64",
     "https://www.st.com/resource/en/datasheet/stm32f405rg.pdf", LCSC="C15742"))

p = kicad_pins("MCU_ST_STM32F0", "STM32F051K8Ux")
ic("eMCU", "STM32F051K8U6", "U", p,
   nums(p, "VDD", "VDDA") + [None] + nums(p, "NRST", "BOOT0", "PF0", "PF1") + [None] + nums(p, "VSS"),
   port_sort(p, "A") + [None] + port_sort(p, "B"),
   "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.45x3.45mm",
   F("STMicroelectronics", "STM32F051K8U6", "ARM Cortex-M0 MCU 48MHz, 64KB Flash, UFQFPN-32 (AM32 ESC MCU). "
     "Pin-compatible alternative: Artery AT32F421K8U7 (AM32 HARDWARE_GROUP_AT_B)",
     "https://www.st.com/resource/en/datasheet/stm32f051k8.pdf"))

p = kicad_pins("MCU_ST_STM32F0", "STM32F031G6Ux")
ic("eMCU", "STM32F031G6U6", "U", p,
   nums(p, "VDD", "VDDA") + [None] + nums(p, "NRST", "BOOT0", "PF0", "PF1") + [None] + nums(p, "VSS"),
   port_sort(p, "A") + [None] + port_sort(p, "B"),
   "Package_DFN_QFN:QFN-28_4x4mm_P0.5mm",
   F("STMicroelectronics", "STM32F031G6U6", "ARM Cortex-M0 MCU 48MHz, 32KB Flash, UFQFPN-28 (VTX controller). "
     "Pin-compatible alternative: GigaDevice GD32F130G6U6 (used by OpenVTx Generic_GD32F130 target)",
     "https://www.st.com/resource/en/datasheet/stm32f031g6.pdf"))

p = kicad_pins("MCU_Espressif", "ESP32-C3")
ren = {"XTAL_32K_P": "XTAL_32K_P/GPIO0", "XTAL_32K_N": "XTAL_32K_N/GPIO1", "MTMS": "MTMS/GPIO4",
       "MTDI": "MTDI/GPIO5", "MTCK": "MTCK/GPIO6", "MTDO": "MTDO/GPIO7", "U0RXD": "U0RXD/GPIO20",
       "U0TXD": "U0TXD/GPIO21", "GPIO18": "GPIO18/USB_D-", "GPIO19": "GPIO19/USB_D+"}
p = [(n, ren.get(nm, nm), "power_in" if (nm in ("VDD3P3", "VDDA") and t == "passive") else t) for n, nm, t in p]
ic("eMCU", "ESP32-C3FH4", "U", p,
   nums(p, "VDD3P3", "VDD3P3_RTC", "VDD3P3_CPU", "VDDA", "VDD_SPI") + [None] + nums(p, "CHIP_EN", "XTAL_P", "XTAL_N", "LNA_IN")
   + [None] + nums(p, "GND"),
   nums(p, "XTAL_32K_P/GPIO0", "XTAL_32K_N/GPIO1", "GPIO2", "GPIO3", "MTMS/GPIO4", "MTDI/GPIO5", "MTCK/GPIO6",
        "MTDO/GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO18/USB_D-", "GPIO19/USB_D+", "U0RXD/GPIO20", "U0TXD/GPIO21")
   + [None] + nums(p, "SPIHD", "SPIWP", "SPICS0", "SPICLK", "SPID", "SPIQ"),
   "Package_DFN_QFN:QFN-32-1EP_5x5mm_P0.5mm_EP3.7x3.7mm",
   F("Espressif", "ESP32-C3FH4", "RISC-V WiFi/BLE SoC with 4MB in-package flash, QFN-32 5x5 (ELRS receiver MCU)",
     "https://www.espressif.com/sites/default/files/documentation/esp32-c3_datasheet_en.pdf"))

# =============================================================================== sensors / memory
p = kicad_pins("Sensor_Motion", "IIM-42652")
p = [(n, nm, "power_in" if n == "7" else t) for n, nm, t in p]
p = [(n, "AP_SDO/AP_AD0", "output") if n == "1" else (n, nm, t) for n, nm, t in p]
ic("eSensor", "ICM-42688-P", "U", p,
   nums(p, "VDD", "VDDIO") + [None] + nums(p, "AP_CS", "AP_SCL/AP_SCLK", "AP_SDA/AP_SDIO/AP_SDI", "AP_SDO/AP_AD0")
   + [None] + nums(p, "GND"),
   nums(p, "INT1/INT", "INT2/FSYNC/CLKIN") + [None] + nums(p, "RESV"),
   "Package_LGA:Bosch_LGA-14_3x2.5mm_P0.5mm",
   F("TDK InvenSense", "ICM-42688-P", "6-axis IMU (gyro + accel), SPI 24MHz, LGA-14 2.5x3mm",
     "https://invensense.tdk.com/wp-content/uploads/2020/04/ds-000347_icm-42688-p-datasheet.pdf"),
   verify="Pin table from KiCad IIM-42652 (same LGA-14 package/pinout as ICM-42688-P). Confirm pin 7/RESV handling vs DS-000347.")

p = kicad_pins("Sensor_Pressure", "LPS22DF")
p = [(n, nm, "power_in" if n == "3" else t) for n, nm, t in p]
ic("eSensor", "LPS22DF", "U", p,
   nums(p, "VDD", "Vdd_IO") + [None] + nums(p, "SCL", "SDA", "SA0", "~{CS}") + [None] + nums(p, "GND_IO", "GND"),
   nums(p, "INT_DRDY"),
   "Package_LGA:ST_HLGA-10_2x2mm_P0.5mm_LayoutBorder3x2y",
   F("STMicroelectronics", "LPS22DFTR", "Barometric pressure sensor 260-1260hPa, I2C/SPI, HLGA-10 2x2mm",
     "https://www.st.com/resource/en/datasheet/lps22df.pdf"))

p = kicad_pins("Memory_Flash", "W25Q128JVS")
ic("eMemory", "W25Q128JVSIQ", "U", p, nums(p, "VCC", "~{CS}", "CLK", "DI\\(IO0\\)", "GND"),
   nums(p, "DO\\(IO1\\)", "IO2", "IO3"), fp_src=
   "Package_SO:SOIC-8_5.23x5.23mm_P1.27mm",
   model="Package_SO.3dshapes/SOIC-8_5.3x5.3mm_P1.27mm.step", fields=F("Winbond", "W25Q128JVSIQ", "128Mbit SPI NOR flash (blackbox logging), SOIC-8 208mil",
     "https://www.winbond.com/hq/product/code-storage-flash-memory/serial-nor-flash/?__locale=en&partNo=W25Q128JV", LCSC="C97521"))

# =============================================================================== OSD (datasheet pin table)
p = [("1", "NC", "no_connect"), ("2", "NC", "no_connect"), ("3", "DVDD", "power_in"), ("4", "DGND", "power_in"),
     ("5", "CLKIN", "input"), ("6", "XFB", "passive"), ("7", "CLKOUT", "output"), ("8", "~{CS}", "input"),
     ("9", "SDIN", "input"), ("10", "SCLK", "input"), ("11", "SDOUT", "tri_state"), ("12", "~{LOS}", "open_collector"),
     ("13", "NC", "no_connect"), ("14", "NC", "no_connect"), ("15", "NC", "no_connect"), ("16", "NC", "no_connect"),
     ("17", "~{VSYNC}", "open_collector"), ("18", "~{HSYNC}", "open_collector"), ("19", "~{RESET}", "input"),
     ("20", "AGND", "power_in"), ("21", "AVDD", "power_in"), ("22", "VIN", "input"), ("23", "PGND", "power_in"),
     ("24", "PVDD", "power_in"), ("25", "SAG", "input"), ("26", "VOUT", "output"), ("27", "NC", "no_connect"),
     ("28", "NC", "no_connect"), ("29", "EP", "power_in")]
ic("eDisplay", "AT7456E", "U", p,
   ["3", "21", "24", None, "8", "10", "9", "11", "19", None, "5", "6", "7", None, "4", "20", "23", "29"],
   ["22", "26", "25", None, "12", "17", "18", None, "1", "2", "13", "14", "15", "16", "27", "28"],
   "Package_SO:HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP2.85x5.4mm",
   model="Package_SO.3dshapes/HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.4x9.5mm.step", fields=F("Shenzhen Zhongkewei (ZKW)", "AT7456E", "Analog video OSD generator, SPI, MAX7456 pin-compatible, HTSSOP-28",
     "https://www.lcsc.com/product-detail/C82351.html", LCSC="C82351"),
   verify="Pin table = MAX7456 pinout (AT7456E is pin-compatible). Exposed-pad size of the footprint must be checked "
          "against the AT7456E package drawing.")

# =============================================================================== power ICs
p = kicad_pins("Regulator_Switching", "TPS54360DDA")
ic("eConverterDCDC", "TPS54360BDDAR", "U", p, nums(p, "VIN", "EN", "RT/CLK", "COMP", "GND", "GNDPAD"),
   nums(p, "BOOT", "SW", "FB"), "Package_SO:TI_SO-PowerPAD-8_ThermalVias",
   F("Texas Instruments", "TPS54360BDDAR", "60V 3.5A non-synchronous buck converter, HSOP-8 PowerPAD",
     "https://www.ti.com/lit/ds/symlink/tps54360b.pdf"), model="Package_SO.3dshapes/TI_SO-PowerPAD-8.step")

p = kicad_pins("Regulator_Switching", "LMR16006YQ")
ic("eConverterDCDC", "LMR16006YDDCR", "U", p, nums(p, "VIN", "~{SHDN}", "GND"), nums(p, "CB", "SW", "FB"),
   "Package_TO_SOT_SMD:SOT-23-6",
   F("Texas Instruments", "LMR16006YDDCR", "40V 0.6A 2.1MHz buck converter, SOT-23-6 (ESC gate-driver rail)",
     "https://www.ti.com/lit/ds/symlink/lmr16006.pdf"))

p = kicad_pins("Regulator_Linear", "AP2112K-3.3")
ic("eLinearReg", "AP2112K-3.3TRG1", "U", p, nums(p, "VIN", "EN", "GND"), nums(p, "VOUT", "NC"),
   "Package_TO_SOT_SMD:SOT-23-5",
   F("Diodes Inc", "AP2112K-3.3TRG1", "3.3V 600mA LDO, SOT-23-5", "https://www.diodes.com/assets/Datasheets/AP2112.pdf",
     LCSC="C51118"))

p = kicad_pins("Regulator_Linear", "MCP1703Ax-330xxMB")
ic("eLinearReg", "MCP1703AT-3302E_MB", "U", p, nums(p, "VI", "GND"), nums(p, "VO"), "Package_TO_SOT_SMD:SOT-89-3",
   F("Microchip", "MCP1703AT-3302E/MB", "3.3V 250mA LDO, Vin up to 16V, SOT-89", "https://ww1.microchip.com/downloads/en/DeviceDoc/20005122B.pdf",
     ))

# =============================================================================== analog / drivers
p = kicad_pins("Amplifier_Current", "INA181")
ic("eAmplifier", "INA181A3IDBVR", "U", p, nums(p, "V\\+", "\\+", "-", "REF", "GND"), nums(p, "~"),
   "Package_TO_SOT_SMD:SOT-23-6",
   F("Texas Instruments", "INA181A3IDBVR", "Current sense amplifier, gain 100V/V, SOT-23-6",
     "https://www.ti.com/lit/ds/symlink/ina181.pdf"))

p = [("1", "INLA", "input"), ("2", "INLB", "input"), ("3", "INLC", "input"), ("4", "GVDD", "power_in"),
     ("5", "MODE", "input"), ("6", "GND", "power_in"), ("7", "NC", "no_connect"), ("8", "NC", "no_connect"),
     ("9", "GLC", "output"), ("10", "GLB", "output"), ("11", "GLA", "output"), ("12", "SHC", "passive"),
     ("13", "GHC", "output"), ("14", "BSTC", "passive"), ("15", "SHB", "passive"), ("16", "GHB", "output"),
     ("17", "BSTB", "passive"), ("18", "SHA", "passive"), ("19", "GHA", "output"), ("20", "BSTA", "passive"),
     ("21", "DT", "input"), ("22", "INHA", "input"), ("23", "INHB", "input"), ("24", "INHC", "input"),
     ("25", "EP", "power_in")]
ic("eInterface", "DRV8300DRGER", "U", p,
   ["4", None, "22", "1", "23", "2", "24", "3", None, "5", "21", None, "6", "25"],
   ["20", "19", "18", "11", None, "17", "16", "15", "10", None, "14", "13", "12", "9", None, "7", "8"],
   "Package_DFN_QFN:VQFN-24-1EP_4x4mm_P0.5mm_EP2.45x2.45mm",
   F("Texas Instruments", "DRV8300DRGER", "100V 3-phase BLDC gate driver, integrated bootstrap diodes, VQFN-24 4x4",
     "https://www.ti.com/lit/ds/symlink/drv8300.pdf"),
   verify="Pin table typed from TI DRV8300 datasheet (RGE pin table). Check exposed-pad size vs TI RGE0024 drawing.")

# =============================================================================== RF ICs (datasheet pin tables)
p = [("1", "VR_PA", "power_out"), ("2", "VDD_IN", "power_in"), ("3", "~{NRESET}", "input"), ("4", "XTA", "passive"),
     ("5", "GND", "power_in"), ("6", "XTB", "passive"), ("7", "BUSY", "output"), ("8", "DIO1", "bidirectional"),
     ("9", "DIO2", "bidirectional"), ("10", "DIO3", "bidirectional"), ("11", "VBAT_IO", "power_in"),
     ("12", "DCC_FB", "power_out"), ("13", "GND", "power_in"), ("14", "DCC_SW", "passive"), ("15", "VBAT", "power_in"),
     ("16", "MISO", "output"), ("17", "MOSI", "input"), ("18", "SCK", "input"), ("19", "~{NSS}", "input"),
     ("20", "GND", "power_in"), ("21", "GND", "power_in"), ("22", "RFIO", "passive"), ("23", "GND", "power_in"),
     ("24", "GND", "power_in"), ("25", "EP", "power_in")]
ic("eRFModule", "SX1281IMLTRT", "U", p,
   ["15", "11", "2", None, "14", "12", "1", None, "4", "6", None, "5", "13", "20", "21", "23", "24", "25"],
   ["22", None, "19", "18", "17", "16", None, "3", "7", "8", "9", "10"],
   "Package_DFN_QFN:QFN-24-1EP_4x4mm_P0.5mm_EP2.6x2.6mm",
   F("Semtech", "SX1281IMLTRT", "2.4GHz LoRa/FLRC/GFSK transceiver (ExpressLRS 2.4GHz), QFN-24 4x4",
     "https://www.semtech.com/products/wireless-rf/lora-connect/sx1281"),
   verify="Pin table typed from Semtech DS_SX1280-1 rev 3.x. RF matching values on the RX sheet are starting points.")

p = [("1", "SPI_SE", "input"), ("2", "NC", "no_connect"), ("3", "S", "input"), ("4", "BX", "input"),
     ("5", "SPIDATA/CS0", "input"), ("6", "SPILE/CS1", "input"), ("7", "SPICLK/CS2", "input"),
     ("8", "VDD33_DIG", "power_in"), ("9", "V2D5_PLL", "power_in"), ("10", "VT_MOD", "input"), ("11", "RF_VT2", "input"),
     ("12", "NC", "no_connect"), ("13", "AVDD_6", "power_in"), ("14", "AVT1", "input"), ("15", "ACP1", "output"),
     ("16", "AOUT1", "output"), ("17", "AVDD_6.5", "power_in"), ("18", "NC", "no_connect"), ("19", "AOUT2", "output"),
     ("20", "ACP2", "output"), ("21", "AVT2", "input"), ("22", "VDD3V3", "power_in"), ("23", "REG1D8_1", "power_out"),
     ("24", "XTAL1", "passive"), ("25", "XTAL2", "passive"), ("26", "REG1D8", "power_out"), ("27", "CP", "output"),
     ("28", "GND", "power_in"), ("29", "VT", "input"), ("30", "VDDVT", "power_in"), ("31", "BUFVDD", "power_in"),
     ("32", "PAVDD", "power_in"), ("33", "RFGND", "power_in"), ("34", "PAOUT2", "output"), ("35", "PAOUT1", "output"),
     ("36", "NC", "no_connect"), ("37", "NC", "no_connect"), ("38", "GND", "power_in"), ("39", "VCOVDD", "power_in"),
     ("40", "LDD2V5", "power_in"), ("41", "EP", "power_in")]
ic("eRFModule", "RTC6705", "U", p,
   ["8", "9", "13", "17", "22", "30", "31", "32", "39", "40", None, "1", "5", "6", "7", "3", "4", None,
    "10", "11", None, "24", "25", None, "28", "33", "38", "41"],
   ["35", "34", None, "27", "29", None, "15", "14", "16", None, "20", "21", "19", None, "23", "26", None,
    "2", "12", "18", "36", "37"],
   "Package_DFN_QFN:QFN-40-1EP_6x6mm_P0.5mm_EP4.6x4.6mm",
   F("RichWave", "RTC6705", "5.8GHz FM video transmitter, SPI tuned, QFN-40 6x6",
     "https://github.com/OpenVTx/OpenVTx/blob/master/docs/RTC6705-RichWave.pdf"),
   verify="Pin table from RichWave RTC6705 datasheet V0.2 (datasheet/RTC6705-RichWave.pdf). The datasheet gives no "
          "exposed-pad size: check EP4.6x4.6 against the actual part. Loop-filter values must be tuned.")

p = [("1", "NC", "no_connect"), ("2", "GND", "power_in"), ("3", "RFIN", "input"), ("4", "GND", "power_in"),
     ("5", "PA_EN", "input"), ("6", "NC", "no_connect"), ("7", "NC", "no_connect"), ("8", "NC", "no_connect"),
     ("9", "NC", "no_connect"), ("10", "PDET", "output"), ("11", "GND", "power_in"), ("12", "GND", "power_in"),
     ("13", "RFOUT", "output"), ("14", "GND", "power_in"), ("15", "GND", "power_in"), ("16", "GND", "power_in"),
     ("17", "GND", "power_in"), ("18", "VCC3", "power_in"), ("19", "VCC2", "power_in"), ("20", "VCC1", "power_in"),
     ("21", "EP", "power_in")]
ic("eAmplifier", "RFPA5542", "U", p,
   ["20", "19", "18", None, "3", "5", None, "2", "4", "11", "12", "14", "15", "16", "17", "21"],
   ["13", "10", None, "1", "6", "7", "8", "9"],
   "Package_DFN_QFN:QFN-20-1EP_4x4mm_P0.5mm_EP2.5x2.5mm",
   F("Qorvo", "RFPA5542TR13", "4.9-5.925GHz 3-stage power amplifier, 33dB gain, P1dB 33dBm, QFN-20 4x4",
     "https://github.com/OpenVTx/OpenVTx/blob/master/docs/RFPA5542-Qorvo.pdf"))

# =============================================================================== discretes
Part("eTransistor", "BSZ018N04LS6", "Q", "NMOS_PWR", fp="PQFN-8_3.3x3.3mm_P0.65mm_PowerFET",
     fp_src="Package_SON:VSON-8_3.3x3.3mm_P0.65mm_NexFET", model="Package_SON.3dshapes/VSON-8_3.3x3.3mm_P0.65mm_NexFET.step",
     fields=F("Infineon", "BSZ018N04LS6ATMA1", "N-MOSFET 40V 1.8mOhm OptiMOS 6, PG-TSDSON-8 FL 3.3x3.3",
              "https://www.infineon.com/cms/en/product/power/mosfet/n-channel/bsz018n04ls6/"),
     verify="Land pattern copied from TI NexFET SON3.3 (same S-S-S-G / D-tab pinout). Compare with Infineon PG-TSDSON-8 FL "
            "recommended footprint before fab.")
Part("eTransistor", "2N7002", "Q", "NMOS", fp="SOT-23", fp_src="Package_TO_SOT_SMD:SOT-23",
     model="Package_TO_SOT_SMD.3dshapes/SOT-23.step",
     fields=F("Nexperia", "2N7002,215", "N-MOSFET 60V 0.3A SOT-23", "https://assets.nexperia.com/documents/data-sheet/2N7002.pdf",
              LCSC="C8545"))
Part("eTransistor", "MMBT3904", "Q", "NPN", fp="SOT-23", fp_src="Package_TO_SOT_SMD:SOT-23",
     model="Package_TO_SOT_SMD.3dshapes/SOT-23.step",
     fields=F("onsemi", "MMBT3904LT1G", "NPN 40V 200mA SOT-23", "https://www.onsemi.com/pdf/datasheet/mmbt3904lt1-d.pdf",
              LCSC="C20526"))

p = kicad_pins("Power_Protection", "USBLC6-2SC6")
ic("eDiodes", "USBLC6-2SC6", "D", p, nums(p, "I/O1", "VBUS"), nums(p, "I/O2", "GND"), "Package_TO_SOT_SMD:SOT-23-6",
   F("STMicroelectronics", "USBLC6-2SC6", "USB ESD protection, 2 lines + VBUS, SOT-23-6",
     "https://www.st.com/resource/en/datasheet/usblc6-2.pdf", LCSC="C7519"))

# =============================================================================== generic passives
for nm, kind, lib, ref in [("R", "R", "eResistor", "R"), ("C", "C", "eCapacitor", "C"), ("CP", "CP", "eCapacitor", "C"),
                           ("L", "L", "eCoil", "L"), ("FB", "FB", "eChoke", "FB"), ("D_Schottky", "DS", "eDiodes", "D"),
                           ("D", "D", "eDiodes", "D"), ("D_TVS", "DZ", "eDiodes", "D"), ("LED", "LED", "eLED", "D"),
                           ("Crystal", "XTAL", "eCrystal", "Y"), ("Crystal_GND24", "XTAL4", "eCrystal", "Y"),
                           ("SW_Push", "SW", "eSwitch", "SW"), ("TestPoint", "TP", "eTestPoint", "TP"),
                           ("SolderJumper_3", "JUMPER3", "eJumpers", "JP"), ("Conn_Coaxial", "COAX", "eConnector", "J"),
                           ("Antenna_Chip", "ANT", "eAntenna", "AE"), ("MountingHole", "HOLE", "eMechanical", "H")]:
    Part(lib, nm, ref, kind)

# footprints used by generic symbols: name -> (lib, kicad source, 3d model)
GENERIC_FP = {}


def gfp(lib, src, model=True):
    name = fp_of(src)
    GENERIC_FP[(lib, name)] = (lib, src, model_of(src) if model is True else model)
    return f"{lib}:{name}"


R0402 = gfp("eResistor", "Resistor_SMD:R_0402_1005Metric")
R0603 = gfp("eResistor", "Resistor_SMD:R_0603_1608Metric")
R2512 = gfp("eResistor", "Resistor_SMD:R_2512_6332Metric")
C0402 = gfp("eCapacitor", "Capacitor_SMD:C_0402_1005Metric")
C0603 = gfp("eCapacitor", "Capacitor_SMD:C_0603_1608Metric")
C0805 = gfp("eCapacitor", "Capacitor_SMD:C_0805_2012Metric")
C1206 = gfp("eCapacitor", "Capacitor_SMD:C_1206_3216Metric")
L0402 = gfp("eCoil", "Inductor_SMD:L_0402_1005Metric")
L0603 = gfp("eCoil", "Inductor_SMD:L_0603_1608Metric")
L0805 = gfp("eCoil", "Inductor_SMD:L_0805_2012Metric")
L_SRP5030 = gfp("eCoil", "Inductor_SMD:L_Bourns_SRP5030T")
L_SWPA3012 = gfp("eCoil", "Inductor_SMD:L_Sunlord_SWPA3012S")
FB0402 = gfp("eChoke", "Inductor_SMD:L_0402_1005Metric", model="Inductor_SMD.3dshapes/L_0402_1005Metric.step")
FB0603 = gfp("eChoke", "Inductor_SMD:L_0603_1608Metric", model="Inductor_SMD.3dshapes/L_0603_1608Metric.step")
D_SOD123 = gfp("eDiodes", "Diode_SMD:D_SOD-123")
D_SOD123F = gfp("eDiodes", "Diode_SMD:D_SOD-123F")
D_SOD128 = gfp("eDiodes", "Diode_SMD:D_SOD-128")
D_SMA = gfp("eDiodes", "Diode_SMD:D_SMA")
LED0603 = gfp("eLED", "LED_SMD:LED_0603_1608Metric")
XTAL3225 = gfp("eCrystal", "Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm")
XTAL2016 = gfp("eCrystal", "Crystal:Crystal_SMD_2016-4Pin_2.0x1.6mm")
SW_B3U = gfp("eSwitch", "Button_Switch_SMD:SW_SPST_B3U-1000P")
TP10 = gfp("eTestPoint", "TestPoint:TestPoint_Pad_D1.0mm", model=None)
TP15 = gfp("eTestPoint", "TestPoint:TestPoint_Pad_D1.5mm", model=None)
TP20 = gfp("eTestPoint", "TestPoint:TestPoint_Pad_2.0x2.0mm", model=None)
JP3 = gfp("eJumpers", "Jumper:SolderJumper-3_P1.3mm_Open_RoundedPad1.0x1.5mm", model=None)
UFL = gfp("eConnector", "Connector_Coaxial:U.FL_Hirose_U.FL-R-SMT-1_Vertical")
ANT2450 = gfp("eAntenna", "RF_Antenna:Johanson_2450AT18x100", model=None)
MH_M3 = gfp("eMechanical", "MountingHole:MountingHole_3.2mm_M3", model=None)
MH_M4 = gfp("eMechanical", "MountingHole:MountingHole_4mm", model=None)
MH_M2 = gfp("eMechanical", "MountingHole:MountingHole_2.2mm_M2", model=None)

# custom solder pads (generated, see libbuild.py)
CUSTOM_FP = {
    "SolderPad_3x5mm": ("eConnector", 3.0, 5.0),
    "SolderPad_5x8mm": ("eConnector", 5.0, 8.0),
    "SolderPad_4x6mm": ("eConnector", 4.0, 6.0),
}
PAD3x5 = "eConnector:SolderPad_3x5mm"
PAD5x8 = "eConnector:SolderPad_5x8mm"
PAD4x6 = "eConnector:SolderPad_4x6mm"

# =============================================================================== connectors
for n in (3, 4, 6, 8):
    src = f"Connector_JST:JST_SH_SM{n:02d}B-SRSS-TB_1x{n:02d}-1MP_P1.00mm_Horizontal"
    Part("eConnector", f"JST_SH_SM{n:02d}B-SRSS-TB", "J", "conn", fp=fp_of(src), fp_src=src, model=model_of(src), npins=n,
         fields=F("JST", f"SM{n:02d}B-SRSS-TB(LF)(SN)", f"JST-SH 1.0mm {n}-pin side-entry SMD header",
                  "https://www.jst-mfg.com/product/pdf/eng/eSH.pdf"))

p = [("A1", "GND", "passive"), ("A4", "VBUS", "passive"), ("A5", "CC1", "bidirectional"), ("A6", "D+", "bidirectional"),
     ("A7", "D-", "bidirectional"), ("A8", "SBU1", "bidirectional"), ("A9", "VBUS", "passive"), ("A12", "GND", "passive"),
     ("B1", "GND", "passive"), ("B4", "VBUS", "passive"), ("B5", "CC2", "bidirectional"), ("B6", "D+", "bidirectional"),
     ("B7", "D-", "bidirectional"), ("B8", "SBU2", "bidirectional"), ("B9", "VBUS", "passive"), ("B12", "GND", "passive"),
     ("S1", "SHIELD", "passive")]
ic("eConnector", "USB_C_GCT_USB4105-GF-A", "J", p,
   ["A4", "A9", "B4", "B9", None, "A5", "B5", None, "A1", "A12", "B1", "B12", "S1"],
   ["A6", "B6", "A7", "B7", None, "A8", "B8"],
   "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
   F("GCT", "USB4105-GF-A", "USB 2.0 Type-C receptacle, 16-pin, top mount (alt: HRO TYPE-C-31-M-12 with footprint swap)",
     "https://gct.co/files/drawings/usb4105.pdf"))

Part("eConnector", "Conn_Coaxial", "J", "COAX")  # footprint chosen per instance (U.FL)

# small-part default footprints for generic symbols with a fixed package
PartDefaults = {
    "Conn_Coaxial": UFL,
    "Antenna_Chip": ANT2450,
    "SW_Push": SW_B3U,
    "SolderJumper_3": JP3,
}

POWER_NETS_GND = {"GND"}


def power_kind(net):
    return "gnd" if net in POWER_NETS_GND else "vcc"
