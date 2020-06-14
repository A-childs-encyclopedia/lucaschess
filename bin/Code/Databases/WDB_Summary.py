from PySide2 import QtWidgets

from Code import AperturasStd
from Code import Game
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import Delegados
from Code.QT import FormLayout
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios


class WSummary(QtWidgets.QWidget):
    def __init__(self, procesador, wb_database, dbGames, siMoves=True):
        QtWidgets.QWidget.__init__(self)

        self.wb_database = wb_database

        self.dbGames = dbGames  # <--setdbGames
        self.infoMove = None  # <-- setInfoMove
        self.wmoves = None  # <-- setwmoves
        self.fenm2 = None
        self.liMoves = []
        self.analisisMRM = None
        self.siMoves = siMoves
        self.procesador = procesador
        self.configuracion = procesador.configuracion

        self.leeConfig()

        self.aperturasStd = AperturasStd.ap

        self.si_figurines_pgn = self.configuracion.x_pgn_withfigurines

        self.pvBase = ""

        self.orden = ["games", False]

        self.lbName = (
            Controles.LB(self, "")
            .ponWrap()
            .alinCentrado()
            .ponColorFondoN("white", "#4E5A65")
            .ponTipoLetra(puntos=10 if siMoves else 16)
        )
        if not siMoves:
            self.lbName.hide()

        # Grid
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("number", _("N."), 35, centered=True)
        self.delegadoMove = Delegados.EtiquetaPGN(True if self.si_figurines_pgn else None)
        o_columns.nueva("move", _("Move"), 60, edicion=self.delegadoMove)
        o_columns.nueva("analisis", _("Analysis"), 60, siDerecha=True)
        o_columns.nueva("games", _("Games"), 70, siDerecha=True)
        o_columns.nueva("pgames", "% " + _("Games"), 70, siDerecha=True)
        o_columns.nueva("win", _("Win"), 70, siDerecha=True)
        o_columns.nueva("draw", _("Draw"), 70, siDerecha=True)
        o_columns.nueva("lost", _("Lost"), 70, siDerecha=True)
        o_columns.nueva("pwin", "% " + _("Win"), 60, siDerecha=True)
        o_columns.nueva("pdraw", "% " + _("Draw"), 60, siDerecha=True)
        o_columns.nueva("plost", "% " + _("Lost"), 60, siDerecha=True)
        o_columns.nueva("pdrawwin", "%% %s" % _("W+D"), 60, siDerecha=True)
        o_columns.nueva("pdrawlost", "%% %s" % _("L+D"), 60, siDerecha=True)

        self.grid = Grid.Grid(self, o_columns, xid="summary", siSelecFilas=True)
        self.grid.tipoLetra(puntos=self.configuracion.x_pgn_fontpoints)
        self.grid.ponAltoFila(self.configuracion.x_pgn_rowheight)

        # ToolBar
        li_acciones = [
            (_("Start position"), Iconos.Inicio(), self.inicio),
            None,
            (_("Previous"), Iconos.AnteriorF(), self.anterior),
            (_("Next"), Iconos.SiguienteF(), self.siguiente),
            None,
            (_("Analyze"), Iconos.Analizar(), self.analizar),
            None,
            (_("Rebuild"), Iconos.Reindexar(), self.reindexar),
            None,
            (_("Config"), Iconos.Configurar(), self.config),
            None,
        ]

        self.tb = QTVarios.LCTB(self, li_acciones, tamIcon=20, siTexto=not self.siMoves)
        if self.siMoves:
            self.tb.vertical()

        layout = Colocacion.V().control(self.lbName)
        if not self.siMoves:
            layout.control(self.tb)
        layout.control(self.grid)
        if self.siMoves:
            layout = Colocacion.H().control(self.tb).otro(layout)

        layout.margen(1)

        self.setLayout(layout)

        self.qtColor = (
            QTUtil.qtColorRGB(221, 255, 221),
            QTUtil.qtColorRGB(247, 247, 247),
            QTUtil.qtColorRGB(255, 217, 217),
        )
        self.qtColorTotales = QTUtil.qtColorRGB(170, 170, 170)

    def grid_doble_clickCabecera(self, grid, oColumna):
        key = oColumna.clave

        if key == "analisis":

            def func(dic):
                return dic["analisis"].centipawns_abs() if dic["analisis"] else -9999999

        elif key == "move":

            def func(dic):
                return dic["move"].upper()

        else:

            def func(dic):
                return dic[key]

        tot = self.liMoves[-1]
        li = sorted(self.liMoves[:-1], key=func)

        orden, mas = self.orden
        if orden == key:
            mas = not mas
        else:
            mas = key == "move"
        if not mas:
            li.reverse()
        self.orden = key, mas
        li.append(tot)
        self.liMoves = li
        self.grid.refresh()

    def setdbGames(self, dbGames):
        self.dbGames = dbGames

    def focusInEvent(self, event):
        self.wb_database.ultFocus = self

    def setInfoMove(self, infoMove):
        self.infoMove = infoMove

    def setwmoves(self, wmoves):
        self.wmoves = wmoves

    def grid_num_datos(self, grid):
        return len(self.liMoves)

    def grid_tecla_control(self, grid, k, siShift, siControl, siAlt):
        if k == 16777220:
            self.siguiente()

    def grid_dato(self, grid, nfila, ocol):
        key = ocol.clave

        # Last=Totals
        if self.siFilaTotales(nfila):
            if key in ("number", "analisis", "pgames"):
                return ""
            elif key == "move":
                return _("Total")

        if self.liMoves[nfila]["games"] == 0 and not (key in ("number", "analisis", "move")):
            return ""
        v = self.liMoves[nfila][key]
        if key.startswith("p"):
            return "%.01f %%" % v
        elif key == "analisis":
            return v.abrTextoBase() if v else ""
        elif key == "number":
            if self.si_figurines_pgn:
                self.delegadoMove.setWhite(not ("..." in v))
            return v
        else:
            return str(v)

    def posicionFila(self, nfila):
        dic = self.liMoves[nfila]
        li = [[k, dic[k]] for k in ("win", "draw", "lost")]
        li = sorted(li, key=lambda x: x[1], reverse=True)
        d = {}
        prev = 0
        ant = li[0][1]
        total = 0
        for cl, v in li:
            if v < ant:
                prev += 1
            d[cl] = prev
            ant = v
            total += v
        if total == 0:
            d["win"] = d["draw"] = d["lost"] = -1
        return d

    def grid_color_fondo(self, grid, nfila, ocol):
        key = ocol.clave
        if self.siFilaTotales(nfila) and not (key in ("number", "analisis")):
            return self.qtColorTotales
        if key in ("pwin", "pdraw", "plost"):
            dic = self.posicionFila(nfila)
            n = dic[key[1:]]
            if n > -1:
                return self.qtColor[n]

    def popPV(self, pv):
        if pv:
            rb = pv.rfind(" ")
            if rb == -1:
                pv = ""
            else:
                pv = pv[:rb]
        return pv

    def analizar(self):
        if not self.fenm2:
            return

        fila = self.grid.recno()

        def dispatch(nada):
            self.actualizaPV(self.pvBase)

        # TODO pendiente
        # analisis = WBG_Comun.Analisis(self, self.de, dispatch, self.procesador)
        # resp = analisis.menuAnalizar(self.fenm2, None, siShowMoves)
        # if resp:
        #     game = wk["game"]
        #     fen = game.last_jg().position_before.fen()
        #     pv = wk["pv"]
        #     analisis.exeAnalizar(self.fenm2, resp, None, fen, pv, rmAnalisis)

    def inicio(self):
        self.actualizaPV("")
        self.cambiaInfoMove()

    def anterior(self):
        if self.pvBase:
            pv = self.popPV(self.pvBase)

            self.actualizaPV(pv)
            self.cambiaInfoMove()

    def rehazActual(self):
        recno = self.grid.recno()
        if recno >= 0:
            dic = self.liMoves[recno]
            if "pv" in dic:
                pv = dic["pv"]
                if pv:
                    li = pv.split(" ")
                    pv = " ".join(li[:-1])
                self.actualizaPV(pv)
                self.cambiaInfoMove()

    def siguiente(self):
        recno = self.grid.recno()
        if recno >= 0:
            dic = self.liMoves[recno]
            if "pv" in dic:
                pv = dic["pv"]
                if pv.count(" ") > 0:
                    pv = "%s %s" % (self.pvBase, dic["pvmove"])  # transposition case
                self.actualizaPV(pv)
                self.cambiaInfoMove()

    def ponPV(self, pvMirar):
        if not pvMirar:
            self.actualizaPV(None)
        else:
            self.analisisMRM = None
            dicAnalisis = {}
            self.fenm2 = None
            p = Game.Game()
            if pvMirar:
                p.read_pv(pvMirar)
            self.fenm2 = p.last_position.fenm2()
            self.analisisMRM = None
            # TODO analisis
            #     self.dbAnalisis.mrm(self.fenm2)
            # if self.analisisMRM:
            #     for rm in self.analisisMRM.li_rm:
            #         dicAnalisis[rm.movimiento()] = rm
            li = pvMirar.split(" ")
            self.pvBase = " ".join(li[:-1])
            busca = li[-1]
            self.liMoves = self.dbGames.get_summary(pvMirar, dicAnalisis, self.si_figurines_pgn)
            for fila, move in enumerate(self.liMoves):
                if move.get("pvmove") == busca:
                    self.grid.goto(fila, 0)
                    break
        self.cambiaInfoMove()

    def reindexar(self, depth=None):
        if depth is None:
            if not QTUtil2.pregunta(self, _("Do you want to rebuild stats?")):
                return

            # Select depth
            liGen = [(None, None)]
            liGen.append((None, _("Select the number of moves <br> for each game to be considered")))
            liGen.append((None, None))

            config = FormLayout.Spinbox(_("Depth"), 3, 255, 50)
            liGen.append((config, self.dbGames.depthStat()))

            resultado = FormLayout.fedit(liGen, title=_("Rebuild"), parent=self, icon=Iconos.Reindexar())
            if resultado is None:
                return None

            accion, liResp = resultado

            depth = liResp[0]

        self.RECCOUNT = 0

        bpTmp = QTUtil2.BarraProgreso1(self, _("Rebuilding"))
        bpTmp.mostrar()

        def dispatch(recno, reccount):
            if reccount != self.RECCOUNT:
                self.RECCOUNT = reccount
                bpTmp.ponTotal(reccount)
            bpTmp.pon(recno)
            return not bpTmp.is_canceled()

        self.dbGames.rebuild_stat(dispatch, depth)
        bpTmp.cerrar()
        self.inicio()

    def movActivo(self):
        recno = self.grid.recno()
        if recno >= 0:
            return self.liMoves[recno]
        else:
            return None

    def siFilaTotales(self, nfila):
        return nfila == len(self.liMoves) - 1

    def noFilaTotales(self, nfila):
        return nfila < len(self.liMoves) - 1

    def grid_doble_click(self, grid, fil, col):
        if self.noFilaTotales(fil):
            self.siguiente()

    def gridActualiza(self):
        nfila = self.grid.recno()
        if nfila > -1:
            self.grid_cambiado_registro(None, nfila, None)

    def actualiza(self):
        movActual = self.infoMove.movActual
        pvBase = self.popPV(movActual.allPV())
        self.actualizaPV(pvBase)
        if movActual:
            pv = movActual.allPV()
            for n in range(len(self.liMoves) - 1):
                if self.liMoves[n]["pv"] == pv:
                    self.grid.goto(n, 0)
                    return

    def actualizaPV(self, pvBase):
        self.pvBase = pvBase
        if not pvBase:
            pvMirar = ""
        else:
            pvMirar = self.pvBase

        self.analisisMRM = None
        dicAnalisis = {}
        self.fenm2 = None
        if pvMirar:
            p = Game.Game()
            if pvMirar:
                p.read_pv(pvMirar)
            self.fenm2 = p.last_position.fenm2()
            # TODO añadir el análisis
            # self.analisisMRM = self.dbAnalisis.mrm(self.fenm2)
            # if self.analisisMRM:
            #     for rm in self.analisisMRM.li_rm:
            #         dicAnalisis[rm.movimiento()] = rm
        self.liMoves = self.dbGames.get_summary(pvMirar, dicAnalisis, self.si_figurines_pgn, self.allmoves)

        self.grid.refresh()
        self.grid.gotop()

    def reset(self):
        self.actualizaPV(None)
        self.grid.refresh()
        self.grid.gotop()

    def grid_cambiado_registro(self, grid, fila, oCol):
        if self.grid.hasFocus() or self.hasFocus():
            self.cambiaInfoMove()

    def cambiaInfoMove(self):
        fila = self.grid.recno()
        if fila >= 0 and self.noFilaTotales(fila):
            pv = self.liMoves[fila]["pv"]
            p = Game.Game()
            p.read_pv(pv)
            p.is_finished()
            p.assign_opening()
            self.infoMove.modoPartida(p, 9999)
            self.setFocus()
            self.grid.setFocus()

    def showActiveName(self, name):
        # Llamado de WBG_Games -> setNameToolbar
        self.lbName.ponTexto(_("Summary of %s") % name)

    def leeConfig(self):
        dicConfig = self.configuracion.leeVariables("DBSUMMARY")
        if not dicConfig:
            dicConfig = {"allmoves": False}
        self.allmoves = dicConfig["allmoves"]
        return dicConfig

    def grabaConfig(self):
        dicConfig = {"allmoves": self.allmoves}
        self.configuracion.escVariables("DBSUMMARY", dicConfig)
        self.configuracion.graba()

    # def pr int_repertorio(self):
    #     siW = True
    #     basepv = "e2e4"
    #     k = [0, []]

    #     def haz(lipv):
    #         npv = len(lipv)
    #         liChildren = self.dbGames.db_stat.children(" ".join(lipv), False)
    #         if len(liChildren) == 0:
    #             return
    #         suma = 0
    #         for n, alm in enumerate(liChildren):
    #             alm.tt = alm.W + alm.B + alm.D + alm.O
    #             suma += alm.tt
    #         if (npv % 2 == 0) and siW:
    #             # buscamos la que tenga mas tt
    #             mx = 0
    #             mx_alm = None
    #             for alm in liChildren:
    #                 if alm.tt > mx:
    #                     mx_alm = alm
    #                     mx = alm.tt
    #             li = lipv[:]
    #             if mx_alm:
    #                 li.append(mx_alm.move)
    #                 haz(li)
    #         else:
    #             if suma < 2000 and npv < 20:
    #                 k[0] += 1
    #                 liLast = k[1]
    #                 nl = len(liLast)
    #                 ok = False
    #                 lip = []
    #                 for nr, pv in enumerate(lipv):
    #                     if nr < nl and not ok:
    #                         if pv == liLast[nr]:
    #                             lip.append("....")
    #                         else:
    #                             lip.append(pv)
    #                             ok = True
    #                     else:
    #                         lip.append(pv)
    #                 k[1] = lipv
    #                 # liW = []
    #                 # liB = []
    #                 # sitW = True
    #                 # for pv in lip:
    #                 #     if sitW:
    #                 #         liW.append(pv)
    #                 #     else:
    #                 #         liB.append(pv)
    #                 #     sitW = not sitW
    #                 #
    #                 # p rint " ".join(liW)
    #                 # pr int " ".join(liB)
    #                 pri nt " ".join(lip)
    #                 return
    #             for alm in liChildren:
    #                 li = lipv[:]
    #                 li.append(alm.move)
    #                 haz(li)
    #     haz([basepv,])

    def config(self):
        menu = QTVarios.LCMenu(self)
        menu.opcion("allmoves", _("Show all moves"), siChecked=self.allmoves)
        resp = menu.lanza()
        if resp is None:
            return
        self.allmoves = not self.allmoves

        self.actualizaPV(self.pvBase)


class WSummaryBase(QtWidgets.QWidget):
    def __init__(self, procesador, db_stat):
        QtWidgets.QWidget.__init__(self)

        self.db_stat = db_stat
        self.liMoves = []
        self.procesador = procesador
        self.configuracion = procesador.configuracion

        self.si_figurines_pgn = self.configuracion.x_pgn_withfigurines

        self.orden = ["games", False]

        # Grid
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("number", _("N."), 35, centered=True)
        self.delegadoMove = Delegados.EtiquetaPGN(True if self.si_figurines_pgn else None)
        o_columns.nueva("move", _("Move"), 60, edicion=self.delegadoMove)
        o_columns.nueva("games", _("Games"), 70, siDerecha=True)
        o_columns.nueva("pgames", "% " + _("Games"), 70, siDerecha=True, centered=True)
        o_columns.nueva("win", _("Win"), 70, siDerecha=True)
        o_columns.nueva("draw", _("Draw"), 70, siDerecha=True)
        o_columns.nueva("lost", _("Lost"), 70, siDerecha=True)
        o_columns.nueva("pwin", "% " + _("Win"), 60, siDerecha=True)
        o_columns.nueva("pdraw", "% " + _("Draw"), 60, siDerecha=True)
        o_columns.nueva("plost", "% " + _("Lost"), 60, siDerecha=True)
        o_columns.nueva("pdrawwin", "%% %s" % _("W+D"), 60, siDerecha=True)
        o_columns.nueva("pdrawlost", "%% %s" % _("L+D"), 60, siDerecha=True)

        self.grid = Grid.Grid(self, o_columns, xid="summarybase", siSelecFilas=True)
        self.grid.tipoLetra(puntos=self.configuracion.x_pgn_fontpoints)
        self.grid.ponAltoFila(self.configuracion.x_pgn_rowheight)

        layout = Colocacion.V()
        layout.control(self.grid)
        layout.margen(1)

        self.setLayout(layout)

        self.qtColor = (
            QTUtil.qtColorRGB(221, 255, 221),
            QTUtil.qtColorRGB(247, 247, 247),
            QTUtil.qtColorRGB(255, 217, 217),
        )
        self.qtColorTotales = QTUtil.qtColorRGB(170, 170, 170)

    def grid_doble_clickCabecera(self, grid, oColumna):
        key = oColumna.clave

        if key == "move":

            def func(dic):
                return dic["move"].upper()

        else:

            def func(dic):
                return dic[key]

        tot = self.liMoves[-1]
        li = sorted(self.liMoves[:-1], key=func)

        orden, mas = self.orden
        if orden == key:
            mas = not mas
        else:
            mas = key == "move"
        if not mas:
            li.reverse()
        self.orden = key, mas
        li.append(tot)
        self.liMoves = li
        self.grid.refresh()

    def grid_num_datos(self, grid):
        return len(self.liMoves)

    def grid_dato(self, grid, nfila, ocol):
        key = ocol.clave

        # Last=Totals
        if self.siFilaTotales(nfila):
            if key in ("number", "pgames"):
                return ""
            elif key == "move":
                return _("Total")

        if self.liMoves[nfila]["games"] == 0 and not (key in ("number", "move")):
            return ""
        v = self.liMoves[nfila][key]
        if key.startswith("p"):
            return "%.01f %%" % v
        elif key == "number":
            if self.si_figurines_pgn:
                self.delegadoMove.setWhite(not ("..." in v))
            return v
        else:
            return str(v)

    def posicionFila(self, nfila):
        dic = self.liMoves[nfila]
        li = [[k, dic[k]] for k in ("win", "draw", "lost")]
        li = sorted(li, key=lambda x: x[1], reverse=True)
        d = {}
        prev = 0
        ant = li[0][1]
        total = 0
        for cl, v in li:
            if v < ant:
                prev += 1
            d[cl] = prev
            ant = v
            total += v
        if total == 0:
            d["win"] = d["draw"] = d["lost"] = -1
        return d

    def grid_color_fondo(self, grid, nfila, ocol):
        key = ocol.clave
        if self.siFilaTotales(nfila) and not (key in ("number", "analisis")):
            return self.qtColorTotales
        if key in ("pwin", "pdraw", "plost"):
            dic = self.posicionFila(nfila)
            n = dic[key[1:]]
            if n > -1:
                return self.qtColor[n]

    def siFilaTotales(self, nfila):
        return nfila == len(self.liMoves) - 1

    def noFilaTotales(self, nfila):
        return nfila < len(self.liMoves) - 1

    def actualizaPV(self, pvBase):
        self.pvBase = pvBase
        if not pvBase:
            pvMirar = ""
        else:
            pvMirar = self.pvBase

        self.liMoves = self.db_stat.get_summary(pvMirar, {}, self.si_figurines_pgn, False)

        self.grid.refresh()
        self.grid.gotop()

    def grid_boton_derecho(self, grid, fila, columna, modificadores):
        if self.siFilaTotales(fila):
            return
        alm = self.liMoves[fila]["rec"]
        if not alm or len(alm.LIALMS) < 2:
            return

        menu = QTVarios.LCMenu(self)
        rondo = QTVarios.rondoPuntos()
        for ralm in alm.LIALMS:
            menu.opcion(ralm, Game.pv_pgn(None, ralm.PV), rondo.otro())
            menu.separador()
        resp = menu.lanza()
        if resp:
            self.actualizaPV(resp.PV)

    def grid_tecla_control(self, grid, k, siShift, siControl, siAlt):
        if k == 16777220:
            self.siguiente()

    def grid_doble_click(self, grid, fil, col):
        self.siguiente()

    def siguiente(self):
        recno = self.grid.recno()
        if recno >= 0 and self.noFilaTotales(recno):
            dic = self.liMoves[recno]
            if "pv" in dic:
                pv = dic["pv"]
                if pv.count(" ") > 0:
                    pv = "%s %s" % (self.pvBase, dic["pvmove"])  # transposition case
                self.actualizaPV(pv)
