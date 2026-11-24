import sys
import numpy as np
from scipy.signal.windows import blackmanharris
import matplotlib.pyplot as plt

from idioma import tr

N_ARMONICOS = 9      # hasta el 9º armónico
UMBRAL_ARMONICO = 10   # veces el suelo de ruido (10 = +10 dB)
ANCHO = 4            # bins a cada lado de un tono (lóbulo de Blackman-Harris)


def cargar(ruta):
    d = np.loadtxt(ruta, delimiter=",", skiprows=1)
    return d[:, 0], d[:, 1]


def espectro(t, v):
    """Espectro de potencia con ventana Blackman-Harris. Devuelve (X, fs, n)."""
    fs = 1 / np.mean(np.diff(t))
    n = len(v)
    w = blackmanharris(n)
    # Se resta la media ponderada por la ventana (no la media simple): con un número no entero de
    # periodos la media simple deja un residuo de DC que la ventana reparte por los primeros bins.
    X = np.abs(np.fft.rfft((v - np.sum(v * w) / np.sum(w)) * w)) ** 2
    return X, fs, n


def analizar(t, v, f_max=None, X_promedio=None):
    """X_promedio: espectro ya promediado de varias capturas (misma longitud)."""
    X, fs, n = espectro(t, v)
    if X_promedio is not None and len(X_promedio) == len(X):
        X = X_promedio
    f = np.fft.rfftfreq(n, 1 / fs)
    df = f[1] - f[0]
    fmax = f_max if f_max else fs / 2        # ancho de banda de la medida

    # Fundamental: pico máximo (ignorando solo DC y el bin 1)
    k0 = 2 + np.argmax(X[2:])
    # Interpolación parabólica (sobre el log) para afinar la frecuencia entre bins
    a, b, c = np.log(X[k0 - 1:k0 + 2] + 1e-30)
    delta = 0.5 * (a - c) / (a - 2 * b + c)
    f0 = (k0 + delta) * df
    n_periodos = f0 * n / fs

    def potencia_tono(k):
        a, b = max(k - ANCHO, 0), min(k + ANCHO + 1, len(X))
        return X[a:b].sum(), (a, b)

    p_fund, banda_f = potencia_tono(k0)
    usados = np.zeros(len(X), bool)
    usados[0] = True                          # solo DC: el ruido de baja frecuencia sí cuenta
    usados[banda_f[0]:banda_f[1]] = True
    usados[f > fmax] = True                   # fuera del ancho de banda

    # Suelo de ruido típico por bin (mediana, robusta frente a picos)
    suelo = np.median(X[~usados])

    # Armónicos (se pliegan si superan Nyquist: aliasing).
    # Solo cuentan si sobresalen >= 10 dB del suelo de ruido; si no, son ruido.
    p_arm, armonicos = 0.0, []
    for h in range(2, N_ARMONICOS + 1):
        if h * f0 > fmax:
            break
        fh = (h * f0) % fs
        if fh > fs / 2:
            fh = fs - fh
        kh = int(round(fh / df))
        if kh <= ANCHO or kh >= len(X) - ANCHO or usados[kh]:
            continue
        if X[max(kh - 2, 0):kh + 3].max() < UMBRAL_ARMONICO * suelo:
            continue
        p, (a, b) = potencia_tono(kh)
        p_arm += p
        usados[a:b] = True
        armonicos.append((h, f[kh], 10 * np.log10(p / p_fund)))

    p_ruido = X[~usados].sum()

    thd = 10 * np.log10(p_arm / p_fund) if p_arm > 0 else -np.inf
    snr = 10 * np.log10(p_fund / p_ruido)
    sinad = 10 * np.log10(p_fund / (p_ruido + p_arm))
    enob = (sinad - 1.76) / 6.02
    return dict(n_periodos=n_periodos, fmax=fmax, fs=fs, f0=f0, thd=thd, snr=snr, sinad=sinad, enob=enob,
                armonicos=armonicos, f=f, X=X, p_fund=p_fund)


def main():
    if len(sys.argv) < 2:
        sys.exit(tr("cli_uso_dac"))
    t, v = cargar(sys.argv[1])

    r = analizar(t, v)
    if r["n_periodos"] < 10:
        print(tr("cli_aviso_periodos", p=r["n_periodos"]))
    print(tr("cli_fs_f0", fs=r["fs"] / 1e3, f0=r["f0"]))
    print("THD   = " + (f"{r['thd']:.1f} dBc" if np.isfinite(r['thd'])
                        else tr("cli_thd_no_detectable")))
    print(f"SNR   = {r['snr']:.1f} dB")
    print(f"SINAD = {r['sinad']:.1f} dB")
    print(f"ENOB  = {r['enob']:.2f} bits")
    for h, fh, db in r["armonicos"]:
        print(tr("cli_armonico", h=h, f=fh, db=db))

    espectro = 10 * np.log10(r["X"] / r["p_fund"] + 1e-20)
    fig, ax = plt.subplots(2, 1, figsize=(8, 7))
    ax[0].plot(t * 1e3, v)
    ax[0].set(xlabel=tr("eje_tiempo_ms"), ylabel=tr("eje_tension_v"), title=tr("cli_forma_onda"))
    ax[0].grid(True)
    ax[1].plot(r["f"] / 1e3, espectro)
    ax[1].set(xlabel=tr("eje_frec") + " (kHz)", ylabel="dBc",
              title=tr("cli_espectro", sinad=r["sinad"], enob=r["enob"]))
    ax[1].grid(True)
    plt.tight_layout()
    plt.savefig("analisis_dac.png", dpi=150)
    plt.show()


if __name__ == "__main__":
    main()
