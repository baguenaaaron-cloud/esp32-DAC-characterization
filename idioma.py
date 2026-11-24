IDIOMAS = ("es", "en")
_actual = "es"


def set_idioma(codigo):
    global _actual
    if codigo in IDIOMAS:
        _actual = codigo


def get_idioma():
    return _actual


def tr(clave, **kw):
    """Texto de `clave` en el idioma actual; rellena los {campos} con kw."""
    par = TEXTOS.get(clave)
    if par is None:
        return clave
    texto = par[IDIOMAS.index(_actual)]
    return texto.format(**kw) if kw else texto


TEXTOS = {
    # --- ventana y barra superior / window and top bar
    "titulo": ("Banco de pruebas - Rigol DS1102Z-E", "Test bench - Rigol DS1102Z-E"),
    "conectar": ("Conectar", "Connect"),
    "desconectar": ("Desconectar", "Disconnect"),
    "lb_canal": ("Canal:", "Channel:"),
    "run": ("RUN", "RUN"),
    "stop": ("STOP", "STOP"),
    "captura_unica": ("Captura única", "Single capture"),
    "lb_idioma": ("Idioma:", "Language:"),
    "lb_tema": ("Tema:", "Theme:"),
    "tema_claro": ("Claro", "Light"),
    "tema_oscuro": ("Oscuro", "Dark"),
    # --- precisión / accuracy controls
    "chk_raw": ("RAW (memoria profunda)", "RAW (deep memory)"),
    "tip_raw": ("Lee toda la memoria del osciloscopio: más puntos y más frecuencia de muestreo. "
                "Más lento, mucho más preciso.",
                "Reads the oscilloscope's whole memory: more points and a higher sample rate. "
                "Slower, much more accurate."),
    "mem_12k": ("12 k", "12 k"),
    "mem_120k": ("120 k", "120 k"),
    "mem_1_2M": ("1,2 M", "1.2 M"),
    "chk_bwl": ("Filtro 20 MHz", "20 MHz filter"),
    "tip_bwl": ("Limita el ancho de banda del canal para reducir ruido.",
                "Limits the channel bandwidth to reduce noise."),
    "adq_personalizada": ("Adquisición personalizada", "Custom acquisition"),
    "adq_normal": ("Adquisición normal", "Normal acquisition"),
    "adq_hres": ("Alta resolución", "High resolution"),
    "tip_adq": ("Personalizada: se respeta lo que tengas puesto en el menú Acquire del "
                "osciloscopio (Normal, Promedio, Alta resolución...).\n"
                "Normal / Alta resolución: la aplicación fuerza ese modo en cada captura.",
                "Custom: whatever is set in the oscilloscope's Acquire menu is kept (Normal, "
                "Average, High Resolution...).\n"
                "Normal / High resolution: the application forces that mode on every capture."),
    "lb_prom": ("Promedios del espectro (PC):", "Spectrum averages (PC):"),
    "tip_prom": ("Se hace en el ordenador: promedia el espectro de varias capturas (el suelo de "
                 "ruido se estabiliza y los armónicos reales destacan).\n"
                 "NO tiene relación con el modo de promedio del osciloscopio.",
                 "Done on the computer: averages the spectrum of several captures (the noise "
                 "floor settles and real harmonics stand out).\n"
                 "It is NOT related to the oscilloscope's average mode."),
    "bt_auto": ("Autoajustar escala vertical", "Auto-fit vertical scale"),
    "tip_auto": ("Hace que la señal ocupe 50-90% de la pantalla (el osciloscopio tiene solo 8 bits).",
                 "Makes the signal fill 50-90% of the screen (the oscilloscope has only 8 bits)."),
    # --- pestañas y gráficas / tabs and plots
    "tab_vivo": ("En vivo", "Live"),
    "tab_dac": ("Análisis DAC", "DAC analysis"),
    "chk_autoescala": ("Auto-escala", "Auto-scale"),
    "zoom_x_mas": ("Zoom X +", "Zoom X +"),
    "zoom_x_menos": ("Zoom X −", "Zoom X −"),
    "zoom_y_mas": ("Zoom Y +", "Zoom Y +"),
    "zoom_y_menos": ("Zoom Y −", "Zoom Y −"),
    "eje_tiempo": ("Tiempo", "Time"),
    "eje_tension": ("Tensión", "Voltage"),
    "eje_frec": ("Frecuencia", "Frequency"),
    "eje_nivel": ("Nivel", "Level"),
    "eje_tiempo_ms": ("Tiempo (ms)", "Time (ms)"),
    "eje_tension_v": ("Tensión (V)", "Voltage (V)"),
    "medidas1": ("Vpp {vpp:.3f} V | Vmax {vmax:.3f} V | Vmin {vmin:.3f} V | Vmedia {vmed:.3f} V | "
                 "Vrms {vrms:.3f} V | f {f}",
                 "Vpp {vpp:.3f} V | Vmax {vmax:.3f} V | Vmin {vmin:.3f} V | Vmean {vmed:.3f} V | "
                 "Vrms {vrms:.3f} V | f {f}"),
    "medidas2": ("{n} puntos | Fs {fs} | base de tiempos {base}/div | ventana {ms:.2f} ms | "
                 "escalón del ADC del osciloscopio ≈ {lsb}",
                 "{n} points | Fs {fs} | time base {base}/div | window {ms:.2f} ms | "
                 "oscilloscope ADC step ≈ {lsb}"),
    # --- análisis DAC / DAC analysis
    "lb_bw": ("Ancho de banda de la medida:", "Measurement bandwidth:"),
    "bw_completo": ("completo", "full"),
    "tip_bw": ("Por defecto, la banda de Nyquist del propio DAC (frecuencia de actualización / 2). "
               "0 = hasta Nyquist del osciloscopio.",
               "By default, the DAC's own Nyquist band (update rate / 2). "
               "0 = up to the oscilloscope's Nyquist."),
    "chk_banda": ("Ajustar gráfica a la banda", "Fit plot to the band"),
    "dac_inicial": ("Captura una señal (RUN o Captura única)",
                    "Capture a signal (RUN or Single capture)"),
    "dac_error": ("No se pudo analizar: {e}", "Analysis failed: {e}"),
    "dac_l1": ("Fs {fs:.1f} kS/s | {n} puntos | resolución {res:.1f} Hz | Fundamental {f0:.0f} Hz | "
               "promedios {k}/{N}",
               "Fs {fs:.1f} kS/s | {n} points | resolution {res:.1f} Hz | Fundamental {f0:.0f} Hz | "
               "averages {k}/{N}"),
    "dac_l2": ("Excluye solo DC y la zona de la fundamental (±{z:.0f} Hz = 4 bins)",
               "Excludes only DC and the fundamental's zone (±{z:.0f} Hz = 4 bins)"),
    "dac_l3": ("THD {thd} | SNR {snr:.1f} dB | SINAD {sinad:.1f} dB | ENOB {enob:.2f} bits "
               "(banda 0-{bw:.1f} kHz)",
               "THD {thd} | SNR {snr:.1f} dB | SINAD {sinad:.1f} dB | ENOB {enob:.2f} bits "
               "(band 0-{bw:.1f} kHz)"),
    "thd_ruido": ("< ruido", "< noise"),
    "aviso_periodos": ("Solo {p:.1f} periodos: aumenta el tiempo por división (p. ej. 1 ms/div) o usa RAW",
                       "Only {p:.1f} periods: increase the time per division (e.g. 1 ms/div) or use RAW"),
    "aviso_fs": ("Fs baja ({fs:.0f} kS/s): puede haber aliasing; activa RAW",
                 "Low Fs ({fs:.0f} kS/s): aliasing is possible; enable RAW"),
    # --- estado y errores / status and errors
    "conectado": ("Conectado: {nombre}", "Connected: {nombre}"),
    "desconectado": ("Desconectado", "Disconnected"),
    "error_conectar": ("Error al conectar: {e}", "Connection error: {e}"),
    "error_config": ("Error al configurar el osciloscopio: {e}", "Error configuring the oscilloscope: {e}"),
    "error_generico": ("Error: {msg}", "Error: {msg}"),
    "error_auto": ("Error al autoajustar: {e}", "Auto-fit error: {e}"),
    "escala_ok": ("Escala vertical ajustada", "Vertical scale adjusted"),
    "escala_ok_v": ("Escala vertical ajustada: {esc} V/div", "Vertical scale adjusted: {esc} V/div"),
    "barra_adq": ("Base de tiempos: {base}/div | Ventana: {ventana} | Fs {fs} | {n} puntos",
                  "Time base: {base}/div | Window: {ventana} | Fs {fs} | {n} points"),
    "err_n_puntos": ("El osciloscopio devolvió {n} puntos", "The oscilloscope returned {n} points"),
    "err_pocos_puntos": ("El osciloscopio devolvió {n} puntos ({que}). Revisa que el canal esté activo "
                         "y la señal conectada.",
                         "The oscilloscope returned {n} points ({que}). Check that the channel is "
                         "enabled and the signal is connected."),
    "err_resp_inesperada": ("Respuesta inesperada a '{cmd}': {resp}", "Unexpected response to '{cmd}': {resp}"),
    "err_timeout_adq": ("El osciloscopio no terminó la adquisición.",
                        "The oscilloscope did not finish the acquisition."),
    "cfg_aver": ("{tipo} con {n} promedios", "{tipo} with {n} averages"),
    "cfg_no_aver": ("{tipo} (el nº de promedios del osciloscopio solo se usa en modo AVER)",
                    "{tipo} (the oscilloscope's average count is only used in AVER mode)"),
    "cfg_resumen": ("Osciloscopio: adquisición={adq}, filtro 20 MHz={bwl}, sonda={sonda}, "
                    "canales activos={canales}",
                    "Oscilloscope: acquisition={adq}, 20 MHz filter={bwl}, probe={sonda}, "
                    "active channels={canales}"),
    # --- línea de comandos / command line
    "cli_uso_dac": ("Uso: python analisis_dac.py captura_ch1.csv", "Usage: python analisis_dac.py captura_ch1.csv"),
    "cli_aviso_periodos": ("AVISO: solo {p:.1f} periodos capturados; usa >= 10.",
                           "WARNING: only {p:.1f} periods captured; use >= 10."),
    "cli_fs_f0": ("Fs = {fs:.1f} kS/s | Fundamental = {f0:.1f} Hz", "Fs = {fs:.1f} kS/s | Fundamental = {f0:.1f} Hz"),
    "cli_thd_no_detectable": ("no detectable (por debajo del ruido)", "not detectable (below the noise)"),
    "cli_armonico": ("  Armónico {h}: {f:.0f} Hz, {db:.1f} dBc", "  Harmonic {h}: {f:.0f} Hz, {db:.1f} dBc"),
    "cli_conectado": ("Conectado a: {idn}", "Connected to: {idn}"),
    "cli_resumen": ("{n} puntos | Fs = {fs:.1f} kS/s | Vpp = {vpp:.3f} V",
                    "{n} points | Fs = {fs:.1f} kS/s | Vpp = {vpp:.3f} V"),
    "cli_csv_cabecera": ("tiempo_s,tension_V", "time_s,voltage_V"),
    "cli_forma_onda": ("Forma de onda", "Waveform"),
    "cli_espectro": ("Espectro | SINAD {sinad:.1f} dB, ENOB {enob:.2f} bits",
                     "Spectrum | SINAD {sinad:.1f} dB, ENOB {enob:.2f} bits"),
    # --- exportar datos / export data
    "bt_img": ("Guardar imagen", "Save image"),
    "tip_img": ("Guarda una imagen PNG de toda la ventana del programa.",
                "Saves a PNG image of the whole program window."),
    "img_guardada": ("Imagen guardada en {ruta}", "Image saved to {ruta}"),
    "err_guardar": ("No se pudo guardar: {e}", "Could not save: {e}"),
    # --- validación del analizador / analyzer validation (validacion_analisis.py)
    "val_titulo": ("Validación del analizador con señales sintéticas de resultado conocido",
                   "Analyzer validation with synthetic signals of known result"),
    "val_t1": ("1) Seno ideal cuantizado a 8 bits, toda la banda (teoría: SINAD {sinad:.1f} dB, ENOB 8.0)",
               "1) Ideal 8-bit quantized sine, full band (theory: SINAD {sinad:.1f} dB, ENOB 8.0)"),
    "val_t2": ("2) El mismo seno, banda 0-{bw:.1f} kHz como en la GUI",
               "2) The same sine, band 0-{bw:.1f} kHz as in the GUI"),
    "val_t3": ("3) Escalera de esp32_dac_seno.ino (64 muestras de 15 us), banda 0-{bw:.1f} kHz: "
               "un DAC de 8 bits ideal (informativo: ver la nota final)",
               "3) Staircase of esp32_dac_seno.ino (64 samples of 15 us), band 0-{bw:.1f} kHz: "
               "an ideal 8-bit DAC (informative: see the final note)"),
    "val_t4": ("4) Seno + 2º armónico a -60 dBc (THD esperado: -60.0 dBc)",
               "4) Sine + 2nd harmonic at -60 dBc (expected THD: -60.0 dBc)"),
    "val_t5": ("5) Seno + ruido blanco con SNR de 40 dB (SNR esperada: 40.0 dB)",
               "5) Sine + white noise with 40 dB SNR (expected SNR: 40.0 dB)"),
    "val_l_sinad": ("  {ms:>4d} ms | SINAD medido {med:.2f} dB | referencia {ref:.2f} dB | "
                    "diferencia {dif:+.2f} dB | ENOB {enob:.2f} | {estado}",
                    "  {ms:>4d} ms | measured SINAD {med:.2f} dB | reference {ref:.2f} dB | "
                    "difference {dif:+.2f} dB | ENOB {enob:.2f} | {estado}"),
    "val_l_thd": ("  {ms:>4d} ms | THD medido {med:.2f} dBc | diferencia {dif:+.2f} dB | {estado}",
                  "  {ms:>4d} ms | measured THD {med:.2f} dBc | difference {dif:+.2f} dB | {estado}"),
    "val_l_snr": ("  {ms:>4d} ms | SNR medida {med:.2f} dB | diferencia {dif:+.2f} dB | {estado}",
                  "  {ms:>4d} ms | measured SNR {med:.2f} dB | difference {dif:+.2f} dB | {estado}"),
    "val_ok": ("OK", "OK"),
    "val_fallo": ("FALLO", "FAIL"),
    "val_ref": ("Referencia: la referencia de cada prueba se calcula aparte a partir de las líneas "
                "espectrales exactas de la señal.",
                "Reference: each test's reference is computed separately from the signal's exact "
                "spectral lines."),
    "val_nota": ("Nota: 6.02*N+1.76 (SINAD 49.9 dB, ENOB 8.0 para N=8) es el valor medio de un cuantizador "
                 "con error blanco en toda la banda de Nyquist; el test 1 lo reproduce. En el test 3 la "
                 "escalera ideal da {sinad:.1f} dB (ENOB {enob:.2f}) por dos efectos, ninguno es un fallo "
                 "del analizador: el error de una tabla de 64 puntos no es blanco ({a:+.1f} dB) y el "
                 "mantenimiento de la salida atenua los armonicos altos ({b:+.1f} dB).",
                 "Note: 6.02*N+1.76 (SINAD 49.9 dB, ENOB 8.0 for N=8) is the average value of a quantizer "
                 "with white error over the whole Nyquist band; test 1 reproduces it. In test 3 the ideal "
                 "staircase gives {sinad:.1f} dB (ENOB {enob:.2f}) because of two effects, neither is an "
                 "analyzer fault: the error of a 64-point table is not white ({a:+.1f} dB) and the output "
                 "hold attenuates the high harmonics ({b:+.1f} dB)."),
    "val_final_ok": ("RESULTADO: todas las comprobaciones superadas", "RESULT: all checks passed"),
    "val_final_fallo": ("RESULTADO: hay comprobaciones fallidas", "RESULT: some checks failed"),
}
