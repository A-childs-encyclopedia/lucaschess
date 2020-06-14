from PySide2 import QtCore, QtWidgets

import Code
from Code import Game
from Code import XRun
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import Delegados
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import PantallaAnalisisParam
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.QT import Tablero
from Code.QT import Histogram


class WAnalisisGraph(QTVarios.WDialogo):
    def __init__(self, wowner, gestor, alm, show_analysis):
        titulo = _("Result of analysis")
        icono = Iconos.Estadisticas()
        extparam = "estadisticasv1"
        QTVarios.WDialogo.__init__(self, wowner, titulo, icono, extparam)
        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.Dialog
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )

        self.alm = alm
        self.procesador = gestor.procesador
        self.gestor = gestor
        self.configuracion = gestor.configuracion
        self.show_analysis = show_analysis
        self.colorWhite = QTUtil.qtColorRGB(231, 244, 254)

        def xcol():
            o_columns = Columnas.ListaColumnas()
            o_columns.nueva("NUM", _("N."), 50, centered=True)
            o_columns.nueva("MOVE", _("Move"), 120, centered=True, edicion=Delegados.EtiquetaPGN(True, True, True))
            o_columns.nueva("BEST", _("Best move"), 120, centered=True, edicion=Delegados.EtiquetaPGN(True, True, True))
            o_columns.nueva("DIF", _("Difference"), 80, centered=True)
            o_columns.nueva("PORC", "%", 80, centered=True)
            o_columns.nueva("ELO", _("Elo"), 80, centered=True)
            return o_columns

        self.dicLiJG = {"A": self.alm.lijg, "W": self.alm.lijgW, "B": self.alm.lijgB}
        gridAll = Grid.Grid(self, xcol(), siSelecFilas=True, xid="A")
        anchoGrid = gridAll.fixMinWidth()
        self.register_grid(gridAll)
        gridW = Grid.Grid(self, xcol(), siSelecFilas=True, xid="W")
        anchoGrid = max(gridW.fixMinWidth(), anchoGrid)
        self.register_grid(gridW)
        gridB = Grid.Grid(self, xcol(), siSelecFilas=True, xid="B")
        anchoGrid = max(gridB.fixMinWidth(), anchoGrid)
        self.register_grid(gridB)

        self.emIndexes = Controles.EM(self, alm.indexesHTML).soloLectura()
        pbSave = Controles.PB(self, _("Save to game comments"), self.saveIndexes, plano=False)
        pbSave.ponIcono(Iconos.Grabar())
        ly0 = Colocacion.H().control(pbSave).relleno()
        ly = Colocacion.V().control(self.emIndexes).otro(ly0).relleno()
        wIdx = QtWidgets.QWidget()
        wIdx.setLayout(ly)

        self.tabGrid = tabGrid = Controles.Tab()
        tabGrid.nuevaTab(gridAll, _("All moves"))
        tabGrid.nuevaTab(gridW, _("White"))
        tabGrid.nuevaTab(gridB, _("Black"))
        tabGrid.nuevaTab(wIdx, _("Indexes"))
        tabGrid.dispatchChange(self.tabChanged)
        self.tabActive = 0

        config_board = Code.configuracion.config_board("ANALISISGRAPH", 48)
        self.tablero = Tablero.Tablero(self, config_board)
        self.tablero.crea()
        self.tablero.ponerPiezasAbajo(alm.is_white_bottom)
        self.tablero.dispatchSize(self.tableroSizeChanged)

        # self.capturas = WCapturas.CapturaLista(self, self.tablero)
        ly_tc = Colocacion.H().control(self.tablero)
            # .control(self.capturas)

        self.rbShowValues = Controles.RB(self, _("Values"), rutina=self.cambiadoShow).activa(True)
        self.rbShowElo = Controles.RB(self, _("Elo performance"), rutina=self.cambiadoShow)
        self.chbShowLostPoints = Controles.CHB(self, _("Show lost points"), self.getShowLostPoints()).capturaCambiado(
            self, self.showLostPointsChanged
        )
        ly_rb = (
            Colocacion.H()
            .espacio(40)
            .control(self.rbShowValues)
            .espacio(20)
            .control(self.rbShowElo)
            .espacio(30)
            .control(self.chbShowLostPoints)
            .relleno(1)
        )

        layout = Colocacion.G()
        layout.controlc(tabGrid, 0, 0)
        layout.otroc(ly_rb, 1, 0)
        layout.otroc(ly_tc, 0, 1, numFilas=2)

        Controles.Tab().ponPosicion("W")
        ancho = self.tablero.width() + anchoGrid
        self.htotal = [
            Histogram.Histogram(self, alm.hgame, gridAll, ancho, True),
            Histogram.Histogram(self, alm.hwhite, gridW, ancho, True),
            Histogram.Histogram(self, alm.hblack, gridB, ancho, True),
            Histogram.Histogram(self, alm.hgame, gridAll, ancho, False, alm.eloT),
            Histogram.Histogram(self, alm.hwhite, gridW, ancho, False, alm.eloW),
            Histogram.Histogram(self, alm.hblack, gridB, ancho, False, alm.eloB),
        ]
        lh = Colocacion.V()
        for x in range(6):
            lh.control(self.htotal[x])
            if x:
                self.htotal[x].hide()

        layout.otroc(lh, 2, 0, 1, 3)
        self.setLayout(layout)

        self.restore_video()

        gridAll.gotop()
        gridB.gotop()
        gridW.gotop()
        self.grid_boton_izquierdo(gridAll, 0, None)
        th = self.tablero.height()
        self.tabGrid.setFixedHeight(th)
        self.adjustSize()
        self.emIndexes.setFixedHeight(th - 72)

    def valorShowLostPoints(self):
        # Llamada from_sq histogram
        return self.chbShowLostPoints.valor()

    def showLostPointsChanged(self):
        dic = {"SHOWLOSTPOINTS": self.valorShowLostPoints()}
        self.configuracion.escVariables("ANALISIS_GRAPH", dic)
        self.cambiadoShow()

    def getShowLostPoints(self):
        dic = self.configuracion.leeVariables("ANALISIS_GRAPH")
        return dic.get("SHOWLOSTPOINTS", True) if dic else True

    def cambiadoShow(self):
        self.tabChanged(self.tabGrid.currentIndex())

    def tableroSizeChanged(self):
        th = self.tablero.height()
        self.tabGrid.setFixedHeight(th)
        self.emIndexes.setFixedHeight(th - 72)
        self.adjustSize()
        self.cambiadoShow()

    def tabChanged(self, ntab):
        QtWidgets.QApplication.processEvents()
        tab_vis = 0 if ntab == 3 else ntab
        if self.rbShowElo.isChecked():
            tab_vis += 3
        for n in range(6):
            self.htotal[n].setVisible(False)
        self.htotal[tab_vis].setVisible(True)
        self.adjustSize()
        self.tabActive = ntab

    def grid_cambiado_registro(self, grid, fila, columna):
        self.grid_boton_izquierdo(grid, fila, columna)

    def saveIndexes(self):
        self.gestor.game.set_first_comment(self.alm.indexesRAW)
        QTUtil2.mensajeTemporal(self, _("Saved"), 1.8)

    def grid_boton_izquierdo(self, grid, fila, columna):
        self.tablero.quitaFlechas()
        move = self.dicLiJG[grid.id][fila]
        self.tablero.ponPosicion(move.position)
        mrm, pos = move.analysis
        rm = mrm.li_rm[pos]
        self.tablero.ponFlechaSC(rm.from_sq, rm.to_sq)
        rm = mrm.li_rm[0]
        self.tablero.creaFlechaMulti(rm.movimiento(), False)
        grid.setFocus()
        ta = self.tabActive if self.tabActive < 3 else 0
        self.htotal[ta].setPointActive(fila)
        self.htotal[ta + 3].setPointActive(fila)

        # dic, is_white = move.position.capturas()
        # self.capturas.pon(dic)

    def grid_doble_click(self, grid, fila, columna):
        move = self.dicLiJG[grid.id][fila]
        mrm, pos = move.analysis
        self.show_analysis(
            self.procesador,
            self.procesador.xtutor,
            move,
            self.tablero.is_white_bottom,
            999999,
            pos,
            main_window=self,
            must_save=False,
        )

    def grid_tecla_control(self, grid, k, siShift, siControl, siAlt):
        nrecno = grid.recno()
        if k in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self.grid_doble_click(grid, nrecno, None)
        elif k == QtCore.Qt.Key_Right:
            if nrecno + 1 < self.grid_num_datos(grid):
                grid.goto(nrecno + 1, 0)
        elif k == QtCore.Qt.Key_Left:
            if nrecno > 0:
                grid.goto(nrecno - 1, 0)

    def grid_color_fondo(self, grid, fila, oColumna):
        if grid.id == "A":
            move = self.alm.lijg[fila]
            return self.colorWhite if move.xsiW else None
        return None

    def grid_alineacion(self, grid, fila, oColumna):
        if grid.id == "A":
            move = self.alm.lijg[fila]
            return "i" if move.xsiW else "d"
        return None

    def grid_num_datos(self, grid):
        return len(self.dicLiJG[grid.id])

    def grid_dato(self, grid, fila, oColumna):
        columna = oColumna.clave
        move = self.dicLiJG[grid.id][fila]
        if columna == "NUM":
            return " %s " % move.xnum
        elif columna in ("MOVE", "BEST"):
            mrm, pos = move.analysis
            rm = mrm.li_rm[pos if columna == "MOVE" else 0]
            pv1 = rm.pv.split(" ")[0]
            from_sq = pv1[:2]
            to_sq = pv1[2:4]
            promotion = pv1[4] if len(pv1) == 5 else None
            txt = rm.abrTextoBase()
            if txt:
                txt = " (%s)" % txt
            return move.position_before.pgn(from_sq, to_sq, promotion) + txt
        elif columna == "DIF":
            mrm, pos = move.analysis
            rm = mrm.li_rm[0]
            rm1 = mrm.li_rm[pos]
            pts = rm.puntosABS_5() - rm1.puntosABS_5()
            pts /= 100.0
            return "%0.2f" % pts
        elif columna == "PORC":
            return "%3d%%" % move.porcentaje
        elif columna == "ELO":
            return "%3d" % move.elo

    def closeEvent(self, event):
        self.save_video()


def showGraph(wowner, gestor, alm, show_analysis):
    w = WAnalisisGraph(wowner, gestor, alm, show_analysis)
    w.exec_()


class WMuestra(QtWidgets.QWidget):
    def __init__(self, owner, um):
        super(WMuestra, self).__init__(owner)

        self.um = um
        self.owner = owner

        self.time_engine = um.time_engine()
        self.time_label = um.time_label()

        self.tablero = owner.tablero

        self.lbMotorM = Controles.LB(self, self.time_engine).alinCentrado().ponTipoLetra(puntos=9, peso=75)
        self.lbTiempoM = Controles.LB(self, self.time_label).alinCentrado().ponTipoLetra(puntos=9, peso=75)
        self.dicFonts = {True: "blue", False: "grey"}

        self.btCancelar = Controles.PB(self, "", self.cancelar).ponIcono(Iconos.X())

        self.lbPuntuacion = owner.lbPuntuacion
        self.lbMotor = owner.lbMotor
        self.lbTiempo = owner.lbTiempo
        self.lbPGN = owner.lbPGN

        self.list_rm_name = um.list_rm_name  # rm, name, centipawns
        self.siTiempoActivo = False

        self.colorNegativo = QTUtil.qtColorRGB(255, 0, 0)
        self.colorImpares = QTUtil.qtColorRGB(231, 244, 254)
        o_columns = Columnas.ListaColumnas()
        self.si_figurines_pgn = Code.configuracion.x_pgn_withfigurines
        o_columns.nueva(
            "JUGADAS",
            "%d %s" % (len(self.list_rm_name), _("Moves")),
            120,
            centered=True,
            edicion=Delegados.EtiquetaPGN(um.move.is_white() if self.si_figurines_pgn else None),
        )
        self.wrm = Grid.Grid(self, o_columns, siLineas=False)

        self.wrm.tipoLetra(puntos=Code.configuracion.x_pgn_fontpoints)
        nAncho = self.wrm.anchoColumnas() + 20
        self.wrm.setFixedWidth(nAncho)
        self.wrm.goto(self.um.pos_selected, 0)

        # Layout
        ly2 = Colocacion.H().relleno().control(self.lbTiempoM).relleno().control(self.btCancelar)
        layout = Colocacion.V().control(self.lbMotorM).otro(ly2).control(self.wrm)

        self.setLayout(layout)

        self.wrm.setFocus()

    def activa(self, siActivar):
        color = self.dicFonts[siActivar]
        self.lbMotorM.ponColorN(color)
        self.lbTiempoM.ponColorN(color)
        self.btCancelar.setEnabled(not siActivar)
        self.siTiempoActivo = False

        if siActivar:
            self.lbMotor.ponTexto(self.time_engine)
            self.lbTiempo.ponTexto(self.time_label)

    def cancelar(self):
        self.owner.borrarMuestra(self.um)

    def cambiadoRM(self, fila):
        self.um.set_pos_rm_active(fila)
        self.lbPuntuacion.ponTexto(self.um.score_active())

        self.lbPGN.ponTexto(self.um.pgn_active())

        self.ponTablero()
        self.owner.adjustSize()
        QTUtil.refresh_gui()

    def ponTablero(self):
        position, from_sq, to_sq = self.um.active_position()
        self.tablero.ponPosicion(position)
        if from_sq:
            self.tablero.ponFlechaSC(from_sq, to_sq)

    def grid_num_datos(self, grid):
        return len(self.list_rm_name)

    def grid_boton_izquierdo(self, grid, fila, columna):
        self.cambiadoRM(fila)
        self.owner.activaMuestra(self.um)

    def grid_boton_derecho(self, grid, fila, columna, modificadores):
        self.cambiadoRM(fila)

    def grid_bold(self, grid, fila, columna):
        return self.um.is_selected(fila)

    def grid_dato(self, grid, fila, oColumna):
        return self.list_rm_name[fila][1]

    def grid_color_texto(self, grid, fila, oColumna):
        rm = self.list_rm_name[fila][0]
        return None if rm.centipawns_abs() >= 0 else self.colorNegativo

    def grid_color_fondo(self, grid, fila, oColumna):
        if fila % 2 == 1:
            return self.colorImpares
        else:
            return None

    def situate(self, recno):
        if 0 <= recno < len(self.list_rm_name):
            self.wrm.goto(recno, 0)
            self.cambiadoRM(recno)
            self.owner.activaMuestra(self.um)

    def abajo(self):
        self.situate(self.wrm.recno() + 1)

    def primero(self):
        self.situate(0)

    def arriba(self):
        self.situate(self.wrm.recno() - 1)

    def ultimo(self):
        self.situate(len(self.list_rm_name) - 1)

    def process_toolbar(self, accion):
        accion = accion[5:]
        if accion in ("Adelante", "Atras", "Inicio", "Final"):
            self.um.change_mov_active(accion)
            self.ponTablero()
        elif accion == "Libre":
            self.um.external_analysis(self.owner, self.owner.is_white)
        elif accion == "Tiempo":
            self.lanzaTiempo()
        elif accion == "Grabar":
            self.grabar()
        elif accion == "GrabarTodos":
            self.grabarTodos()
        elif accion == "Jugar":
            self.jugarPosicion()
        elif accion == "FEN":
            QTUtil.ponPortapapeles(self.um.fen_active())
            QTUtil2.message_bold(self, _("FEN is in clipboard"))

    def jugarPosicion(self):
        position, from_sq, to_sq = self.um.active_base_position()
        fen = position.fen()

        XRun.run_lucas("-play", fen)

    def lanzaTiempo(self):
        self.siTiempoActivo = not self.siTiempoActivo
        if self.siTiempoActivo:
            self.um.change_mov_active("Inicio")
            self.ponTablero()
            QtCore.QTimer.singleShot(400, self.siguienteTiempo)

    def siguienteTiempo(self):
        if self.siTiempoActivo:
            self.um.change_mov_active("Adelante")
            self.ponTablero()
            if self.um.is_final_position():
                self.siTiempoActivo = False
            else:
                QtCore.QTimer.singleShot(1400, self.siguienteTiempo)

    def grabar(self):
        menu = QTVarios.LCMenu(self)
        menu.opcion(True, _("Complete variation"), Iconos.PuntoVerde())
        menu.separador()
        menu.opcion(False, _("Only the first move"), Iconos.PuntoRojo())
        resp = menu.lanza()
        if resp is None:
            return
        self.um.save_base(self.um.game, self.um.rm, resp)
        self.um.put_view_gestor()

    def grabarTodos(self):
        menu = QTVarios.LCMenu(self)
        menu.opcion(True, _("Complete variations"), Iconos.PuntoVerde())
        menu.separador()
        menu.opcion(False, _("Only the first move of each variation"), Iconos.PuntoRojo())
        resp = menu.lanza()
        if resp:
            for pos, tp in enumerate(self.um.list_rm):
                rm = tp[0]
                game = Game.Game(self.um.move.position_before)
                game.read_pv(rm.pv)
                self.um.save_base(game, rm, resp)
            self.um.put_view_gestor()


class WAnalisis(QTVarios.WDialogo):
    def __init__(self, tb_analysis, ventana, is_white, siLibre, must_save, muestraInicial):
        titulo = _("Analysis")
        icono = Iconos.Tutor()
        extparam = "analysis"

        QTVarios.WDialogo.__init__(self, ventana, titulo, icono, extparam)

        self.tb_analysis = tb_analysis
        self.muestraActual = None

        configuracion = Code.configuracion
        config_board = configuracion.config_board("ANALISIS", 48)
        self.siLibre = siLibre
        self.must_save = must_save
        self.is_white = is_white

        tbWork = QTVarios.LCTB(self, tamIcon=24)
        tbWork.new(_("Close"), Iconos.MainMenu(), self.terminar)
        tbWork.new(_("New"), Iconos.NuevoMas(), self.crear)

        self.tablero = Tablero.Tablero(self, config_board)
        self.tablero.crea()
        self.tablero.ponerPiezasAbajo(is_white)

        self.lbMotor = Controles.LB(self).alinCentrado()
        self.lbTiempo = Controles.LB(self).alinCentrado()
        self.lbPuntuacion = (
            Controles.LB(self).alinCentrado().ponTipoLetra(puntos=configuracion.x_pgn_fontpoints, peso=75)
        )
        self.lbPGN = Controles.LB(self).ponWrap().ponTipoLetra(puntos=configuracion.x_pgn_fontpoints)

        self.setStyleSheet(
            "QStatusBar::item { border-style: outset; border-width: 1px; border-color: LightSlateGray ;}"
        )

        liMasAcciones = (("FEN:%s" % _("Copy to clipboard"), "MoverFEN", Iconos.Clipboard()),)
        lytb, self.tb = QTVarios.lyBotonesMovimiento(
            self,
            "",
            siLibre=siLibre,
            must_save=must_save,
            siGrabarTodos=must_save,
            siJugar=tb_analysis.max_recursion > 10,
            liMasAcciones=liMasAcciones,
        )

        lyTabl = Colocacion.H().relleno().control(self.tablero).relleno()

        lyMotor = Colocacion.H().control(self.lbPuntuacion).relleno().control(self.lbMotor).control(self.lbTiempo)

        lyV = Colocacion.V()
        lyV.control(tbWork)
        lyV.otro(lyTabl)
        lyV.otro(lytb)
        lyV.otro(lyMotor)
        lyV.control(self.lbPGN)
        lyV.relleno()

        wm = WMuestra(self, muestraInicial)
        muestraInicial.wmu = wm

        # Layout
        self.ly = Colocacion.H().margen(10)
        self.ly.otro(lyV)
        self.ly.control(wm)

        lyM = Colocacion.H().margen(0).otro(self.ly).relleno()

        layout = Colocacion.V()
        layout.otro(lyM)
        layout.margen(3)
        layout.setSpacing(1)
        self.setLayout(layout)

        self.restore_video(siTam=False)
        wm.cambiadoRM(muestraInicial.pos_selected)
        self.activaMuestra(muestraInicial)

    def keyPressEvent(self, event):
        k = event.key()

        if k == 16777237:  # abajo
            self.muestraActual.wmu.abajo()
        elif k == 16777235:  # arriba
            self.muestraActual.wmu.arriba()
        elif k == 16777234:  # izda
            self.muestraActual.wmu.process_toolbar("MoverAtras")
        elif k == 16777236:  # dcha
            self.muestraActual.wmu.process_toolbar("MoverAdelante")
        elif k == 16777232:  # inicio
            self.muestraActual.wmu.process_toolbar("MoverInicio")
        elif k == 16777233:  # final
            self.muestraActual.wmu.process_toolbar("MoverFinal")
        elif k == 16777238:  # avpag
            self.muestraActual.wmu.primero()
        elif k == 16777239:  # dnpag
            self.muestraActual.wmu.ultimo()
        elif k == 16777220:  # enter
            self.muestraActual.wmu.process_toolbar("MoverLibre")
        elif k == 16777216:  # esc
            self.terminar()

    def closeEvent(self, event):  # Cierre con X
        self.terminar(False)

    def terminar(self, siAccept=True):
        for una in self.tb_analysis.li_tabs_analysis:
            una.wmu.siTiempoActivo = False
        self.save_video()
        if siAccept:
            self.accept()
        else:
            self.reject()

    def activaMuestra(self, um):
        self.muestraActual = um
        for una in self.tb_analysis.li_tabs_analysis:
            if hasattr(una, "wmu"):
                una.wmu.activa(una == um)

    def crearMuestra(self, um):
        wm = WMuestra(self, um)
        self.ly.control(wm)
        wm.show()

        um.set_wmu(wm)

        self.activaMuestra(um)

        wm.grid_boton_izquierdo(wm.wrm, um.pos_rm_active, 0)

        return wm

    def borrarMuestra(self, um):
        um.desactiva()
        self.adjustSize()
        QTUtil.refresh_gui()

    def process_toolbar(self):
        clave = self.sender().clave
        if clave == "terminar":
            self.terminar()
            self.accept()
        elif clave == "crear":
            self.crear()
        else:
            self.muestraActual.wmu.process_toolbar(clave)

    def start_clock(self, funcion):
        if not hasattr(self, "timer"):
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(funcion)
        self.timer.start(1000)

    def stop_clock(self):
        if hasattr(self, "timer"):
            self.timer.stop()
            delattr(self, "timer")

    def crear(self):
        alm = PantallaAnalisisParam.paramAnalisis(self, Code.configuracion, False, siTodosMotores=True)
        if alm:
            um = self.tb_analysis.create_show(self, alm)
            self.crearMuestra(um)


class WAnalisisVariantes(QtWidgets.QDialog):
    def __init__(self, oBase, ventana, segundosPensando, is_white, cPuntos, max_recursion):
        super(WAnalisisVariantes, self).__init__(ventana)

        self.oBase = oBase

        # Creamos los controles
        self.setWindowTitle(_("Variations"))

        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.Dialog | QtCore.Qt.WindowMinimizeButtonHint)
        self.setWindowIcon(Iconos.Tutor())

        f = Controles.TipoLetra(puntos=12, peso=75)
        flb = Controles.TipoLetra(puntos=10)

        lbPuntuacionAnterior = Controles.LB(self, cPuntos).alinCentrado().ponFuente(flb)
        self.lbPuntuacionNueva = Controles.LB(self).alinCentrado().ponFuente(flb)

        config_board = Code.configuracion.config_board("ANALISISVARIANTES", 32)
        self.tablero = Tablero.Tablero(self, config_board)
        self.tablero.crea()
        self.tablero.ponerPiezasAbajo(is_white)

        self.tableroT = Tablero.Tablero(self, config_board)
        self.tableroT.crea()
        self.tableroT.ponerPiezasAbajo(is_white)

        btTerminar = Controles.PB(self, _("Close"), self.close).ponPlano(False)
        btReset = Controles.PB(self, _("Another change"), oBase.reset).ponIcono(Iconos.MoverLibre()).ponPlano(False)
        liMasAcciones = (("FEN:%s" % _("Copy to clipboard"), "MoverFEN", Iconos.Clipboard()),)
        lytbTutor, self.tb = QTVarios.lyBotonesMovimiento(
            self, "", siLibre=max_recursion > 0, liMasAcciones=liMasAcciones
        )
        self.max_recursion = max_recursion - 1

        self.segundos, lbSegundos = QTUtil2.spinBoxLB(
            self, segundosPensando, 1, 999, maxTam=40, etiqueta=_("Second(s)")
        )

        # Creamos los layouts

        lyVariacion = Colocacion.V().control(lbPuntuacionAnterior).control(self.tablero)
        gbVariacion = Controles.GB(self, _("Proposed change"), lyVariacion).ponFuente(f).alinCentrado()

        lyTutor = Colocacion.V().control(self.lbPuntuacionNueva).control(self.tableroT)
        gbTutor = Controles.GB(self, _("Tutor's prediction"), lyTutor).ponFuente(f).alinCentrado()

        lyBT = Colocacion.H().control(btTerminar).control(btReset).relleno().control(lbSegundos).control(self.segundos)

        layout = Colocacion.G().control(gbVariacion, 0, 0).control(gbTutor, 0, 1)
        layout.otro(lyBT, 1, 0).otro(lytbTutor, 1, 1)

        self.setLayout(layout)

        self.move(ventana.x() + 20, ventana.y() + 20)

    def dameSegundos(self):
        return int(self.segundos.value())

    def ponPuntuacion(self, pts):
        self.lbPuntuacionNueva.ponTexto(pts)

    def process_toolbar(self):
        self.oBase.process_toolbar(self.sender().clave, self.max_recursion)

    def start_clock(self, funcion):
        if not hasattr(self, "timer"):
            self.timer = QtCore.QTimer(self)
            self.timer.timeout.connect(funcion)
        self.timer.start(1000)

    def stop_clock(self):
        if hasattr(self, "timer"):
            self.timer.stop()
            delattr(self, "timer")

    def closeEvent(self, event):  # Cierre con X
        self.stop_clock()

    def keyPressEvent(self, event):
        k = event.key()
        if k == 16777237:  # abajo
            clave = "MoverAtras"
        elif k == 16777235:  # arriba
            clave = "MoverAdelante"
        elif k == 16777234:  # izda
            clave = "MoverAtras"
        elif k == 16777236:  # dcha
            clave = "MoverAdelante"
        elif k == 16777232:  # inicio
            clave = "MoverInicio"
        elif k == 16777233:  # final
            clave = "MoverFinal"
        elif k == 16777216:  # esc
            self.stop_clock()
            self.accept()
        else:
            return
        self.oBase.process_toolbar(clave, self.max_recursion)
