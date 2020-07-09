import os
import shutil
import time

from PySide2 import QtWidgets, QtCore

from Code import Position
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import FormLayout
from Code.QT import Grid
from Code.QT import Iconos
from Code.Engines import WEngines
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.QT import Tablero
from Code import STS
from Code import Util
import Code


class WRun(QTVarios.WDialogo):
    def __init__(self, wParent, sts, work, procesador):
        titulo = "%s - %s - %s" % (sts.name, work.ref, work.pathToExe())
        icono = Iconos.STS()
        extparam = "runsts"
        QTVarios.WDialogo.__init__(self, wParent, titulo, icono, extparam)

        self.work = work
        self.sts = sts
        self.ngroup = -1
        self.xengine = procesador.creaGestorMotor(work.configEngine(), work.seconds * 1000, work.depth)
        self.xengine.set_direct()
        self.playing = False
        self.configuracion = procesador.configuracion
        self.run_test_close = work.seconds > 3 or work.depth > 10

        # Toolbar
        li_acciones = [
            (_("Close"), Iconos.MainMenu(), self.cerrar),
            None,
            (_("Run"), Iconos.Run(), self.run),
            (_("Pause"), Iconos.Pelicula_Pausa(), self.pause),
            None,
        ]
        self.tb = tb = QTVarios.LCTB(self, li_acciones, tamIcon=24)

        # Area resultados
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("GROUP", _("Group"), 180)
        o_columns.nueva("DONE", _("Done"), 100, centered=True)
        o_columns.nueva("WORK", _("Result"), 120, centered=True)

        self.dworks = self.read_works()
        self.calc_max()
        for x in range(len(self.sts.works) - 1, -1, -1):
            work = self.sts.works.getWork(x)
            if work != self.work:
                key = "OTHER%d" % x
                reg = self.dworks[key]
                o_columns.nueva(key, reg.title, 120, centered=True)

        self.grid = Grid.Grid(self, o_columns, siSelecFilas=True)

        self.colorMax = QTUtil.qtColor("#840C24")
        self.colorOth = QTUtil.qtColor("#4668A6")

        layout = Colocacion.H()
        layout.control(self.grid)
        layout.margen(3)

        ly = Colocacion.V().control(tb).otro(layout)

        self.setLayout(ly)

        self.restore_video(siTam=True, anchoDefecto=800, altoDefecto=430)

        resp = self.sts.siguientePosicion(self.work)
        if resp:
            self.tb.setAccionVisible(self.pause, False)
            self.tb.setAccionVisible(self.run, True)
        else:
            self.tb.setAccionVisible(self.pause, False)
            self.tb.setAccionVisible(self.run, False)

    def cerrar(self):
        if self.playing:
            self.pause()
            return
        self.sts.save()
        self.xengine.terminar()
        self.save_video()
        self.playing = False
        self.accept()

    def closeEvent(self, event):
        self.cerrar()

    def test_close(self, rm):
        QTUtil.refresh_gui()
        return self.playing

    def run(self):
        if not Util.exist_file(self.work.pathToExe()):
            QTUtil2.message_error(self, "%s\n%s" % (self.work.pathToExe(), _("Path does not exist.")))
            return
        self.tb.setAccionVisible(self.pause, True)
        self.tb.setAccionVisible(self.run, False)
        QTUtil.refresh_gui()
        self.playing = True

        if self.run_test_close:
            self.xengine.ponGuiDispatch(self.test_close)
        while self.playing:
            self.siguiente()

    def pause(self):
        self.tb.setAccionVisible(self.pause, False)
        self.tb.setAccionVisible(self.run, True)
        QTUtil.refresh_gui()
        self.playing = False
        self.sts.save()

    def siguiente(self):
        resp = self.sts.siguientePosicion(self.work)
        if resp:
            ngroup, self.nfen, self.elem = resp
            if ngroup != self.ngroup:
                self.calc_max()
                self.grid.refresh()
                self.ngroup = ngroup
            if not self.playing:
                return
            t0 = time.time()
            mrm = self.xengine.analiza(self.elem.fen)
            t_dif = time.time() - t0
            if mrm:
                rm = mrm.mejorMov()
                if rm:
                    mov = rm.movimiento()
                    if mov:
                        self.sts.setResult(self.work, self.ngroup, self.nfen, mov, t_dif)
                        self.grid.refresh()

        else:
            self.sts.save()
            self.calc_max()
            self.grid.refresh()
            self.tb.setAccionVisible(self.pause, False)
            self.tb.setAccionVisible(self.run, False)
            self.playing = False

        QTUtil.refresh_gui()

    def grid_num_datos(self, grid):
        return len(self.sts.groups)

    def grid_bold(self, grid, fila, oColumna):
        columna = oColumna.clave
        if columna.startswith("OTHER") or columna == "WORK":
            return self.dworks[columna].labels[fila].is_max
        return False

        # def grid_color_texto(self, grid, fila, oColumna):
        # columna = oColumna.clave
        # if columna.startswith("OTHER") or columna == "WORK":
        # mx_col = []
        # mx_pt = 0
        # for col, work in self.dworks.items():
        # pt = self.sts.xdonePoints(work, fila)
        # if pt:
        # if pt == mx_pt:
        # mx_col.append(col)
        # elif pt > mx_pt:
        # mx_col = [col]
        # mx_pt = pt
        # if columna in mx_col:
        # return self.colorMax
        # else:
        # return self.colorOth
        # return None

    def grid_dato(self, grid, fila, oColumna):
        columna = oColumna.clave
        group = self.sts.groups.group(fila)
        if columna == "GROUP":
            return group.name
        elif columna == "DONE":
            return self.sts.donePositions(self.work, fila)
        elif columna == "WORK":
            return self.sts.donePoints(self.work, fila)
        elif columna.startswith("OTHER"):
            return self.dworks[columna].labels[fila].label

    def read_work(self, work):
        tm = '%d"' % work.seconds if work.seconds else ""
        dp = "%d^" % work.depth if work.depth else ""
        r = Util.Record()
        r.title = "%s %s%s" % (work.ref, tm, dp)
        r.labels = []
        for ng in range(len(self.sts.groups)):
            rl = Util.Record()
            rl.points = self.sts.xdonePoints(work, ng)
            rl.label = self.sts.donePoints(work, ng)
            rl.is_max = False
            r.labels.append(rl)
        return r

    def read_works(self):
        d = {}
        nworks = len(self.sts.works)
        for xw in range(nworks):
            work = self.sts.works.getWork(xw)
            key = "OTHER%d" % xw if work != self.work else "WORK"
            d[key] = self.read_work(work)
        return d

    def calc_max(self):
        self.dworks["WORK"] = self.read_work(self.work)
        ngroups = len(self.sts.groups)
        for ng in range(ngroups):
            mx = 0
            st = set()
            for key, r in self.dworks.items():
                rl = r.labels[ng]
                pt = rl.points
                if pt > mx:
                    mx = pt
                    st = {key}
                elif pt > 0 and pt == mx:
                    st.add(key)
            for key, r in self.dworks.items():
                r.labels[ng].is_max = key in st


class WRun2(QTVarios.WDialogo):
    def __init__(self, wParent, sts, work, procesador):
        titulo = "%s - %s - %s" % (sts.name, work.ref, work.pathToExe())
        icono = Iconos.STS()
        extparam = "runsts2"
        QTVarios.WDialogo.__init__(self, wParent, titulo, icono, extparam)

        self.work = work
        self.sts = sts
        self.ngroup = -1
        self.xengine = procesador.creaGestorMotor(work.configEngine(), work.seconds * 1000, work.depth)
        self.xengine.set_direct()
        self.playing = False
        self.configuracion = procesador.configuracion

        # Toolbar
        li_acciones = [(_("Close"), Iconos.MainMenu(), self.cerrar), None,
                      (_("Run"), Iconos.Run(), self.run),
                      (_("Pause"), Iconos.Pelicula_Pausa(), self.pause), None,
                      ]
        self.tb = tb = Controles.TBrutina(self, li_acciones, tamIcon=24)

        # Board
        config_board = self.configuracion.config_board("STS", 32)
        self.tablero = Tablero.Tablero(self, config_board)
        self.tablero.crea()

        # Area resultados
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("GROUP", _("Group"), 180)
        o_columns.nueva("DONE", _("Done"), 100, centered=True)
        o_columns.nueva("WORK", _("Result"), 120, centered=True)

        self.dworks = self.read_works()
        self.calc_max()
        for x in range(len(self.sts.works)-1, -1, -1):
            work = self.sts.works.getWork(x)
            if work != self.work:
                key = "OTHER%d" % x
                reg = self.dworks[key]
                o_columns.nueva(key, reg.title, 120, centered=True)

        self.grid = Grid.Grid(self, o_columns, siSelecFilas=True)

        self.colorMax = QTUtil.qtColor("#840C24")
        self.colorOth = QTUtil.qtColor("#4668A6")

        layout = Colocacion.H()
        layout.control(self.tablero)
        layout.control(self.grid)
        layout.margen(3)

        ly = Colocacion.V().control(tb).otro(layout)

        self.setLayout(ly)

        self.restore_video(siTam=True, anchoDefecto=800, altoDefecto=430)

        resp = self.sts.siguientePosicion(self.work)
        if resp:
            self.tb.setAccionVisible(self.pause, False)
            self.tb.setAccionVisible(self.run, True)
        else:
            self.tb.setAccionVisible(self.pause, False)
            self.tb.setAccionVisible(self.run, False)

    def cerrar(self):
        self.sts.save()
        self.xengine.terminar()
        self.save_video()
        self.playing = False
        self.accept()

    def closeEvent(self, event):
        self.cerrar()

    def run(self):
        self.tb.setAccionVisible(self.pause, True)
        self.tb.setAccionVisible(self.run, False)
        QTUtil.refresh_gui()
        self.playing = True
        while self.playing:
            self.siguiente()

    def pause(self):
        self.tb.setAccionVisible(self.pause, False)
        self.tb.setAccionVisible(self.run, True)
        QTUtil.refresh_gui()
        self.playing = False
        self.sts.save()

    def siguiente(self):
        resp = self.sts.siguientePosicion(self.work)
        if resp:
            ngroup, self.nfen, self.elem = resp
            if ngroup != self.ngroup:
                self.calc_max()
                self.grid.refresh()
                self.ngroup = ngroup
            cp = Position.Position()
            cp.read_fen(self.elem.fen)
            self.tablero.setposition(cp)
            self.xengine.ponGuiDispatch(self.dispatch)
            xpt, xa1h8 = self.elem.bestA1H8()
            self.tablero.quitaFlechas()
            self.tablero.ponFlechaSC(xa1h8[:2], xa1h8[2:4])
            QTUtil.refresh_gui()
            if not self.playing:
                return
            t0 = time.time()
            mrm = self.xengine.analiza(self.elem.fen)
            t1 = time.time() - t0
            if mrm:
                rm = mrm.mejorMov()
                if rm:
                    mov = rm.movimiento()
                    if mov:
                        self.tablero.creaFlechaTmp(rm.from_sq, rm.to_sq, False)
                        self.sts.setResult(self.work, self.ngroup, self.nfen, mov, t1)
                        self.grid.refresh()
            else:
                self.pause()

        else:
            self.sts.save()
            self.calc_max()
            self.grid.refresh()
            self.tb.setAccionVisible(self.pause, False)
            self.tb.setAccionVisible(self.run, False)
            self.playing = False

        QTUtil.refresh_gui()

    def dispatch(self, rm):
        if rm.from_sq:
            self.tablero.creaFlechaTmp(rm.from_sq, rm.to_sq, False)
        QTUtil.refresh_gui()
        return self.playing

    def grid_num_datos(self, grid):
        return len(self.sts.groups)

    def grid_bold(self, grid, fila, oColumna):
        columna = oColumna.clave
        if columna.startswith("OTHER") or columna == "WORK":
            return self.dworks[columna].labels[fila].is_max
        return False

    def grid_dato(self, grid, fila, oColumna):
        columna = oColumna.clave
        group = self.sts.groups.group(fila)
        if columna == "GROUP":
            return group.name
        elif columna == "DONE":
            return self.sts.donePositions(self.work, fila)
        elif columna == "WORK":
            return self.sts.donePoints(self.work, fila)
        elif columna.startswith("OTHER"):
            return self.dworks[columna].labels[fila].label

    def read_work(self, work):
        tm = '%d"' % work.seconds if work.seconds else ''
        dp = "%d^" % work.depth if work.depth else ''
        r = Util.Record()
        r.title = "%s %s%s" % (work.ref, tm, dp)
        r.labels = []
        for ng in range(len(self.sts.groups)):
            rl = Util.Record()
            rl.points = self.sts.xdonePoints(work, ng)
            rl.label = self.sts.donePoints(work, ng)
            rl.is_max = False
            r.labels.append(rl)
        return r

    def read_works(self):
        d = {}
        nworks = len(self.sts.works)
        for xw in range(nworks):
            work = self.sts.works.getWork(xw)
            key = "OTHER%d" % xw if work != self.work else "WORK"
            d[key] = self.read_work(work)
        return d

    def calc_max(self):
        self.dworks["WORK"] = self.read_work(self.work)
        ngroups = len(self.sts.groups)
        for ng in range(ngroups):
            mx = 0
            st = set()
            for key, r in self.dworks.items():
                rl = r.labels[ng]
                pt = rl.points
                if pt > mx:
                    mx = pt
                    st = {key}
                elif pt > 0 and pt == mx:
                    st.add(key)
            for key, r in self.dworks.items():
                r.labels[ng].is_max = key in st



class WWork(QtWidgets.QDialog):
    def __init__(self, wParent, sts, work):
        super(WWork, self).__init__(wParent)

        self.work = work

        self.setWindowTitle(work.pathToExe())
        self.setWindowIcon(Iconos.Motor())
        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.Dialog
            | QtCore.Qt.WindowTitleHint
            | QtCore.Qt.WindowMinimizeButtonHint
            | QtCore.Qt.WindowMaximizeButtonHint
        )

        tb = QTUtil2.tbAcceptCancel(self)

        # Tabs
        tab = Controles.Tab()

        # Tab-basic --------------------------------------------------
        lbRef = Controles.LB(self, _("Reference") + ": ")
        self.edRef = Controles.ED(self, work.ref).anchoMinimo(360)

        lbInfo = Controles.LB(self, _("Information") + ": ")
        self.emInfo = Controles.EM(self, work.info, siHTML=False).anchoMinimo(360).altoFijo(60)

        lbDepth = Controles.LB(self, _("Maximum depth") + ": ")
        self.sbDepth = Controles.ED(self).tipoInt(work.depth).anchoFijo(30)

        lbSeconds = Controles.LB(self, _("Maximum seconds to think") + ": ")
        self.sbSeconds = Controles.ED(self).tipoFloat(float(work.seconds), decimales=3).anchoFijo(60)

        lbSample = Controles.LB(self, _("Sample") + ": ")
        self.sbIni = Controles.SB(self, work.ini + 1, 1, 100).capturaCambiado(self.changeSample)
        self.sbIni.isIni = True
        lbGuion = Controles.LB(self, _("to"))
        self.sbEnd = Controles.SB(self, work.end + 1, 1, 100).capturaCambiado(self.changeSample)
        self.sbEnd.isIni = False

        # self.lbError = Controles.LB(self).ponTipoLetra(peso=75).ponColorN("red")
        # self.lbError.hide()

        lySample = Colocacion.H().control(self.sbIni).control(lbGuion).control(self.sbEnd)
        ly = Colocacion.G()
        ly.controld(lbRef, 0, 0).control(self.edRef, 0, 1)
        ly.controld(lbInfo, 1, 0).control(self.emInfo, 1, 1)
        ly.controld(lbDepth, 2, 0).control(self.sbDepth, 2, 1)
        ly.controld(lbSeconds, 3, 0).control(self.sbSeconds, 3, 1)
        ly.controld(lbSample, 4, 0).otro(lySample, 4, 1)

        w = QtWidgets.QWidget()
        w.setLayout(ly)
        tab.nuevaTab(w, _("Basic data"))

        # Tab-Engine
        scrollArea = WEngines.wgen_options_engine(self, work.me)
        tab.nuevaTab(scrollArea, _("Engine options"))

        # Tab-Groups
        btAll = Controles.PB(self, _("All"), self.setAll, plano=False)
        btNone = Controles.PB(self, _("None"), self.setNone, plano=False)
        lyAN = Colocacion.H().control(btAll).espacio(10).control(btNone)
        self.liGroups = []
        ly = Colocacion.G()
        ly.columnaVacia(1, 10)
        num = len(sts.groups)
        mitad = num / 2 + num % 2

        for x in range(num):
            group = sts.groups.group(x)
            chb = Controles.CHB(self, _F(group.name), work.liGroupActive[x])
            self.liGroups.append(chb)
            col = 0 if x < mitad else 2
            fil = x % mitad

            ly.control(chb, fil, col)
        ly.otroc(lyAN, mitad, 0, numColumnas=3)

        w = QtWidgets.QWidget()
        w.setLayout(ly)
        tab.nuevaTab(w, _("Groups"))

        layout = Colocacion.V().control(tb).control(tab).margen(8)
        self.setLayout(layout)

        self.edRef.setFocus()

    def changeSample(self):
        vIni = self.sbIni.valor()
        vEnd = self.sbEnd.valor()
        p = self.sender()
        if vEnd < vIni:
            if p.isIni:
                self.sbEnd.ponValor(vIni)
            else:
                self.sbIni.ponValor(vEnd)

    def setAll(self):
        for group in self.liGroups:
            group.ponValor(True)

    def setNone(self):
        for group in self.liGroups:
            group.ponValor(False)

    def aceptar(self):
        self.work.ref = self.edRef.texto()
        self.work.info = self.emInfo.texto()
        self.work.depth = self.sbDepth.textoInt()
        self.work.seconds = self.sbSeconds.textoFloat()
        self.work.ini = self.sbIni.valor() - 1
        self.work.end = self.sbEnd.valor() - 1
        me = self.work.me
        WEngines.wsave_options_engine(me)
        for n, group in enumerate(self.liGroups):
            self.work.liGroupActive[n] = group.valor()
        self.accept()


class WUnSTS(QTVarios.WDialogo):
    def __init__(self, wParent, sts, procesador):
        titulo = sts.name
        icono = Iconos.STS()
        extparam = "unsts"
        QTVarios.WDialogo.__init__(self, wParent, titulo, icono, extparam)

        # Datos
        self.sts = sts
        self.procesador = procesador

        # Toolbar
        li_acciones = [(_("Close"), Iconos.MainMenu(), self.terminar), None,
                      (_("Run"), Iconos.Run(), self.wkRun), None,
                      ("+%s" % _("Board"), Iconos.Run2(), self.wkRun2), None,
                      (_("New"), Iconos.NuevoMas(), self.wkNew), None,
                      (_("Edit"), Iconos.Modificar(), self.wkEdit), None,
                      (_("Copy"), Iconos.Copiar(), self.wkCopy), None,
                      (_("Remove"), Iconos.Borrar(), self.wkRemove), None,
                      (_("Up"), Iconos.Arriba(), self.up),
                      (_("Down"), Iconos.Abajo(), self.down), None,
                      (_("Export"), Iconos.Grabar(), self.export), None,
                      (_("Config"), Iconos.Configurar(), self.configurar), None,
                      ]
        tb = Controles.TBrutina(self, li_acciones, tamIcon=24)

        # # Grid works
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("POS", _("N."), 30, centered=True)
        o_columns.nueva("REF", _("Reference"), 100)
        o_columns.nueva("TIME", _("Time"), 50, centered=True)
        o_columns.nueva("DEPTH", _("Depth"), 50, centered=True)
        o_columns.nueva("SAMPLE", _("Sample"), 50, centered=True)
        o_columns.nueva("RESULT", _("Result"), 150, centered=True)
        o_columns.nueva("ELO", _("Elo"), 80, centered=True)
        o_columns.nueva("WORKTIME", _("Work time"), 80, centered=True)
        for x in range(len(sts.groups)):
            group = sts.groups.group(x)
            o_columns.nueva("T%d" % x, group.name, 140, centered=True)
        self.grid = Grid.Grid(self, o_columns, siSelecFilas=True, siSeleccionMultiple=True)
        self.register_grid(self.grid)

        # Layout
        layout = Colocacion.V().control(tb).control(self.grid).margen(8)
        self.setLayout(layout)

        self.restore_video(siTam=True, anchoDefecto=800, altoDefecto=430)

        self.grid.gotop()

    def terminar(self):
        self.save_video()
        self.accept()

    def closeEvent(self, event):
        self.save_video()

    def configurar(self):
        menu = QTVarios.LCMenu(self)
        menu.opcion("formula", _("Formula to calculate elo"), Iconos.STS())
        resp = menu.lanza()
        if resp:
            X = self.sts.X
            K = self.sts.K
            while True:
                liGen = [(None, None)]
                liGen.append((None, "X * %s + K" % _("Result")))
                config = FormLayout.Editbox("X", 100, tipo=float, decimales=4)
                liGen.append((config, X))
                config = FormLayout.Editbox("K", 100, tipo=float, decimales=4)
                liGen.append((config, K))
                resultado = FormLayout.fedit(
                    liGen, title=_("Formula to calculate elo"), parent=self, icon=Iconos.Elo(), with_default=True
                )
                if resultado:
                    resp, valor = resultado
                    if resp == "defecto":
                        X = self.sts.Xdefault
                        K = self.sts.Kdefault
                    else:
                        x, k = valor
                        self.sts.formulaChange(x, k)
                        self.grid.refresh()
                        return
                else:
                    return

    def export(self):
        resp = QTUtil2.salvaFichero(
            self, _("CSV file"), Code.configuracion.x_save_folder, _("File") + " csv (*.csv)", True
        )
        if resp:
            self.sts.writeCSV(resp)

    def up(self):
        fila = self.grid.recno()
        if self.sts.up(fila):
            self.grid.goto(fila - 1, 0)
            self.grid.refresh()

    def down(self):
        fila = self.grid.recno()
        if self.sts.down(fila):
            self.grid.goto(fila + 1, 0)
            self.grid.refresh()

    def wkRun(self):
        fila = self.grid.recno()
        if fila >= 0:
            work = self.sts.getWork(fila)
            w = WRun(self, self.sts, work, self.procesador)
            w.exec_()

    def wkRun2(self):
        fila = self.grid.recno()
        if fila >= 0:
            work = self.sts.getWork(fila)
            w = WRun2(self, self.sts, work, self.procesador)
            w.exec_()

    def grid_doble_click(self, grid, fila, columna):
        self.wkRun()

    def wkEdit(self):
        fila = self.grid.recno()
        if fila >= 0:
            work = self.sts.getWork(fila)
            w = WWork(self, self.sts, work)
            if w.exec_():
                self.sts.save()

    def wkNew(self, work=None):
        if work is None or not work:
            me = WEngines.selectEngine(self)
            if not me:
                return
            work = self.sts.createWork(me)
        else:
            work.workTime = 0.0

        w = WWork(self, self.sts, work)
        if w.exec_():
            self.sts.addWork(work)
            self.sts.save()
            self.grid.refresh()
            self.grid.gobottom()
        return work

    def wkCopy(self):
        fila = self.grid.recno()
        if fila >= 0:
            work = self.sts.getWork(fila)
            self.wkNew(work.clone())

    def wkRemove(self):
        li = self.grid.recnosSeleccionados()
        if li:
            if QTUtil2.pregunta(self, _("Do you want to delete all selected records?")):
                li.sort(reverse=True)
                for fila in li:
                    self.sts.removeWork(fila)
                self.sts.save()
                self.grid.refresh()

    def grid_num_datos(self, grid):
        return len(self.sts.works)

    def grid_dato(self, grid, fila, oColumna):
        work = self.sts.works.lista[fila]
        columna = oColumna.clave
        if columna == "POS":
            return str(fila + 1)
        if columna == "REF":
            return work.ref
        if columna == "TIME":
            return str(work.seconds) if work.seconds else "-"
        if columna == "DEPTH":
            return str(work.depth) if work.depth else "-"
        if columna == "SAMPLE":
            return "%d-%d" % (work.ini + 1, work.end + 1)
        if columna == "RESULT":
            return str(self.sts.allPoints(work))
        if columna == "ELO":
            return self.sts.elo(work)
        if columna == "WORKTIME":
            secs = work.workTime
            if secs == 0.0:
                return "-"
            d = int(secs * 10) % 10
            s = int(secs) % 60
            m = int(secs) // 60
            return "%d' %02d.%d\"" % (m, s, d)
        test = int(columna[1:])
        return self.sts.donePoints(work, test)

    def grid_doble_clickCabecera(self, grid, oCol):
        if oCol.clave != "POS":
            self.sts.ordenWorks(oCol.clave)
            self.sts.save()
            self.grid.refresh()
            self.grid.gotop()


class WSTS(QTVarios.WDialogo):
    def __init__(self, wParent, procesador):

        titulo = _("STS: Strategic Test Suite")
        icono = Iconos.STS()
        extparam = "sts"
        QTVarios.WDialogo.__init__(self, wParent, titulo, icono, extparam)

        # Datos
        self.procesador = procesador
        self.carpetaSTS = procesador.configuracion.carpetaSTS
        self.lista = self.leeSTS()

        # Toolbar
        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.terminar),
            (_("Select"), Iconos.Seleccionar(), self.modificar),
            (_("New"), Iconos.NuevoMas(), self.crear),
            (_("Rename"), Iconos.Rename(), self.rename),
            (_("Copy"), Iconos.Copiar(), self.copiar),
            (_("Remove"), Iconos.Borrar(), self.borrar),
        )
        tb = Controles.TBrutina(self, li_acciones)
        if len(self.lista) == 0:
            for x in (self.modificar, self.borrar, self.copiar, self.rename):
                tb.setAccionVisible(x, False)

        # grid
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NOMBRE", _("Name"), 240)
        o_columns.nueva("FECHA", _("Date"), 120, centered=True)

        self.grid = Grid.Grid(self, o_columns, siSelecFilas=True)
        self.register_grid(self.grid)

        lb = Controles.LB(
            self,
            'STS %s: <b>Dan Corbit & Swaminathan</b> <a href="https://sites.google.com/site/strategictestsuite/about-1">%s</a>'
            % (_("Authors"), _("More info")),
        )

        # Layout
        layout = Colocacion.V().control(tb).control(self.grid).control(lb).margen(8)
        self.setLayout(layout)

        self.restore_video(siTam=True, anchoDefecto=400, altoDefecto=500)

        self.grid.gotop()

    def leeSTS(self):
        li = []
        Util.create_folder(self.carpetaSTS)
        for entry in Util.listdir(self.carpetaSTS):
            x = entry.name
            if x.lower().endswith(".sts"):
                st = entry.stat()
                li.append((x, st.st_ctime, st.st_mtime))

        sorted(li, key=lambda x: x[2], reverse=True)  # por ultima modificacin y al reves
        return li

    def grid_num_datos(self, grid):
        return len(self.lista)

    def grid_dato(self, grid, fila, oColumna):
        columna = oColumna.clave
        name, fcreacion, fmanten = self.lista[fila]
        if columna == "NOMBRE":
            return name[:-4]
        elif columna == "FECHA":
            tm = time.localtime(fmanten)
            return "%d-%02d-%d, %2d:%02d" % (tm.tm_mday, tm.tm_mon, tm.tm_year, tm.tm_hour, tm.tm_min)

    def terminar(self):
        self.save_video()
        self.accept()

    def grid_doble_click(self, grid, fila, columna):
        self.modificar()

    def modificar(self):
        n = self.grid.recno()
        if n >= 0:
            name = self.lista[n][0][:-4]
            sts = STS.STS(name)
            self.trabajar(sts)

    def nombreNum(self, num):
        return self.lista[num][0][:-4]

    def crear(self):
        name = self.editarNombre("", True)
        if name:
            sts = STS.STS(name)
            sts.save()
            self.grid.refresh()
            self.reread()
            self.trabajar(sts)

    def reread(self):
        self.lista = self.leeSTS()
        self.grid.refresh()

    def rename(self):
        n = self.grid.recno()
        if n >= 0:
            nombreOri = self.nombreNum(n)
            nombreDest = self.editarNombre(nombreOri)
            pathOri = os.path.join(self.carpetaSTS, nombreOri + ".sts")
            pathDest = os.path.join(self.carpetaSTS, nombreDest + ".sts")
            shutil.move(pathOri, pathDest)
            self.reread()

    def editarNombre(self, previo, siNuevo=False):
        while True:
            liGen = [(None, None)]
            liGen.append((_("Name") + ":", previo))
            resultado = FormLayout.fedit(liGen, title=_("STS: Strategic Test Suite"), parent=self, icon=Iconos.STS())
            if resultado:
                accion, liGen = resultado
                name = Util.valid_filename(liGen[0].strip())
                if name:
                    if not siNuevo and previo == name:
                        return None
                    path = os.path.join(self.carpetaSTS, name + ".sts")
                    if os.path.isfile(path):
                        QTUtil2.message_error(self, _("The file %s already exist") % name)
                        continue
                    return name
                else:
                    return None
            else:
                return None

    def trabajar(self, sts):
        w = WUnSTS(self, sts, self.procesador)
        w.exec_()

    def borrar(self):
        n = self.grid.recno()
        if n >= 0:
            name = self.nombreNum(n)
            if QTUtil2.pregunta(self, _X(_("Delete %1?"), name)):
                path = os.path.join(self.carpetaSTS, name + ".sts")
                os.remove(path)
                self.reread()

    def copiar(self):
        n = self.grid.recno()
        if n >= 0:
            nombreBase = self.nombreNum(n)
            name = self.editarNombre(nombreBase, True)
            if name:
                sts = STS.STS(nombreBase)
                sts.saveCopyNew(name)
                sts = STS.STS(name)
                self.reread()
                self.trabajar(sts)


def sts(procesador, parent):
    w = WSTS(parent, procesador)
    w.exec_()
