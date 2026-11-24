# esp32-DAC-characterization

A test bench for measuring the quality of the **ESP32's 8-bit DAC** using a **Rigol DS1102** oscilloscope controlled from Python. The ESP32 generates a sine wave on its DAC, the oscilloscope captures it over USB, and the program computes **THD, SNR, SINAD and ENOB** through spectral analysis, all from a graphical interface with light/dark themes and Spanish/English support.

## Features

- **Graphical interface** (PyQt5 + pyqtgraph) with two tabs:
  - **Live**: waveform and basic measurements, with RUN / STOP and single capture.
  - **DAC analysis**: spectrum, THD, SNR, SINAD, ENOB and detected harmonics.
- **Works with two Rigol families** (auto-detected via `*IDN?`): DS1102E / DS1102D (DS1000E/D series) and DS1102Z-E (DS1000Z series).
- **NORMAL and RAW modes**: NORMAL reads what is shown on screen (fast, low precision); RAW reads the whole deep memory (12 k to 1.2 M points), giving a higher sample rate and finer FFT resolution.
- **Oscilloscope control**: 20 MHz bandwidth filter, acquisition type (normal, high resolution, or whatever is set on the scope) and automatic vertical scale fitting to make use of the full 8 bits of the ADC.
- **Spectrum averaging** over several captures on the PC to lower the noise floor.
- **Configurable measurement bandwidth** (by default, the Nyquist band of the DAC).
- **Export** of the program window as a PNG image.
- **Language (ES/EN) and theme (light/dark)**, remembered between sessions.

## Project structure

```
esp32-DAC-characterization/
├── esp32_dac_seno/
│   └── esp32_dac_seno.ino      # ESP32 sketch: sine wave on DAC1 (GPIO25)
├── osciloscopio_gui.py         # Graphical interface (entry point)
├── captura_rigol.py            # Oscilloscope capture through PyVISA
├── analisis_dac.py             # Spectral analysis: THD, SNR, SINAD, ENOB
├── idioma.py                   # Spanish and English texts
├── requirements.txt
├── LICENSE
└── README.md
```

## Hardware required

| Item | Details |
|---|---|
| ESP32 | Classic ESP32 with an 8-bit DAC (ESP32-S3 / C3 variants do not have a DAC). |
| Oscilloscope | Rigol DS1102E, DS1102D or DS1102Z-E, connected over USB. |
| Probe / cable | One oscilloscope probe. |

### Wiring

```
ESP32 GPIO25 (DAC1) ──────► Oscilloscope CH1 (probe tip)
ESP32 GND           ──────► Probe ground
```

## Installation

1. **Clone the repository** and enter the folder:

   ```bash
   git clone https://github.com/baguenaaaron-cloud/esp32-DAC-characterization.git
   cd esp32-DAC-characterization
   ```

2. **Install the Python dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

   This installs `numpy`, `scipy`, `matplotlib`, `pyqtgraph`, `PyQt5`, `pyvisa`, `pyvisa-py` and `pyusb`.

3. **Upload the sketch to the ESP32** from the Arduino IDE:
   - Open `esp32_dac_seno/esp32_dac_seno.ino`.
   - Select the board **ESP32 Dev Module**.
   - Compile and upload.

> **USB note:** `pyvisa-py` uses `pyusb` as its backend. On Windows you may need a libusb-compatible driver (for example via [Zadig](https://zadig.akeo.ie/)) or NI-VISA installed. On Linux you may need a `udev` rule to access the device without administrator privileges.

## Usage

All `.py` files must be in the same folder.

```bash
python osciloscopio_gui.py
```

1. Click **Connect** (the first USB instrument found is used).
2. Choose the **channel** and, for better accuracy, enable **RAW (deep memory)** and pick the memory depth (12 k, 120 k or 1.2 M).
3. Click **Auto-fit vertical scale** so the signal fills 50–90 % of the screen.
4. Start **RUN** (continuous capture) or **Single capture**.
5. The **DAC analysis** tab shows the spectrum and the measurements.

Plot controls: **mouse wheel** = zoom, **drag** = pan, **right button + drag** = per-axis zoom, **right click** = menu.

## The ESP32 sketch

It writes a table of **64 samples per period** to DAC1, one sample every **15 µs**, giving about **1.04 kHz**. The exact frequency does not matter, since the analysis detects it automatically. The default measurement band is **0 – 33.3 kHz**, i.e. half the DAC update rate.

## How it is computed

The analysis (`analisis_dac.py`) works as follows:

1. **Blackman-Harris window** and power FFT. The window-weighted mean is subtracted so a non-integer number of periods does not leave a DC residue.
2. **Fundamental**: maximum spectral peak, with parabolic interpolation on the logarithm to refine the frequency between bins.
3. **Harmonics**: up to the 9th. Those above Nyquist are folded back (aliasing). They only count if they stand at least 10 dB above the noise floor.
4. **Noise floor**: median of the remaining spectrum, robust against peaks.
5. **Metrics**:
   - `THD = 10·log10(P_harmonics / P_fundamental)` (dBc)
   - `SNR = 10·log10(P_fundamental / P_noise)`
   - `SINAD = 10·log10(P_fundamental / (P_noise + P_harmonics))`
   - `ENOB = (SINAD − 1.76) / 6.02`

The analysis needs at least **10 periods** of the signal to be reliable (the program warns you if there are fewer).

## Tips for better measurements

- Use **RAW** with 120 k or 1.2 M points: more samples and better frequency resolution.
- Use **Auto-fit vertical scale**: the oscilloscope ADC is 8-bit and measures much better when the signal fills the screen.
- Enable **High resolution** if you see wideband noise aliasing: it averages neighboring points before storing them.
- Enable the **20 MHz filter** to reduce high-frequency noise.
- Increase the number of **spectrum averages** to stabilize the noise floor.

## Troubleshooting

| Problem | Possible cause |
|---|---|
| No USB instrument found | Cable unplugged, missing USB driver, or insufficient permissions (see the USB note). |
| Very few points in normal mode | Check that the oscilloscope is in RUN and has a valid trigger. |
| Timeout on RAW reads | Large memories take a while; the timeout is set to 30 s. |
| Warning about too few periods | Reduce the oscilloscope time base to capture at least 10 periods. |

## License

This project is licensed under the [MIT License](LICENSE).
