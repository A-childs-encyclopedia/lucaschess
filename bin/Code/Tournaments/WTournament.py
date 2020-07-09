import os

from PySide2 import QtWidgets, QtCore
from Code.Constantes import FEN_INITIAL

from Code import Game
from Code.Polyglots import Books
from Code.Engines import Engines, WEngines
from Code import Position
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import FormLayout
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import PantallaSavePGN
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.Tournaments import Tournament
from Code import Util
import Code
from Code import XRun
from Code.QT import Voyager

GRID_ALIAS, GRID_VALUES, GRID_GAMES_QUEUED, GRID_GAMES_FINISHED, GRID_RESULTS = range(5)


class WTournament(QTVarios.WDialogo):
    def __init__(self, wParent, nombre_torneo):

        torneo = self.torneo = Tournament.Tournament(nombre_torneo)

        titulo = nombre_torneo
        icono = Iconos.Torneos()
        extparam = "untorneo_v1"
        QTVarios.WDialogo.__init__(self, wParent, titulo, icono, extparam)

        self.configuracion = Code.configuracion

        # Datos

        self.liEnActual = []
        self.xjugar = None
        self.liResult = None
        self.last_change = Util.today()
        self.li_results = []

        # Toolbar
        tb = Controles.TBrutina(self, tamIcon=24)
        tb.new(_("Close"), Iconos.MainMenu(), self.terminar)
        tb.new(_("Launch a worker"), Iconos.Lanzamiento(), self.gm_launch)

        # Tabs
        self.tab = tab = Controles.Tab()

        # Tab-configuracion --------------------------------------------------
        w = QtWidgets.QWidget()

        # Adjudicator
        lb_resign = Controles.LB(self, "%s (%s): " % (_("Minimum centipawns to assign winner"), _("0=disable")))
        self.ed_resign = Controles.ED(self).tipoInt(torneo.resign()).anchoFijo(30)
        bt_resign = Controles.PB(self, "", rutina=self.borra_resign).ponIcono(Iconos.Reciclar())

        # Draw-plys
        lbDrawMinPly = Controles.LB(self, "%s (%s): " % (_("Minimum moves to assign draw"), _("0=disable")))
        self.sbDrawMinPly = Controles.SB(self, torneo.drawMinPly(), 20, 1000)
        # Draw-puntos
        lb_draw_range = Controles.LB(self, _("Maximum centipawns to assign draw") + ": ")
        self.ed_draw_range = Controles.ED(self).tipoInt(torneo.drawRange()).anchoFijo(30)
        bt_draw_range = Controles.PB(self, "", rutina=self.borra_draw_range).ponIcono(Iconos.Reciclar())

        # adjudicator
        self.liMotores = self.configuracion.comboMotoresMultiPV10()
        self.cbJmotor, self.lbJmotor = QTUtil2.comboBoxLB(self, self.liMotores, torneo.adjudicator(), _("Engine"))
        self.edJtiempo = Controles.ED(self).tipoFloat().ponFloat(1.0).anchoFijo(50).ponFloat(torneo.adjudicator_time())
        self.lbJtiempo = Controles.LB2P(self, _("Time in seconds"))
        layout = Colocacion.G()
        layout.controld(self.lbJmotor, 3, 0).control(self.cbJmotor, 3, 1)
        layout.controld(self.lbJtiempo, 4, 0).control(self.edJtiempo, 4, 1)
        self.gbJ = Controles.GB(self, _("Adjudicator"), layout)
        self.gbJ.setCheckable(True)
        self.gbJ.setChecked(torneo.adjudicator_active())

        lbBook = Controles.LB(self, _("Opening book") + ": ")
        fvar = self.configuracion.ficheroBooks
        self.listaLibros = Books.ListaLibros()
        self.listaLibros.restore_pickle(fvar)
        # Comprobamos que todos esten accesibles
        self.listaLibros.comprueba()
        li = [(x.name, x.path) for x in self.listaLibros.lista]
        li.insert(0, ("* " + _("None"), "-"))
        self.cbBooks = Controles.CB(self, li, torneo.book())
        btNuevoBook = Controles.PB(self, "", self.nuevoBook, plano=False).ponIcono(Iconos.Nuevo(), tamIcon=16)
        lyBook = Colocacion.H().control(self.cbBooks).control(btNuevoBook).relleno()

        lbBookDepth = Controles.LB(self, _("Max depth of book (0=Maximum)") + ": ")
        self.sbBookDepth = Controles.SB(self, torneo.bookDepth(), 0, 200)

        # Posicion inicial
        lbFEN = Controles.LB(self, _("Initial position") + ": ")
        self.fen = torneo.fen()
        self.btPosicion = Controles.PB(self, " " * 5 + _("Change") + " " * 5, self.posicionEditar).ponPlano(False)
        self.btPosicionQuitar = Controles.PB(self, "", self.posicionQuitar).ponIcono(Iconos.Motor_No())
        self.btPosicionPegar = (
            Controles.PB(self, "", self.posicionPegar).ponIcono(Iconos.Pegar16()).ponToolTip(_("Paste FEN position"))
        )
        lyFEN = (
            Colocacion.H()
            .control(self.btPosicionQuitar)
            .control(self.btPosicion)
            .control(self.btPosicionPegar)
            .relleno()
        )

        # Norman Pollock
        lbNorman = Controles.LB(
            self,
            '%s(<a href="https://komodochess.com/pub/40H-pgn-utilities">?</a>): '
            % _("Initial position from Norman Pollock openings database"),
        )
        self.chbNorman = Controles.CHB(self, " ", self.torneo.norman())

        # Layout
        layout = Colocacion.G()
        ly_res = Colocacion.H().control(self.ed_resign).control(bt_resign).relleno()
        ly_dra = Colocacion.H().control(self.ed_draw_range).control(bt_draw_range).relleno()
        layout.controld(lb_resign, 0, 0).otro(ly_res, 0, 1)
        layout.controld(lbDrawMinPly, 1, 0).control(self.sbDrawMinPly, 1, 1)
        layout.controld(lb_draw_range, 2, 0).otro(ly_dra, 2, 1)
        layout.controld(lbBook, 3, 0).otro(lyBook, 3, 1)
        layout.controld(lbBookDepth, 4, 0).control(self.sbBookDepth, 4, 1)
        layout.controld(lbFEN, 5, 0).otro(lyFEN, 5, 1)
        layout.controld(lbNorman, 6, 0).control(self.chbNorman, 6, 1)
        layoutV = Colocacion.V().relleno().otro(layout).control(self.gbJ).relleno()
        layoutH = Colocacion.H().relleno().otro(layoutV).relleno()

        # Creamos
        w.setLayout(layoutH)
        tab.nuevaTab(w, _("Configuration"))

        # Tab-engines --------------------------------------------------
        self.splitterEngines = QtWidgets.QSplitter(self)
        self.register_splitter(self.splitterEngines, "engines")
        # TB
        li_acciones = [
            (_("New"), Iconos.TutorialesCrear(), self.enNuevo),
            None,
            (_("Modify"), Iconos.Modificar(), self.enModificar),
            None,
            (_("Remove"), Iconos.Borrar(), self.enBorrar),
            None,
            (_("Copy"), Iconos.Copiar(), self.enCopiar),
            None,
            (_("Import"), Iconos.MasDoc(), self.enImportar),
            None,
        ]
        tbEnA = Controles.TBrutina(self, li_acciones, tamIcon=16, style=QtCore.Qt.ToolButtonTextBesideIcon)

        # Grid engine
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUM", _("N."), 50, centered=True)
        o_columns.nueva("ALIAS", _("Alias"), 209)
        self.gridEnginesAlias = Grid.Grid(self, o_columns, siSelecFilas=True, siSeleccionMultiple=True, xid=GRID_ALIAS)
        self.register_grid(self.gridEnginesAlias)

        w = QtWidgets.QWidget()
        ly = Colocacion.V().control(self.gridEnginesAlias).margen(0)
        w.setLayout(ly)
        self.splitterEngines.addWidget(w)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("CAMPO", _("Label"), 200, siDerecha=True)
        o_columns.nueva("VALOR", _("Value"), 286)
        self.gridEnginesValores = Grid.Grid(self, o_columns, siSelecFilas=False, xid=GRID_VALUES)
        self.register_grid(self.gridEnginesValores)

        w = QtWidgets.QWidget()
        ly = Colocacion.V().control(self.gridEnginesValores).margen(0)
        w.setLayout(ly)
        self.splitterEngines.addWidget(w)

        self.splitterEngines.setSizes([250, 520])  # por defecto

        w = QtWidgets.QWidget()
        ly = Colocacion.V().control(tbEnA).control(self.splitterEngines)
        w.setLayout(ly)
        tab.nuevaTab(w, _("Engines"))

        # Creamos

        # Tab-games queued--------------------------------------------------
        w = QtWidgets.QWidget()
        # TB
        li_acciones = [
            (_("New"), Iconos.TutorialesCrear(), self.gm_crear_queued),
            None,
            (_("Remove"), Iconos.Borrar(), self.gm_borrar_queued),
            None,
        ]
        tbEnG = Controles.TBrutina(self, li_acciones, tamIcon=16, style=QtCore.Qt.ToolButtonTextBesideIcon)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUM", _("N."), 50, centered=True)
        o_columns.nueva("WHITE", _("White"), 190, centered=True)
        o_columns.nueva("BLACK", _("Black"), 190, centered=True)
        o_columns.nueva("TIME", _("Time"), 170, centered=True)
        # o_columns.nueva("STATE", _("State"), 190, centered=True)
        self.gridGamesQueued = Grid.Grid(
            self, o_columns, siSelecFilas=True, siSeleccionMultiple=True, xid=GRID_GAMES_QUEUED
        )
        self.register_grid(self.gridGamesQueued)
        # Layout
        layout = Colocacion.V().control(tbEnG).control(self.gridGamesQueued)

        # Creamos
        w.setLayout(layout)
        tab.nuevaTab(w, _("Games queued"))

        # Tab-games terminados--------------------------------------------------
        w = QtWidgets.QWidget()
        # TB
        li_acciones = [
            (_("Remove"), Iconos.Borrar(), self.gm_borrar_finished),
            None,
            (_("Show"), Iconos.PGN(), self.gm_show_finished),
            None,
            (_("Save") + "(%s)" % _("PGN"), Iconos.GrabarComo(), self.gm_save_pgn),
            None,
        ]
        tbEnGt = Controles.TBrutina(self, li_acciones, tamIcon=16, style=QtCore.Qt.ToolButtonTextBesideIcon)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUM", _("N."), 50, centered=True)
        o_columns.nueva("WHITE", _("White"), 190, centered=True)
        o_columns.nueva("BLACK", _("Black"), 190, centered=True)
        o_columns.nueva("TIME", _("Time"), 170, centered=True)
        o_columns.nueva("RESULT", _("Result"), 190, centered=True)
        self.gridGamesFinished = Grid.Grid(
            self, o_columns, siSelecFilas=True, siSeleccionMultiple=True, xid=GRID_GAMES_FINISHED
        )
        self.register_grid(self.gridGamesFinished)
        # Layout
        layout = Colocacion.V().control(tbEnGt).control(self.gridGamesFinished)

        # Creamos
        w.setLayout(layout)
        tab.nuevaTab(w, _("Games finished"))

        # Tab-resultado --------------------------------------------------
        w = QtWidgets.QWidget()

        # Grid
        wh = _("W")
        bl = _("B")
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUM", _("N."), 35, centered=True)
        o_columns.nueva("ENGINE", _("Engine"), 120, centered=True)
        o_columns.nueva("SCORE", _("Score") + "%", 50, centered=True)
        o_columns.nueva("WIN", _("Wins"), 50, centered=True)
        o_columns.nueva("DRAW", _("Draws"), 50, centered=True)
        o_columns.nueva("LOST", _("Losses"), 50, centered=True)
        o_columns.nueva("WIN-WHITE", "%s %s" % (wh, _("Wins")), 60, centered=True)
        o_columns.nueva("DRAW-WHITE", "%s %s" % (wh, _("Draws")), 60, centered=True)
        o_columns.nueva("LOST-WHITE", "%s %s" % (wh, _("Losses")), 60, centered=True)
        o_columns.nueva("WIN-BLACK", "%s %s" % (bl, _("Wins")), 60, centered=True)
        o_columns.nueva("DRAW-BLACK", "%s %s" % (bl, _("Draws")), 60, centered=True)
        o_columns.nueva("LOST-BLACK", "%s %s" % (bl, _("Losses")), 60, centered=True)
        o_columns.nueva("GAMES", _("Games"), 50, centered=True)
        self.gridResults = Grid.Grid(self, o_columns, siSelecFilas=True, xid=GRID_RESULTS)
        self.register_grid(self.gridResults)

        self.qtColor = {
            "WHITE": QTUtil.qtColorRGB(255, 250, 227),
            "BLACK": QTUtil.qtColorRGB(221, 255, 221),
            "SCORE": QTUtil.qtColorRGB(170, 170, 170),
        }

        # Layout
        layout = Colocacion.V().control(self.gridResults)

        # Creamos
        w.setLayout(layout)
        tab.nuevaTab(w, _("Results"))

        # Layout
        # tab.setposition("W")
        layout = Colocacion.V().control(tb).espacio(-3).control(tab).margen(2)
        self.setLayout(layout)

        self.restore_video(siTam=True, anchoDefecto=800, altoDefecto=430)

        self.gridEnginesAlias.gotop()

        self.ed_resign.setFocus()

        self.muestraPosicion()

        QtCore.QTimer.singleShot(5000, self.comprueba_cambios)
        self.rotulos_tabs()

    def closeEvent(self, event):
        self.cerrar()

    def terminar(self):
        self.cerrar()
        self.accept()

    def cerrar(self):
        if self.torneo:
            self.grabar()
            self.torneo = None
        self.save_video()

    def rotulos_tabs(self):
        self.tab.ponValor(1, "%d %s" % (self.torneo.num_engines(), _("Engines")))
        self.tab.ponValor(2, "%d %s" % (self.torneo.num_games_queued(), _("Games queued")))
        self.tab.ponValor(3, "%d %s" % (self.torneo.num_games_finished(), _("Games finished")))
        self.calc_results()

    def calc_results(self):
        self.li_results = []
        for num in range(self.torneo.num_engines()):
            eng = self.torneo.engine(num)
            ww, wb, dw, db, lw, lb = (
                len(eng.win_white),
                len(eng.win_black),
                len(eng.draw_white),
                len(eng.draw_black),
                len(eng.lost_white),
                len(eng.lost_black),
            )
            tt = ww + wb + dw + db + lw + lb
            p = (ww + wb) * 2 + (dw + db) * 1
            score = (p * 50 / tt) if tt > 0 else 0
            self.li_results.append((eng.clave, score, ww, wb, dw, db, lw, lb))
        self.li_results.sort(key=lambda x: x[1], reverse=True)
        self.gridResults.refresh()

    def borra_resign(self):
        previo = self.ed_resign.textoInt()
        self.ed_resign.tipoInt(0 if previo else 350)

    def borra_draw_range(self):
        previo = self.ed_draw_range.textoInt()
        self.ed_draw_range.tipoInt(0 if previo else 10)

    def muestraPosicion(self):
        if self.fen:
            rotulo = self.fen
            self.btPosicionQuitar.show()
            self.btPosicionPegar.show()
            self.chbNorman.ponValor(False)
        else:
            rotulo = _("Change")
            self.btPosicionQuitar.hide()
            self.btPosicionPegar.show()
        rotulo = " " * 5 + rotulo + " " * 5
        self.btPosicion.ponTexto(rotulo)

    def posicionEditar(self):
        cp = Position.Position()
        cp.read_fen(self.fen)
        resp = Voyager.voyager_position(self, cp)
        if resp is not None:
            self.fen = resp
            self.muestraPosicion()

    def posicionQuitar(self):
        self.fen = ""
        self.muestraPosicion()

    def posicionPegar(self):
        texto = QTUtil.traePortapapeles()
        if texto:
            cp = Position.Position()
            try:
                cp.read_fen(texto.strip())
                self.fen = cp.fen()
                if self.fen == FEN_INITIAL:
                    self.fen = ""
                self.muestraPosicion()
            except:
                pass

    def nuevoBook(self):
        fbin = QTUtil2.leeFichero(self, self.listaLibros.path, "bin", titulo=_("Polyglot book"))
        if fbin:
            self.listaLibros.path = os.path.dirname(fbin)
            name = os.path.basename(fbin)[:-4]
            b = Books.Libro("P", name, fbin, False)
            self.listaLibros.nuevo(b)
            fvar = self.configuracion.ficheroBooks
            self.listaLibros.save_pickle(fvar)
            li = [(x.name, x.path) for x in self.listaLibros.lista]
            li.insert(0, ("* " + _("Default"), "*"))
            self.cbBooks.rehacer(li, b.path)

    def grid_num_datos(self, grid):
        gid = grid.id
        if gid == GRID_ALIAS:
            return self.torneo.num_engines()
        elif gid == GRID_VALUES:
            return len(self.liEnActual)
        elif gid == GRID_GAMES_QUEUED:
            return self.torneo.num_games_queued()
        elif gid == GRID_GAMES_FINISHED:
            return self.torneo.num_games_finished()
        elif gid == GRID_RESULTS:
            return self.torneo.num_engines()

    def grid_dato(self, grid, fila, oColumna):
        columna = oColumna.clave
        gid = grid.id
        if gid == GRID_ALIAS:
            return self.gridDatoEnginesAlias(fila, columna)
        elif gid == GRID_VALUES:
            return self.gridDatoEnginesValores(fila, columna)
        elif gid == GRID_RESULTS:
            return self.gridDatoResult(fila, columna)
        elif gid == GRID_GAMES_QUEUED:
            return self.gridDatoGamesQueued(fila, columna)
        elif gid == GRID_GAMES_FINISHED:
            return self.gridDatoGamesFinished(fila, columna)

    def gridDatoEnginesAlias(self, fila, columna):
        me = self.torneo.engine(fila)
        if columna == "ALIAS":
            return me.clave
        elif columna == "NUM":
            return str(fila + 1)

    def gridDatoEnginesValores(self, fila, columna):
        li = self.liEnActual[fila]
        if columna == "CAMPO":
            return li[0]
        else:
            return str(li[1])

    def gridDatoResult(self, fila, columna):
        clave, score, ww, wb, dw, db, lw, lb = self.li_results[fila]
        if columna == "NUM":
            return str(fila + 1)
        elif columna == "ENGINE":
            return clave
        elif columna == "SCORE":
            return "%.1f" % score if score > 0 else "0"
        elif columna == "WIN":
            return "%d" % (ww + wb)
        elif columna == "LOST":
            return "%d" % (lw + lb)
        elif columna == "DRAW":
            return "%d" % (dw + db)
        elif columna == "WIN-WHITE":
            return "%d" % ww
        elif columna == "LOST-WHITE":
            return "%d" % lw
        elif columna == "DRAW-WHITE":
            return "%d" % dw
        elif columna == "WIN-BLACK":
            return "%d" % wb
        elif columna == "LOST-BLACK":
            return "%d" % lb
        elif columna == "DRAW-BLACK":
            return "%d" % db
        elif columna == "GAMES":
            return "%s" % (ww + wb + lw + lb + dw + db)

    def gridDatoGamesQueued(self, fila, columna):
        gm = self.torneo.game_queued(fila)
        if columna == "NUM":
            return str(fila + 1)
        elif columna == "WHITE":
            en = self.torneo.buscaHEngine(gm.hwhite)
            return en.clave if en else "???"
        elif columna == "BLACK":
            en = self.torneo.buscaHEngine(gm.hblack)
            return en.clave if en else "???"
        # elif columna == "STATE":
        #     return _("Working...") if gm.worker else ""
        elif columna == "TIME":
            return gm.etiTiempo()

    def gridDatoGamesFinished(self, fila, columna):
        gm = self.torneo.game_finished(fila)
        if columna == "NUM":
            return str(fila + 1)
        elif columna == "WHITE":
            en = self.torneo.buscaHEngine(gm.hwhite)
            return en.clave if en else "???"
        elif columna == "BLACK":
            en = self.torneo.buscaHEngine(gm.hblack)
            return en.clave if en else "???"
        elif columna == "RESULT":
            return gm.result
        elif columna == "TIME":
            return gm.etiTiempo()

    def grid_cambiado_registro(self, grid, fila, columna):
        if grid.id == GRID_ALIAS:
            me = self.torneo.engine(fila)
            self.actEngine(me)
            self.gridEnginesValores.refresh()

    def actEngine(self, me):
        self.liEnActual = []
        fila = self.gridEnginesAlias.recno()
        if fila < 0:
            return

        # tipo, key, rotulo, valor
        self.liEnActual.append((_("Engine"), me.name))
        self.liEnActual.append((_("Author"), me.autor))
        self.liEnActual.append((_("File"), Util.relative_path(me.path_exe)))
        self.liEnActual.append((_("Information"), me.id_info.replace("\n", " - ")))
        self.liEnActual.append(("ELO", me.elo))
        self.liEnActual.append((_("Maximum depth"), me.depth))
        self.liEnActual.append((_("Maximum seconds to think"), me.time))
        pbook = me.book
        if pbook == "-":
            pbook = "* " + _("Engine book")
        else:
            if pbook == "*":
                pbook = "* " + _("Default")
            dic = {"au": _("Uniform random"), "ap": _("Proportional random"), "mp": _("Always the highest percentage")}
            pbook += "   (%s)" % dic[me.bookRR]

        self.liEnActual.append((_("Opening book"), pbook))

        for opcion in me.li_uci_options():
            self.liEnActual.append((opcion.name, str(opcion.valor)))

    def gm_launch(self):
        self.grabar()
        worker_plant = os.path.join(self.configuracion.folder_tournaments_workers(), "worker.%05d")
        pos = 1
        while True:
            wfile = worker_plant % pos
            if Util.exist_file(wfile):
                if not Util.remove_file(wfile):
                    pos += 1
                    continue
            break
        XRun.run_lucas("-tournament", self.torneo.file, wfile)

    def verSiJugar(self):
        return self.xjugar

    def comprueba_cambios(self):
        if self.torneo:
            changed = (
                self.torneo.resign() != self.ed_resign.textoInt()
                or self.torneo.drawMinPly() != self.sbDrawMinPly.valor()
                or self.torneo.drawRange() != self.ed_draw_range.textoInt()
                or self.torneo.fen() != self.fen
                or self.torneo.norman() != self.chbNorman.valor()
                or self.torneo.book() != self.cbBooks.valor()
                or self.torneo.bookDepth() != self.sbBookDepth.valor()
                or self.torneo.adjudicator_active() != self.gbJ.isChecked()
                or self.torneo.adjudicator() != self.cbJmotor.valor()
                or self.torneo.adjudicator_time() != self.edJtiempo.textoFloat()
            )
            if changed:
                self.grabar()

            last_change_saved = self.torneo.get_last_change()
            if last_change_saved and last_change_saved > self.last_change:
                self.last_change = Util.today()
                self.torneo.dbs_reread()
                self.gridGamesFinished.refresh()
                self.gridGamesQueued.refresh()
                self.gridResults.refresh()
                self.rotulos_tabs()

            QtCore.QTimer.singleShot(5000, self.comprueba_cambios)

    def grabar(self):
        if self.torneo:
            self.torneo.resign(self.ed_resign.textoInt())
            self.torneo.drawMinPly(self.sbDrawMinPly.valor())
            self.torneo.drawRange(self.ed_draw_range.textoInt())
            self.torneo.fen(self.fen)
            self.torneo.norman(self.chbNorman.valor())
            self.torneo.book(self.cbBooks.valor())
            self.torneo.bookDepth(self.sbBookDepth.valor())
            self.torneo.adjudicator_active(self.gbJ.isChecked())
            self.torneo.adjudicator(self.cbJmotor.valor())
            self.torneo.adjudicator_time(self.edJtiempo.textoFloat())

    def enNuevo(self):
        # Pedimos el ejecutable
        exeMotor = QTUtil2.leeFichero(self, self.torneo.ultCarpetaEngines(), "*", _("Engine"))
        if not exeMotor:
            return
        self.torneo.ultCarpetaEngines(os.path.dirname(exeMotor))

        # Leemos el UCI
        me = Engines.read_engine_uci(exeMotor)
        if not me:
            QTUtil2.message_bold(self, _X(_("The file %1 does not correspond to a UCI engine type."), exeMotor))
            return
        eng = Tournament.EngineTournament()
        eng.restore(me.save())
        eng.pon_huella(self.torneo)
        self.torneo.save_engine(eng)
        self.gridEnginesAlias.refresh()
        self.gridEnginesAlias.gobottom(0)

        self.gridResults.refresh()

        self.rotulos_tabs()

    def enImportar(self):
        menu = QTVarios.LCMenu(self)
        lista = self.configuracion.comboMotores()
        nico = QTVarios.rondoPuntos()
        for name, clave in lista:
            menu.opcion(clave, name, nico.otro())

        resp = menu.lanza()
        if not resp:
            return

        me = Tournament.EngineTournament()
        me.pon_huella(self.torneo)
        me.read_exist_engine(resp)
        self.torneo.save_engine(me)
        self.gridEnginesAlias.refresh()
        self.gridEnginesAlias.gobottom(0)

        self.gridResults.refresh()

        self.rotulos_tabs()

    def grid_tecla_control(self, grid, k, siShift, siControl, siAlt):
        if k == 16777223:
            if grid == self.gridGamesQueued:
                self.gm_borrar_queued()
            elif grid == self.gridEnginesAlias:
                self.enBorrar()
            elif grid == self.gridGamesFinished:
                self.gm_borrar_finished()

    def grid_doble_click(self, grid, fila, columna):
        if grid in [self.gridEnginesAlias, self.gridEnginesValores]:
            self.enModificar()
        elif grid == self.gridGamesFinished:
            self.gm_show_finished()

    def grid_color_fondo(self, grid, nfila, ocol):
        if grid == self.gridResults:
            key = ocol.clave
            if "WHITE" in key:
                return self.qtColor["WHITE"]
            elif "BLACK" in key:
                return self.qtColor["BLACK"]
            elif "SCORE" in key:
                return self.qtColor["SCORE"]

    def enModificar(self):
        fila = self.gridEnginesAlias.recno()
        if fila < 0:
            return
        me = self.torneo.engine(fila)

        w = WEngines.WEngine(self, self.torneo.list_engines(), me, siTorneo=True)
        if w.exec_():
            self.actEngine(me)
            self.torneo.save_engine(me)
            self.gridEnginesAlias.refresh()
            self.gridEnginesValores.refresh()
            self.gridResults.refresh()

    def enBorrar(self):
        li = self.gridEnginesAlias.recnosSeleccionados()
        if li:
            clista = ",".join([self.torneo.engine(pos).name for pos in li])
            if QTUtil2.pregunta(self, _("Do you want to delete all selected records?") + "\n\n%s" % clista):
                self.torneo.remove_engines(li)
                self.gridEnginesAlias.refresh()
                if self.torneo.num_engines() > 0:
                    self.grid_cambiado_registro(self.gridEnginesAlias, 0, None)
                else:
                    self.liEnActual = []
                self.gridEnginesValores.refresh()
                self.gridGamesQueued.refresh()
                self.gridEnginesAlias.setFocus()
                self.gridResults.refresh()
                self.rotulos_tabs()

    def enCopiar(self):
        fila = self.gridEnginesAlias.recno()
        if fila >= 0:
            me = self.torneo.engine(fila)
            self.torneo.copy_engine(me)
            self.gridEnginesAlias.refresh()
            self.gridEnginesAlias.gobottom(0)
            self.gridResults.refresh()
            self.rotulos_tabs()

    def gm_crear_queued(self):
        if self.torneo.num_engines() < 2:
            QTUtil2.message_error(self, _("You must create at least two engines"))
            return

        dicValores = self.configuracion.leeVariables("crear_torneo")

        get = dicValores.get

        liGen = [FormLayout.separador]

        config = FormLayout.Spinbox(_("Rounds"), 1, 999, 50)
        liGen.append((config, get("ROUNDS", 1)))

        liGen.append(FormLayout.separador)

        config = FormLayout.Editbox(_("Total minutes"), 40, tipo=float, decimales=2)
        liGen.append((config, get("MINUTES", 10.00)))

        config = FormLayout.Editbox(_("Seconds added per move"), 40, tipo=float, decimales=2)
        liGen.append((config, get("SECONDS", 0.0)))

        liGen.append((None, _("Engines")))

        li_engines = self.torneo.list_engines()
        for pos, en in enumerate(li_engines):
            liGen.append((en.clave, get(en.huella, True)))

        liGen.append(FormLayout.separador)

        resultado = FormLayout.fedit(liGen, title=_("Games"), parent=self, icon=Iconos.Torneos())
        if resultado is None:
            return

        accion, liResp = resultado
        dicValores["ROUNDS"] = rounds = liResp[0]
        dicValores["MINUTES"] = minutos = liResp[1]
        dicValores["SECONDS"] = segundos = liResp[2]

        liSel = []
        for num in range(self.torneo.num_engines()):
            en = li_engines[num]
            dicValores[en.huella] = si = liResp[3 + num]
            if si:
                liSel.append(en.huella)

        self.configuracion.escVariables("crear_torneo", dicValores)

        nSel = len(liSel)
        if nSel < 2:
            QTUtil2.message_error(self, _("You must use at least two engines"))
            return

        for r in range(rounds):
            for x in range(0, nSel - 1):
                for y in range(x + 1, nSel):
                    self.torneo.nuevoGame(liSel[x], liSel[y], minutos, segundos)
                    self.torneo.nuevoGame(liSel[y], liSel[x], minutos, segundos)

        self.gridGamesQueued.refresh()
        self.gridGamesQueued.gobottom()
        self.rotulos_tabs()

    def gm_borrar_queued(self):
        li = self.gridGamesQueued.recnosSeleccionados()
        if li:
            if QTUtil2.pregunta(self, _("Do you want to delete all selected records?")):
                self.torneo.remove_games_queued(li)
                self.gridGamesQueued.refresh()
                self.gridResults.refresh()
                self.rotulos_tabs()

    def gm_borrar_finished(self):
        li = self.gridGamesFinished.recnosSeleccionados()
        if li:
            if QTUtil2.pregunta(self, _("Do you want to delete all selected records?")):
                self.torneo.remove_games_finished(li)
                self.gridGamesFinished.refresh()
                self.rotulos_tabs()

    def gm_show_finished(self):
        li = self.gridGamesFinished.recnosSeleccionados()
        if li:
            pos = li[0]
            game = self.torneo.game_finished(pos)
            game = Code.procesador.gestorPartida(self, game.game(), True, None)
            if game:
                self.torneo.save_game_finished(pos, game)
                self.gridGamesFinished.refresh()
                self.rotulos_tabs()

    def gm_save_pgn(self):
        if self.torneo.num_games_finished() > 0:
            w = PantallaSavePGN.WSaveVarios(self, self.configuracion)
            if w.exec_():
                ws = PantallaSavePGN.FileSavePGN(self, w.dic_result)
                if ws.open():
                    ws.um()
                    if not ws.is_new:
                        ws.write("\n\n")
                    for gm in self.torneo.db_games_finished:
                        game = Game.Game()
                        game.restore(gm.game_save)
                        ws.write(game.pgn())
                        ws.write("\n\n\n")
                    ws.close()
                    ws.um_final()
