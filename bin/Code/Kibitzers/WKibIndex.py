from PySide2 import QtCore, QtGui, QtWidgets

import FasterCode

import Code
from Code import Position
from Code import AnalisisIndexes
from Code import Game
from Code.Engines import EngineRun
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import Piezas
from Code.QT import QTUtil
from Code.QT import QTVarios
from Code.QT import Tablero
from Code.QT import Voyager


class WKibIndex(QtWidgets.QDialog):
    def __init__(self, cpu):
        QtWidgets.QDialog.__init__(self)

        self.cpu = cpu
        self.kibitzer = cpu.kibitzer

        dicVideo = self.cpu.dic_video
        if not dicVideo:
            dicVideo = {}

        self.siTop = dicVideo.get("SITOP", True)
        self.siShowTablero = dicVideo.get("SHOW_TABLERO", True)
        self.history = []

        self.fen = ""
        self.liData = []

        self.setWindowTitle(cpu.titulo)
        self.setWindowIcon(Iconos.Motor())

        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.Dialog
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )

        self.setBackgroundRole(QtGui.QPalette.Light)

        Code.configuracion = cpu.configuracion

        Code.todasPiezas = Piezas.TodasPiezas()
        config_board = cpu.configuracion.config_board("kib" + cpu.kibitzer.huella, 24)
        self.tablero = Tablero.Tablero(self, config_board)
        self.tablero.crea()
        self.tablero.set_dispatcher(self.mensajero)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("titulo", "", 100, siDerecha=True)
        o_columns.nueva("valor", "", 100, centered=True)
        o_columns.nueva("info", "", 100)
        self.grid = Grid.Grid(self, o_columns, dicVideo=dicVideo, siSelecFilas=True, siCabeceraVisible=True)

        li_acciones = (
            (_("Quit"), Iconos.Kibitzer_Terminar(), self.terminar),
            (_("Continue"), Iconos.Kibitzer_Continuar(), self.play),
            (_("Pause"), Iconos.Kibitzer_Pausa(), self.pause),
            (_("Takeback"), Iconos.Atras(), self.takeback),
            (_("Analyze only color"), Iconos.P_16c(), self.color),
            (_("Show/hide board"), Iconos.Tablero(), self.config_board),
            (_("Manual position"), Iconos.Voyager(), self.set_position),
            ("%s: %s" % (_("Enable"), _("window on top")), Iconos.Top(), self.windowTop),
            ("%s: %s" % (_("Disable"), _("window on top")), Iconos.Bottom(), self.windowBottom),
        )
        self.tb = Controles.TBrutina(self, li_acciones, siTexto=False, tamIcon=16)
        self.tb.setAccionVisible(self.play, False)

        ly1 = Colocacion.H().control(self.tb).relleno()
        ly2 = Colocacion.V().otro(ly1).control(self.grid)

        layout = Colocacion.H().control(self.tablero).otro(ly2)
        self.setLayout(layout)

        self.siPlay = True
        self.is_white = True
        self.siNegras = True

        if not self.siShowTablero:
            self.tablero.hide()
        self.restore_video(dicVideo)
        self.ponFlags()

        self.engine = self.lanzaMotor()

        self.depth = 0
        self.veces = 0

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.compruebaInput)
        self.timer.start(200)

    def compruebaInput(self):
        if not self.engine:
            return
        self.veces += 1
        if self.veces == 3:
            self.veces = 0
            if self.siPlay:
                mrm = self.engine.ac_estado()
                rm = mrm.rmBest()
                if rm and rm.depth > self.depth:
                    if mrm.li_rm:

                        cp = Position.Position()
                        cp.read_fen(self.fen)

                        self.liData = []

                        def tr(tp, mas=""):
                            self.liData.append((tp[0], "%.01f%%" % tp[1], "%s%s" % (mas, tp[2])))

                        tp = AnalisisIndexes.tp_gamestage(cp, mrm)
                        self.liData.append((tp[0], "%d" % tp[1], tp[2]))

                        pts = mrm.li_rm[0].centipawns_abs()
                        mas = ""
                        if pts:
                            w, b = _("White"), _("Black")
                            siW = "w" in self.fen
                            if pts > 0:
                                mas = w if siW else b
                            elif pts < 0:
                                mas = b if siW else w
                            mas += "-"

                        tr(AnalisisIndexes.tp_winprobability(cp, mrm), mas)
                        tr(AnalisisIndexes.tp_complexity(cp, mrm))
                        tr(AnalisisIndexes.tp_efficientmobility(cp, mrm))

                        tr(AnalisisIndexes.tp_narrowness(cp, mrm))
                        tr(AnalisisIndexes.tp_piecesactivity(cp, mrm))
                        tr(AnalisisIndexes.tp_exchangetendency(cp, mrm))

                        tp = AnalisisIndexes.tp_positionalpressure(cp, mrm)
                        self.liData.append((tp[0], "%d" % int(tp[1]), ""))

                        tr(AnalisisIndexes.tp_materialasymmetry(cp, mrm))

                    self.grid.refresh()
                    self.grid.resizeRowsToContents()

                QTUtil.refresh_gui()

        self.cpu.compruebaInput()

    def ponFlags(self):
        flags = self.windowFlags()
        if self.siTop:
            flags |= QtCore.Qt.WindowStaysOnTopHint
        else:
            flags &= ~QtCore.Qt.WindowStaysOnTopHint
        flags |= QtCore.Qt.WindowCloseButtonHint
        self.setWindowFlags(flags)
        self.tb.setAccionVisible(self.windowTop, not self.siTop)
        self.tb.setAccionVisible(self.windowBottom, self.siTop)
        self.show()

    def windowTop(self):
        self.siTop = True
        self.ponFlags()

    def windowBottom(self):
        self.siTop = False
        self.ponFlags()

    def terminar(self):
        self.finalizar()
        self.accept()

    def pause(self):
        self.siPlay = False
        self.tb.setPosVisible(1, True)
        self.tb.setPosVisible(2, False)
        self.stop()

    def play(self):
        self.siPlay = True
        self.tb.setPosVisible(1, False)
        self.tb.setPosVisible(2, True)
        self.ponFen(self.fen)

    def stop(self):
        self.siPlay = False
        self.engine.ac_final(0)

    def grid_num_datos(self, grid):
        return len(self.liData)

    def grid_dato(self, grid, fila, oColumna):
        key = oColumna.clave
        titulo, valor, info = self.liData[fila]
        if key == "titulo":
            return titulo

        elif key == "valor":
            return valor

        elif key == "info":
            return info

    def grid_bold(self, grid, fila, oColumna):
        return oColumna.clave in ("Titulo",)

    def lanzaMotor(self):
        self.nom_engine = self.kibitzer.name
        exe = self.kibitzer.path_exe
        args = self.kibitzer.args
        li_uci = self.kibitzer.liUCI
        return EngineRun.RunEngine(self.nom_engine, exe, li_uci, 1, priority=self.cpu.prioridad, args=args)

    def closeEvent(self, event):
        self.finalizar()

    def siAnalizar(self):
        siW = " w " in self.fen
        if not self.siPlay or (siW and (not self.is_white)) or ((not siW) and (not self.siNegras)):
            return False
        return True

    def color(self):
        menu = QTVarios.LCMenu(self)
        menu.opcion("blancas", _("White"), Iconos.PuntoNaranja())
        menu.opcion("negras", _("Black"), Iconos.PuntoNegro())
        menu.opcion("blancasnegras", "%s + %s" % (_("White"), _("Black")), Iconos.PuntoVerde())
        resp = menu.lanza()
        if resp:
            self.siNegras = True
            self.is_white = True
            if resp == "blancas":
                self.siNegras = False
            elif resp == "negras":
                self.is_white = False
            if self.siAnalizar():
                self.ponFen(self.fen)

    def finalizar(self):
        self.save_video()
        if self.engine:
            self.engine.ac_final(0)
            self.engine.close()
            self.engine = None
            self.siPlay = False

    def save_video(self):
        dic = {}

        pos = self.pos()
        dic["_POSICION_"] = "%d,%d" % (pos.x(), pos.y())

        tam = self.size()
        dic["_SIZE_"] = "%d,%d" % (tam.width(), tam.height())

        dic["SHOW_TABLERO"] = self.siShowTablero

        dic["SITOP"] = self.siTop

        self.grid.save_video(dic)

        self.cpu.save_video(dic)

    def restore_video(self, dicVideo):
        if dicVideo:
            wE, hE = QTUtil.tamEscritorio()
            x, y = dicVideo["_POSICION_"].split(",")
            x = int(x)
            y = int(y)
            if not (0 <= x <= (wE - 50)):
                x = 0
            if not (0 <= y <= (hE - 50)):
                y = 0
            self.move(x, y)
            if not ("_SIZE_" in dicVideo):
                w, h = self.width(), self.height()
                for k in dicVideo:
                    if k.startswith("_TAMA"):
                        w, h = dicVideo[k].split(",")
            else:
                w, h = dicVideo["_SIZE_"].split(",")
            w = int(w)
            h = int(h)
            if w > wE:
                w = wE
            elif w < 20:
                w = 20
            if h > hE:
                h = hE
            elif h < 20:
                h = 20
            self.resize(w, h)

    def orden_fen(self, fen):
        posicionInicial = Position.Position()
        posicionInicial.read_fen(fen)

        self.siW = posicionInicial.is_white

        self.tablero.setposition(posicionInicial)
        self.tablero.activaColor(self.siW)

        self.escribe("stop")

        game = Game.Game(fen=fen)
        self.engine.ac_inicio(game)

    def escribe(self, linea):
        self.engine.put_line(linea)

    def config_board(self):
        self.siShowTablero = not self.siShowTablero
        self.tablero.setVisible(self.siShowTablero)
        self.save_video()

    def set_position(self):
        cp = Position.Position()
        cp.read_fen(self.fen)
        resp = Voyager.voyager_position(self, cp)
        if resp is not None:
            self.ponFen(resp.fen())

    def ponFen(self, fen):
        self.history = []
        self.pon_fen_hist(fen)

    def pon_fen_hist(self, fen):
        if not self.history or self.history[-1] != fen:
            self.history.append(fen)
        self.liData = []
        self.depth = 0
        if fen:
            self.fen = fen
            if self.siAnalizar():
                self.orden_fen(fen)
            else:
                self.stop()
        else:
            self.stop()
        self.grid.refresh()

    def mensajero(self, from_sq, to_sq, promocion=""):
        FasterCode.set_fen(self.fen)
        if FasterCode.make_move(from_sq + to_sq + promocion):
            self.fen = FasterCode.get_fen()
            self.pon_fen_hist(self.fen)

    def takeback(self):
        if len(self.history) > 1:
            fen = self.history.pop()
            if fen == self.fen and self.history:
                fen = self.history.pop()
            self.pon_fen_hist(fen)
