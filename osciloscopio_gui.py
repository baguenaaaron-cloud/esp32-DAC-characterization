import os
import sys
from collections import deque
from datetime import datetime

import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets

from analisis_dac import ANCHO, analizar, espectro
from idioma import IDIOMAS, get_idioma, set_idioma, tr

MEMORIAS = (12000, 120000, 1200000)          # misma posición que mem_12k, mem_120k, mem_1_2M
CLAVES_MEMORIA = ("mem_12k", "mem_120k", "mem_1_2M")
F_ACTUALIZACION_DAC = 1 / 15e-6              # el sketch actualiza el DAC cada 15 us
NOMBRES_IDIOMA = {"es": "Español", "en": "English"}

# ----------------------------------------------------------------- temas
TEMAS = {
    "oscuro": dict(
        ventana="#2b2b2b", base="#1e1e1e", base_alt="#262626", texto="#e6e6e6",
        boton="#3a3a3a", acento="#2a82da", acento_texto="#ffffff", inactivo="#808080",
        grafica="#101010", grafica_texto="#d0d0d0", rejilla=0.25,
        traza="#ffd33d", espectro="#4dd0e1", banda="#ff5252"),
    "claro": dict(
        ventana="#f0f0f0", base="#ffffff", base_alt="#f5f5f5", texto="#1a1a1a",
        boton="#e4e4e4", acento="#1a73e8", acento_texto="#ffffff", inactivo="#9a9a9a",
        grafica="#ffffff", grafica_texto="#222222", rejilla=0.35,
        traza="#1565c0", espectro="#00838f", banda="#c62828"),
}
ETIQUETAS_TEMA = ("oscuro", "claro")         # orden de las opciones del selector


def tema_del_sistema():
    """'claro' u 'oscuro' según el sistema (Qt >= 6.5); 'oscuro' si no se puede saber."""
    try:
        esquema = QtWidgets.QApplication.styleHints().colorScheme()
        return "claro" if esquema == QtCore.Qt.ColorScheme.Light else "oscuro"
    except Exception:                                    # noqa: BLE001
        return "oscuro"


def fuente_mono(widget, cursiva=False):
    """Fuente monoespaciada de 15 px. Se usa una QFont y no una hoja de estilo, porque las hojas
    de estilo de cada widget no se actualizan al cambiar la paleta (tema claro/oscuro)."""
    f = QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont)
    f.setPixelSize(15)
    f.setItalic(cursiva)
    widget.setFont(f)


def paleta(c):
    """QPalette de la aplicación a partir de un tema."""
    P = QtGui.QPalette
    pal = P()
    q = QtGui.QColor
    for rol, color in ((P.Window, c["ventana"]), (P.WindowText, c["texto"]),
                       (P.Base, c["base"]), (P.AlternateBase, c["base_alt"]),
                       (P.ToolTipBase, c["base"]), (P.ToolTipText, c["texto"]),
                       (P.Text, c["texto"]), (P.Button, c["boton"]),
                       (P.ButtonText, c["texto"]), (P.BrightText, "#ff0000"),
                       (P.Link, c["acento"]), (P.Highlight, c["acento"]),
                       (P.HighlightedText, c["acento_texto"])):
        pal.setColor(rol, q(color))
    for rol in (P.Text, P.ButtonText, P.WindowText):
        pal.setColor(P.Disabled, rol, q(c["inactivo"]))
    return pal


# ----------------------------------------------------------------- instrumentos
class Rigol:
    def __init__(self):
        import captura_rigol as cr
        self.cr = cr
        self.osc = cr.conectar()
        self.nombre = self.osc.query("*IDN?").strip()
        self.serie_z = cr.es_serie_z(self.osc)

    def preparar(self, canal, bwl=False, adq="NORM"):
        self.cr.configurar_bw(self.osc, canal, bwl, self.serie_z)
        if self.serie_z and adq:                        # adq=None -> no se toca
            self.cr.configurar_adquisicion(self.osc, adq)

    def capturar(self, canal, raw=False, mdep=120000):
        cr = self.cr
        if self.serie_z:
            return (cr.capturar_raw_z(self.osc, canal, mdep) if raw
                    else cr.capturar_serie_z(self.osc, canal))
        return (cr.capturar_raw_e(self.osc, canal, mdep >= 100000) if raw
                else cr.capturar_serie_e(self.osc, canal))

    def ajustar_vertical(self, canal, vmin, vmax):
        return self.cr.ajustar_vertical(self.osc, canal, vmin, vmax)

    def cerrar(self):
        self.osc.close()


# ----------------------------------------------------------------- hilos
class Adquisidor(QtCore.QThread):
    """Captura en un hilo aparte para que la ventana no se congele."""
    datos = QtCore.Signal(object, object)
    error = QtCore.Signal(str)

    def __init__(self, inst, canal, continuo, opc):
        super().__init__()
        self.inst, self.canal, self.continuo = inst, canal, continuo
        self.opc = opc
        self._parar = False

    def parar(self):
        self._parar = True

    def run(self):
        try:
            while not self._parar:
                t, v = self.inst.capturar(self.canal, **self.opc)
                if len(v) < 2:
                    raise RuntimeError(tr("err_n_puntos", n=len(v)))
                self.datos.emit(t, v)
                if not self.continuo:
                    break
                self.msleep(20)
        except Exception as e:  # noqa: BLE001
            self.error.emit(str(e))


def estimar_frecuencia(t, v):
    """Cruces por cero con histéresis (ignora el rizado de alta frecuencia)."""
    x = v - v.mean()
    h = 0.2 * (x.max() - x.min()) / 2
    if h <= 0:
        return None
    est = np.where(x > h, 1, np.where(x < -h, -1, 0))
    idx = np.where(est != 0, np.arange(len(est)), 0)
    est = est[np.maximum.accumulate(idx)]
    subidas = np.where((est[:-1] == -1) & (est[1:] == 1))[0] + 1
    tc = []
    for i in subidas:
        antes = np.where(x[:i] < 0)[0]
        if len(antes):
            j = antes[-1]
            tc.append(t[j] + (-x[j]) / (x[j + 1] - x[j]) * (t[j + 1] - t[j]))
    if len(tc) < 2:
        return None
    return (len(tc) - 1) / (tc[-1] - tc[0])


def base_125(x):
    """La base de tiempos de la secuencia 1-2-5 más cercana a x (s/div). Sale de la propia captura
    (n / Fs / 12 divisiones), así que no hace falta preguntarle nada al osciloscopio."""
    decada = 10 ** np.floor(np.log10(x))
    return min((m * decada for m in (1, 2, 5, 10)), key=lambda c: abs(np.log(c / x)))


def downsampling(curva):
    curva.setClipToView(True)
    try:
        curva.setDownsampling(auto=True, method="peak")
    except TypeError:                       # pyqtgraph antiguo
        curva.setDownsampling(auto=True, mode="peak")


# ----------------------------------------------------------------- ventana
class Ventana(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1150, 850)
        self.inst = None
        self.hilo = None
        self.espectros = deque(maxlen=64)
        self.ajustes = QtCore.QSettings("BancoPruebas", "osciloscopio_gui")
        self._estado = ("desconectado", {})
        self._ultimo = None                  # (t, v) de la última captura
        self._dac = None                     # datos de la última medida DAC
        self.tema = "oscuro"

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        lay = QtWidgets.QVBoxLayout(central)

        # --- barra 1: conexión, control, idioma y tema
        barra = QtWidgets.QHBoxLayout()
        self.bt_conectar = QtWidgets.QPushButton()
        self.lb_canal = QtWidgets.QLabel()
        self.cb_canal = QtWidgets.QComboBox()
        self.cb_canal.addItems(["CH1", "CH2"])
        self.bt_run = QtWidgets.QPushButton()
        self.bt_run.setCheckable(True)
        self.bt_single = QtWidgets.QPushButton()
        for w in (self.bt_conectar, self.lb_canal, self.cb_canal, self.bt_run, self.bt_single):
            barra.addWidget(w)
        barra.addStretch()
        self.lb_idioma = QtWidgets.QLabel()
        self.cb_idioma = QtWidgets.QComboBox()
        self.cb_idioma.addItems([NOMBRES_IDIOMA[i] for i in IDIOMAS])
        self.lb_tema = QtWidgets.QLabel()
        self.cb_tema = QtWidgets.QComboBox()
        self.cb_tema.addItems(["", ""])
        for w in (self.lb_idioma, self.cb_idioma, self.lb_tema, self.cb_tema):
            barra.addWidget(w)
        lay.addLayout(barra)

        # --- barra 2: precisión
        barra2 = QtWidgets.QHBoxLayout()
        self.chk_raw = QtWidgets.QCheckBox()
        self.cb_mdep = QtWidgets.QComboBox()
        self.cb_mdep.addItems([""] * len(MEMORIAS))
        self.cb_mdep.setCurrentIndex(1)                  # 120 k
        self.chk_bwl = QtWidgets.QCheckBox()
        self.cb_adq = QtWidgets.QComboBox()
        self.cb_adq.addItems(["", "", ""])
        self.lb_prom = QtWidgets.QLabel()
        self.sp_prom = QtWidgets.QSpinBox()
        self.sp_prom.setRange(1, 64)
        self.bt_auto = QtWidgets.QPushButton()
        self.bt_img = QtWidgets.QPushButton()
        for w in (self.chk_raw, self.cb_mdep, self.chk_bwl, self.cb_adq,
                  self.lb_prom, self.sp_prom, self.bt_auto):
            barra2.addWidget(w)
        barra2.addStretch()
        barra2.addWidget(self.bt_img)
        lay.addLayout(barra2)
        self.bt_img.setEnabled(False)                    # se activa con la primera captura
        for w in (self.bt_run, self.bt_single, self.bt_auto):
            w.setEnabled(False)

        # --- pestañas
        self.tabs = QtWidgets.QTabWidget()
        lay.addWidget(self.tabs, 1)
        self.tabs.addTab(self._tab_vivo(), "")
        self.tabs.addTab(self._tab_dac(), "")

        self.estado = QtWidgets.QLabel()
        self.statusBar().addWidget(self.estado)
        # La base de tiempos y la ventana van en un texto fijo, aparte de los mensajes de estado
        # (que se pisan unos a otros): así no desaparecen ni salen sin actualizar en las imágenes.
        self.lb_adq = QtWidgets.QLabel()
        self.statusBar().addPermanentWidget(self.lb_adq)

        self._plots = [self.plot, self.plot_fft]
        for cb in (self.cb_idioma, self.cb_tema, self.cb_mdep, self.cb_adq):
            cb.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)

        # --- idioma y tema iniciales (los guardados; si no, español y el del sistema)
        idioma = str(self.ajustes.value("idioma", "es"))
        tema = str(self.ajustes.value("tema", tema_del_sistema()))
        set_idioma(idioma if idioma in IDIOMAS else "es")
        self.cb_idioma.setCurrentIndex(IDIOMAS.index(get_idioma()))
        self.tema = tema if tema in TEMAS else "oscuro"
        self.cb_tema.setCurrentIndex(ETIQUETAS_TEMA.index(self.tema))
        self.aplicar_tema(self.tema)
        self.retraducir()

        self.bt_conectar.clicked.connect(self.conectar)
        self.bt_run.toggled.connect(self.run_toggled)
        self.bt_single.clicked.connect(self.captura_unica)
        self.bt_auto.clicked.connect(self.autoescala)
        self.bt_img.clicked.connect(self.guardar_imagen)
        self.tabs.currentChanged.connect(lambda _: self.espectros.clear())
        self.cb_idioma.currentIndexChanged.connect(self.cambiar_idioma)
        self.cb_tema.currentIndexChanged.connect(self.cambiar_tema)
        for sig in (self.chk_raw.toggled, self.cb_mdep.currentIndexChanged,
                    self.chk_bwl.toggled, self.cb_adq.currentIndexChanged,
                    self.cb_canal.currentIndexChanged,
                    self.sp_prom.valueChanged):
            sig.connect(self.on_cambio_config)

    # ---- pestaña en vivo
    def _tab_vivo(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(w)
        self.plot = pg.PlotWidget()
        self.curva = self.plot.plot(pen=pg.mkPen("y", width=1.5))
        downsampling(self.curva)
        l.addWidget(self.plot, 1)

        fila = QtWidgets.QHBoxLayout()
        self.chk_auto = QtWidgets.QCheckBox()
        self.chk_auto.setChecked(True)
        self.chk_auto.toggled.connect(self.auto_toggled)
        fila.addWidget(self.chk_auto)
        self.bt_zoom = []
        for clave, f in (("zoom_x_mas", (0.5, 1)), ("zoom_x_menos", (2, 1)),
                         ("zoom_y_mas", (1, 0.5)), ("zoom_y_menos", (1, 2))):
            b = QtWidgets.QPushButton()
            b.clicked.connect(lambda _, f=f: self.zoom(f))
            self.bt_zoom.append((clave, b))
            fila.addWidget(b)
        fila.addStretch()
        l.addLayout(fila)

        self.lb_medidas = QtWidgets.QLabel("—")
        fuente_mono(self.lb_medidas)
        l.addWidget(self.lb_medidas)
        return w

    # ---- pestaña DAC
    def _tab_dac(self):
        w = QtWidgets.QWidget()
        l = QtWidgets.QVBoxLayout(w)
        fila = QtWidgets.QHBoxLayout()
        self.lb_bw = QtWidgets.QLabel()
        fila.addWidget(self.lb_bw)
        self.sp_bw = QtWidgets.QDoubleSpinBox()
        self.sp_bw.setRange(0, 1e5)
        self.sp_bw.setDecimals(1)
        self.sp_bw.setValue(round(F_ACTUALIZACION_DAC / 2e3, 1))   # 33,3 kHz
        self.sp_bw.setSuffix(" kHz")
        fila.addWidget(self.sp_bw)
        self.chk_banda = QtWidgets.QCheckBox()
        self.chk_banda.setChecked(True)
        fila.addWidget(self.chk_banda)
        fila.addStretch()
        l.addLayout(fila)
        self.plot_fft = pg.PlotWidget()
        self.plot_fft.setYRange(-110, 5)
        self.curva_fft = self.plot_fft.plot(pen=pg.mkPen("c", width=1.5))
        downsampling(self.curva_fft)
        self.linea_bw = pg.InfiniteLine(angle=90, pen=pg.mkPen("r", style=QtCore.Qt.DashLine))
        self.plot_fft.addItem(self.linea_bw)
        l.addWidget(self.plot_fft, 1)
        self.lb_dac = QtWidgets.QLabel()
        fuente_mono(self.lb_dac)
        l.addWidget(self.lb_dac)
        return w

    # ---- idioma y tema
    def cambiar_idioma(self, idx):
        set_idioma(IDIOMAS[idx])
        self.ajustes.setValue("idioma", IDIOMAS[idx])
        self.retraducir()

    def cambiar_tema(self, idx):
        self.tema = ETIQUETAS_TEMA[idx]
        self.ajustes.setValue("tema", self.tema)
        self.aplicar_tema(self.tema)
        self._etiquetas_ejes()

    def aplicar_tema(self, nombre):
        c = TEMAS[nombre]
        app = QtWidgets.QApplication.instance()
        app.setStyle("Fusion")
        app.setPalette(paleta(c))
        pg.setConfigOptions(background=c["grafica"], foreground=c["grafica_texto"])
        for p in self._plots:
            p.setBackground(c["grafica"])
            p.showGrid(x=True, y=True, alpha=c["rejilla"])
            for eje in ("left", "bottom", "top", "right"):
                ax = p.getAxis(eje)
                ax.setPen(pg.mkPen(c["grafica_texto"]))
                ax.setTextPen(pg.mkPen(c["grafica_texto"]))
        self.curva.setPen(pg.mkPen(c["traza"], width=1.5))
        self.curva_fft.setPen(pg.mkPen(c["espectro"], width=1.5))
        self.linea_bw.setPen(pg.mkPen(c["banda"], style=QtCore.Qt.DashLine))

    def _etiquetas_ejes(self):
        """Etiquetas de los ejes (se rehacen al cambiar idioma o tema para tomar sus colores)."""
        self.plot.setLabel("bottom", tr("eje_tiempo"), units="ms")
        self.plot.setLabel("left", tr("eje_tension"), units="V")
        self.plot_fft.setLabel("bottom", tr("eje_frec"), units="kHz")
        self.plot_fft.setLabel("left", tr("eje_nivel"), units="dBc")

    def retraducir(self):
        """Pone todos los textos en el idioma actual."""
        self.setWindowTitle(tr("titulo"))
        self.bt_conectar.setText(tr("desconectar") if self.inst else tr("conectar"))
        self.lb_canal.setText(tr("lb_canal"))
        self.bt_run.setText(tr("stop") if self.bt_run.isChecked() else tr("run"))
        self.bt_single.setText(tr("captura_unica"))
        self.lb_idioma.setText(tr("lb_idioma"))
        self.lb_tema.setText(tr("lb_tema"))
        for i, nombre in enumerate(ETIQUETAS_TEMA):
            self.cb_tema.setItemText(i, tr("tema_" + nombre))
        self.chk_raw.setText(tr("chk_raw"))
        self.chk_raw.setToolTip(tr("tip_raw"))
        for i, clave in enumerate(CLAVES_MEMORIA):
            self.cb_mdep.setItemText(i, tr(clave))
        self.chk_bwl.setText(tr("chk_bwl"))
        self.chk_bwl.setToolTip(tr("tip_bwl"))
        for i, clave in enumerate(("adq_personalizada", "adq_normal", "adq_hres")):
            self.cb_adq.setItemText(i, tr(clave))
        self.cb_adq.setToolTip(tr("tip_adq"))
        self.lb_prom.setText(tr("lb_prom"))
        self.sp_prom.setToolTip(tr("tip_prom"))
        self.bt_auto.setText(tr("bt_auto"))
        self.bt_auto.setToolTip(tr("tip_auto"))
        self.bt_img.setText(tr("bt_img"))
        self.bt_img.setToolTip(tr("tip_img"))
        for i, clave in enumerate(("tab_vivo", "tab_dac")):
            self.tabs.setTabText(i, tr(clave))
        # en vivo
        self.chk_auto.setText(tr("chk_autoescala"))
        for clave, b in self.bt_zoom:
            b.setText(tr(clave))
        # DAC
        self.lb_bw.setText(tr("lb_bw"))
        self.sp_bw.setSpecialValueText(tr("bw_completo"))
        self.sp_bw.setToolTip(tr("tip_bw"))
        self.chk_banda.setText(tr("chk_banda"))
        # textos que dependen de los datos
        self._etiquetas_ejes()
        self._pintar_estado()
        self._pintar_adquisicion()
        self._pintar_medidas()
        self._pintar_dac_texto()

    # ---- estado
    def set_estado(self, clave, **kw):
        """Muestra tr(clave, **kw) y lo recuerda para retraducirlo si cambia el idioma."""
        self._estado = (clave, kw)
        self._pintar_estado()

    def set_estado_texto(self, texto):
        self._estado = (None, texto)
        self._pintar_estado()

    def _pintar_estado(self):
        clave, kw = self._estado
        self.estado.setText(kw if clave is None else tr(clave, **kw))

    # ---- conexión del osciloscopio
    def conectar(self):
        if self.inst is not None:
            self.desconectar()
            return
        try:
            self.inst = Rigol()
        except Exception as e:  # noqa: BLE001
            self.set_estado("error_conectar", e=e)
            self.inst = None
            return
        self.bt_conectar.setText(tr("desconectar"))
        for w in (self.bt_run, self.bt_single, self.bt_auto):
            w.setEnabled(True)
        self.set_estado("conectado", nombre=self.inst.nombre)

    def desconectar(self):
        self.bt_run.setChecked(False)
        self.parar_hilo()
        try:
            self.inst.cerrar()
        finally:
            self.inst = None
        self.bt_conectar.setText(tr("conectar"))
        for w in (self.bt_run, self.bt_single, self.bt_auto):
            w.setEnabled(False)
        self.set_estado("desconectado")

    # ---- adquisición
    def canal(self):
        return self.cb_canal.currentIndex() + 1

    def opciones(self):
        return dict(raw=self.chk_raw.isChecked(), mdep=MEMORIAS[self.cb_mdep.currentIndex()])

    def adq(self):
        return (None, "NORM", "HRES")[self.cb_adq.currentIndex()]

    def lanzar(self, continuo):
        self.parar_hilo()
        try:
            self.inst.preparar(self.canal(), self.chk_bwl.isChecked(), self.adq())
        except Exception as e:  # noqa: BLE001
            self.set_estado("error_config", e=e)
            return
        self.hilo = Adquisidor(self.inst, self.canal(), continuo, self.opciones())
        self.hilo.datos.connect(self.on_datos)
        self.hilo.error.connect(self.on_error)
        self.hilo.start()

    def parar_hilo(self):
        if self.hilo is not None:
            self.hilo.parar()
            self.hilo.wait(30000)
            self.hilo = None

    def run_toggled(self, activo):
        self.bt_run.setText(tr("stop") if activo else tr("run"))
        if activo:
            self.espectros.clear()
            self.lanzar(True)
        else:
            self.parar_hilo()

    def captura_unica(self):
        self.bt_run.setChecked(False)
        self.espectros.clear()
        self.lanzar(False)

    def on_cambio_config(self, *_):
        self.espectros.clear()
        if self.inst is not None and self.bt_run.isChecked():
            self.lanzar(True)           # reinicia con la nueva configuración

    def on_error(self, msg):
        self.bt_run.setChecked(False)
        self.set_estado("error_generico", msg=msg)

    def autoescala(self):
        self.bt_run.setChecked(False)
        try:
            self.inst.preparar(self.canal(), self.chk_bwl.isChecked(), self.adq())
            t, v = self.inst.capturar(self.canal())
            esc = self.inst.ajustar_vertical(self.canal(), v.min(), v.max())
            if esc:
                self.set_estado("escala_ok_v", esc=f"{esc:g}")
            else:
                self.set_estado("escala_ok")
        except Exception as e:  # noqa: BLE001
            self.set_estado("error_auto", e=e)

    # ---- datos nuevos
    @staticmethod
    def paso_adc(v):
        """Escalón de cuantización del osciloscopio: menor diferencia entre niveles."""
        d = np.diff(np.unique(np.round(v, 6)))
        d = d[d > 1e-6]
        return d.min() if d.size else None

    def on_datos(self, t, v):
        self._ultimo = (t, v)
        self.bt_img.setEnabled(True)
        self.curva.setData(t * 1e3, v)
        self._pintar_adquisicion()
        self._pintar_medidas()
        if self.tabs.currentIndex() == 1:
            self.actualizar_dac(t, v, 1 / np.mean(np.diff(t)))

    def _pintar_adquisicion(self):
        """Base de tiempos y ventana de la última captura. Se calculan de la propia captura
        (puntos / Fs entre las 12 divisiones de la pantalla), sin preguntarle nada al osciloscopio,
        así que siguen al ajuste del osciloscopio en cuanto llega una captura nueva."""
        if self._ultimo is None:
            self.lb_adq.setText("")
            return
        t, v = self._ultimo
        fs = 1 / np.mean(np.diff(t))
        base = base_125(len(t) / fs / 12)
        self.lb_adq.setText(tr("barra_adq", base=pg.siFormat(base, suffix="s"),
                               ventana=pg.siFormat(12 * base, suffix="s"),
                               fs=pg.siFormat(fs, suffix="S/s"), n=len(t)))

    def _pintar_medidas(self):
        if self._ultimo is None:
            return
        t, v = self._ultimo
        fs = 1 / np.mean(np.diff(t))
        lsb = self.paso_adc(v)
        f = estimar_frecuencia(t, v)
        self.lb_medidas.setText(
            tr("medidas1", vpp=v.max() - v.min(), vmax=v.max(), vmin=v.min(), vmed=v.mean(),
               vrms=np.sqrt(np.mean(v ** 2)), f=pg.siFormat(f, suffix="Hz") if f else "—")
            + "\n"
            + tr("medidas2", n=len(v), fs=pg.siFormat(fs, suffix="S/s"),
                 base=pg.siFormat(base_125(len(t) / fs / 12), suffix="s"),
                 ms=(t[-1] - t[0]) * 1e3, lsb=f"{lsb * 1e3:.1f} mV" if lsb else "—"))

    # ---- análisis DAC
    def actualizar_dac(self, t, v, fs):
        try:
            X, _, n = espectro(t, v)
            if self.espectros and len(self.espectros[-1]) != len(X):
                self.espectros.clear()
            self.espectros.append(X)
            lista = list(self.espectros)[-self.sp_prom.value():]
            Xp = np.mean(lista, axis=0)
            bw = self.sp_bw.value()
            r = analizar(t, v, f_max=bw * 1e3 if bw > 0 else None, X_promedio=Xp)
        except Exception as e:  # noqa: BLE001
            self._dac = ("error", e)
            self._pintar_dac_texto()
            return
        self.curva_fft.setData(r["f"] / 1e3, 10 * np.log10(Xp / r["p_fund"] + 1e-20))
        self.linea_bw.setValue(r["fmax"] / 1e3)
        if self.chk_banda.isChecked():
            self.plot_fft.setXRange(0, 1.3 * r["fmax"] / 1e3, padding=0)
        self._dac = ("ok", dict(r=r, fs=fs, n=n, k=len(lista), N=self.sp_prom.value(),
                                ms=(t[-1] - t[0]) * 1e3))
        self._pintar_dac_texto()

    def _pintar_dac_texto(self):
        if self._dac is None:
            self.lb_dac.setText(tr("dac_inicial"))
            return
        estado, d = self._dac
        if estado == "error":
            self.lb_dac.setText(tr("dac_error", e=d))
            return
        r, fs, n = d["r"], d["fs"], d["n"]
        z = ANCHO * fs / n                                # zona excluida junto a DC y a la fundamental
        avisos = []
        if r["n_periodos"] < 10:
            avisos.append(tr("aviso_periodos", p=r["n_periodos"]))
        if fs < 250e3:
            avisos.append(tr("aviso_fs", fs=fs / 1e3))
        thd = f"{r['thd']:.1f} dBc" if np.isfinite(r["thd"]) else tr("thd_ruido")
        arm = "  ".join(f"H{h}:{db:.0f}dBc" for h, _, db in r["armonicos"][:5])
        lineas = [
            tr("dac_l1", fs=fs / 1e3, n=n, res=fs / n, f0=r["f0"], k=d["k"], N=d["N"]),
            tr("dac_l2", z=z),
            tr("dac_l3", thd=thd, snr=r["snr"], sinad=r["sinad"], enob=r["enob"],
               bw=r["fmax"] / 1e3),
        ] + ([arm] if arm else []) + [f"⚠ {a}" for a in avisos]
        self.lb_dac.setText("\n".join(lineas))

    # ---- exportar datos
    def _ruta_guardado(self, titulo, nombre, filtro):
        """Pide dónde guardar; recuerda la última carpeta usada."""
        carpeta = str(self.ajustes.value("carpeta", os.getcwd()))
        ruta, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, titulo, os.path.join(carpeta, nombre), filtro)
        if ruta:
            self.ajustes.setValue("carpeta", os.path.dirname(ruta))
        return ruta

    def guardar_imagen(self):
        """Imagen PNG de toda la ventana del programa (barras, pestaña activa y medidas)."""
        if self._ultimo is None:
            return
        nombre = ("vivo", "espectro")[self.tabs.currentIndex()]
        ruta = self._ruta_guardado(
            tr("bt_img"), f"{nombre}_ch{self.canal()}_{datetime.now():%Y%m%d_%H%M%S}.png",
            "PNG (*.png)")
        if not ruta:
            return
        try:
            if not self.grab().save(ruta, "PNG"):
                raise OSError(ruta)
        except Exception as e:  # noqa: BLE001
            self.set_estado("err_guardar", e=e)
            return
        self.set_estado("img_guardada", ruta=ruta)

    # ---- zoom
    def auto_toggled(self, on):
        self.plot.getViewBox().enableAutoRange(enable=on)

    def zoom(self, factor):
        self.chk_auto.setChecked(False)
        self.plot.getViewBox().scaleBy(factor)

    def closeEvent(self, ev):
        if self.inst is not None:
            self.desconectar()
        ev.accept()


def main():
    app = QtWidgets.QApplication(sys.argv)
    v = Ventana()
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
