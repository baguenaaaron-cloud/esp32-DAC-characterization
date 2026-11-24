import argparse
import sys
import time
import numpy as np
import pyvisa

from idioma import tr


# ------------------------------------------------------------------ utilidades
def conectar():
    rm = pyvisa.ResourceManager()
    usb = [r for r in rm.list_resources() if r.startswith("USB")]
    if not usb:
        sys.exit("No se encontró ningún instrumento USB. Revisa cable y drivers.")
    osc = rm.open_resource(usb[0])
    osc.timeout = 30000          # ms (las lecturas RAW grandes tardan)
    osc.chunk_size = 1024 * 1024
    return osc


def es_serie_z(osc):
    return "Z" in osc.query("*IDN?").split(",")[1].upper()


def leer_bloque(osc, comando):
    """Envía un comando que devuelve un bloque binario '#N<longitud><datos>'."""
    osc.write(comando)
    raw = osc.read_raw()
    if raw[:1] != b"#":
        raise RuntimeError(tr("err_resp_inesperada", cmd=comando, resp=repr(raw[:80])))
    n_digitos = int(raw[1:2])
    longitud = int(raw[2:2 + n_digitos])
    inicio = 2 + n_digitos
    return np.frombuffer(raw[inicio:inicio + longitud], dtype=np.uint8)


def paso_125(x):
    """Siguiente valor de la secuencia 1-2-5 que sea >= x (escalas del osciloscopio)."""
    dec = 10 ** np.floor(np.log10(x))
    for m in (1, 2, 5, 10):
        if m * dec >= x:
            return m * dec


def configurar_bw(osc, canal, activar, serie_z):
    """Filtro de ancho de banda de 20 MHz (reduce ruido de alta frecuencia)."""
    if serie_z:
        osc.write(f":CHAN{canal}:BWL {'20M' if activar else 'OFF'}")
    else:
        osc.write(f":CHAN{canal}:BWL {'ON' if activar else 'OFF'}")


def configurar_adquisicion(osc, tipo):
    """tipo = 'NORM' (normal) o 'HRES' (alta resolución).
    HRES promedia los puntos vecinos antes de guardarlos: filtra el ruido de banda ancha
    que de otro modo se pliega (aliasing) cuando la memoria se muestrea más despacio
    que el convertidor interno."""
    osc.write(f":ACQ:TYPE {tipo}")


def ajustar_vertical(osc, canal, vmin, vmax, ocupacion=0.9):
    """Pone la escala (1-2-5) y el offset para que la señal use ~50-90% de la pantalla.
    Un osciloscopio de 8 bits mide mucho mejor cuando la señal llena la pantalla.
    Respeta los límites de la guía: escala mínima 1 mV x sonda; offset +-100 V x sonda
    si escala >= 0,5 V x sonda, y +-2 V x sonda si es menor."""
    sonda = float(osc.query(f":CHAN{canal}:PROB?"))
    vpp = max(vmax - vmin, 1e-3 * sonda)
    escala = max(paso_125(vpp / (8 * ocupacion)), 1e-3 * sonda)
    limite = 100 * sonda if escala >= 0.5 * sonda else 2 * sonda
    offset = max(-limite, min(limite, -(vmax + vmin) / 2))
    osc.write(f":CHAN{canal}:SCAL {escala:.4g}")
    osc.write(f":CHAN{canal}:OFFS {offset:.4g}")
    time.sleep(0.3)
    return escala


def _validar(datos, que):
    """Comprueba que el osciloscopio devolvió datos y avisa con detalle si no."""
    if datos.size < 2:
        raise RuntimeError(tr("err_pocos_puntos", n=datos.size, que=que))
    return datos


# ------------------------------------------------------------------ modo NORMAL
def capturar_serie_z(osc, canal):
    osc.write(f":WAV:SOUR CHAN{canal}")
    osc.write(":WAV:MODE NORM")
    osc.write(":WAV:FORM BYTE")
    # El rango STAR/STOP se conserva entre modos: si una lectura RAW anterior lo dejó
    # en otro valor, el modo normal devolvería 1 punto. Lo reiniciamos siempre.
    osc.write(":WAV:STAR 1")
    osc.write(":WAV:STOP 1200")
    pre = osc.query(":WAV:PRE?").split(",")
    xinc, xorigin, xref = float(pre[4]), float(pre[5]), float(pre[6])
    yinc, yorigin, yref = float(pre[7]), float(pre[8]), float(pre[9])
    datos = leer_bloque(osc, ":WAV:DATA?")
    if datos.size < 2:
        info = (f"STAR={osc.query(':WAV:STAR?').strip()}, "
                f"STOP={osc.query(':WAV:STOP?').strip()}, "
                f"state={osc.query(':TRIG:STAT?').strip()}, preamble={pre[:4]}")
        _validar(datos, f"Z series, normal; {info}")
    datos = datos.astype(float)
    volts = (datos - yorigin - yref) * yinc
    t = (np.arange(len(datos)) - xref) * xinc + xorigin
    return t, volts


def capturar_serie_e(osc, canal):
    osc.write(":WAV:POIN:MODE NORM")
    osc.write(f":WAV:SOUR CH{canal}")
    osc.write(":WAV:FORM BYTE")
    vscale = float(osc.query(f":CHAN{canal}:SCAL?"))
    voffset = float(osc.query(f":CHAN{canal}:OFFS?"))
    tscale = float(osc.query(":TIM:SCAL?"))
    toffset = float(osc.query(":TIM:OFFS?"))
    datos = _validar(leer_bloque(osc, f":WAV:DATA? CH{canal}"),
                     "E series, normal").astype(float)
    volts = (240 - datos) * (vscale / 25) - voffset      # 25 niveles/división
    t = np.linspace(-6 * tscale, 6 * tscale, len(datos)) + toffset
    return t, volts


# ------------------------------------------------------------------ modo RAW
def _esperar_stop(osc, timeout=3.0):
    """Espera a que termine una adquisición única (:SING); fuerza trigger si no llega."""
    t0, forzado = time.time(), False
    while True:
        if osc.query(":TRIG:STAT?").strip() == "STOP":
            return
        if time.time() - t0 > timeout and not forzado:
            osc.write(":TFOR")
            forzado = True
        if time.time() - t0 > timeout + 5:
            raise TimeoutError(tr("err_timeout_adq"))
        time.sleep(0.02)


def _canales_activos(osc):
    """Cuántos canales analógicos están encendidos (cambia las memorias permitidas)."""
    activos = 0
    for c in (1, 2):
        try:
            activos += int(float(osc.query(f":CHAN{c}:DISP?")))
        except Exception:                               # noqa: BLE001
            pass
    return max(activos, 1)


def resumen_config(osc, canal):
    """Configuración del osciloscopio que influye en la medida (para mostrarla en pantalla)."""
    def q(cmd):
        try:
            return osc.query(cmd).strip()
        except Exception:                               # noqa: BLE001
            return "?"
    tipo = q(":ACQ:TYPE?")
    adq = (tr("cfg_aver", tipo=tipo, n=q(":ACQ:AVER?")) if tipo.upper().startswith("AVER")
           else tr("cfg_no_aver", tipo=tipo))
    return tr("cfg_resumen", adq=adq, bwl=q(f":CHAN{canal}:BWL?"),
              sonda=q(f":CHAN{canal}:PROB?") + "X", canales=_canales_activos(osc))


def capturar_raw_z(osc, canal, puntos=120000):
    """Serie Z: adquisición única + lectura de toda la memoria en bloques.

    Memorias válidas según la guía de programación de la serie Z:
      1 canal activo : 12k, 120k, 1,2M, 12M, 24M
      2 canales      : 6k, 60k, 600k, 6M, 12M   (se usa la mitad si hay 2 canales)
    """
    osc.write(":RUN")                                   # la memoria solo se cambia en RUN
    if puntos:
        if _canales_activos(osc) == 2:
            puntos //= 2
        osc.write(f":ACQ:MDEP {int(puntos)}")
        time.sleep(0.3)
    osc.write(":SING")
    _esperar_stop(osc)
    osc.write(f":WAV:SOUR CHAN{canal}")
    osc.write(":WAV:MODE RAW")
    osc.write(":WAV:FORM BYTE")
    resp = osc.query(":ACQ:MDEP?").strip()
    if resp.upper() == "AUTO":                          # memoria = Fs x (12 div x base de tiempos)
        n = int(round(float(osc.query(":ACQ:SRAT?")) * 12 * float(osc.query(":TIM:SCAL?"))))
    else:
        n = int(float(resp))
    pre = osc.query(":WAV:PRE?").split(",")
    xinc = float(pre[4])
    yinc, yorigin, yref = float(pre[7]), float(pre[8]), float(pre[9])
    partes, paso = [], 100000
    for ini in range(1, n + 1, paso):
        osc.write(f":WAV:STAR {ini}")
        osc.write(f":WAV:STOP {min(ini + paso - 1, n)}")
        partes.append(leer_bloque(osc, ":WAV:DATA?"))
    osc.write(":WAV:MODE NORM")
    osc.write(":WAV:STAR 1")
    osc.write(":WAV:STOP 1200")
    osc.write(":RUN")
    tam = [p.size for p in partes]
    datos = _validar(np.concatenate(partes), f"Z series, RAW: memory={n}, blocks={tam}")
    datos = datos.astype(float)
    volts = (datos - yorigin - yref) * yinc
    t = (np.arange(len(datos)) - len(datos) / 2) * xinc
    return t, volts


def capturar_raw_e(osc, canal, largo=True):
    """Serie E/D: se para el osciloscopio y se lee la memoria completa."""
    osc.write(":RUN")
    osc.write(f":ACQ:MEMD {'LONG' if largo else 'NORM'}")
    tscale = float(osc.query(":TIM:SCAL?"))
    time.sleep(max(0.3, 16 * tscale))                   # que se llene la memoria
    osc.write(":STOP")
    osc.write(":WAV:POIN:MODE RAW")
    osc.write(f":WAV:SOUR CH{canal}")
    osc.write(":WAV:FORM BYTE")
    vscale = float(osc.query(f":CHAN{canal}:SCAL?"))
    voffset = float(osc.query(f":CHAN{canal}:OFFS?"))
    datos = _validar(leer_bloque(osc, f":WAV:DATA? CH{canal}"),
                     "E series, RAW").astype(float)
    try:
        fs = float(osc.query(f":ACQ:SAMP? CHAN{canal}"))
    except Exception:                                   # noqa: BLE001
        fs = len(datos) / (12 * tscale)
    osc.write(":RUN")
    volts = (240 - datos) * (vscale / 25) - voffset
    t = (np.arange(len(datos)) - len(datos) / 2) / fs
    return t, volts


# ------------------------------------------------------------------ programa
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("canal", type=int, nargs="?", default=1)
    ap.add_argument("--raw", action="store_true", help="memoria profunda")
    ap.add_argument("--puntos", type=int, default=120000)
    args = ap.parse_args()

    osc = conectar()
    idn = osc.query("*IDN?").strip()
    print(tr("cli_conectado", idn=idn))
    z = es_serie_z(osc)
    if args.raw:
        t, v = (capturar_raw_z(osc, args.canal, args.puntos) if z
                else capturar_raw_e(osc, args.canal, args.puntos >= 100000))
    else:
        t, v = (capturar_serie_z if z else capturar_serie_e)(osc, args.canal)
    osc.close()

    fs = 1 / np.mean(np.diff(t))
    print(tr("cli_resumen", n=len(v), fs=fs / 1e3, vpp=v.max() - v.min()))
    np.savetxt(f"captura_ch{args.canal}.csv", np.column_stack([t, v]),
               delimiter=",", header=tr("cli_csv_cabecera"), comments="")

    import matplotlib.pyplot as plt
    plt.plot(t * 1e3, v)
    plt.xlabel(tr("eje_tiempo_ms"))
    plt.ylabel(tr("eje_tension_v"))
    plt.title(f"Rigol DS1102 - CH{args.canal}")
    plt.grid(True)
    plt.savefig(f"captura_ch{args.canal}.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()
