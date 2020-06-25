import atexit
import datetime
import random
import time

from PySide2 import QtWidgets, QtGui

from Code import Position
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import PantallaPotencia
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.QT import Tablero
from Code.SQL import Base
from Code import Util


class PuenteHistorico:
    def __init__(self, fichero, nivel):
        self.fichero = fichero
        self.nivel = nivel
        self.db = Base.DBBase(fichero)
        self.tabla = "Nivel%d" % self.nivel

        if not self.db.existeTabla(self.tabla):
            self.creaTabla()

        self.dbf = self.db.dbf(self.tabla, "FECHA,SEGUNDOS", orden="FECHA DESC")
        self.dbf.leer()
        self.calculaMedia()

        self.orden = "FECHA", "DESC"

        atexit.register(self.close)

    def close(self):
        if self.dbf:
            self.dbf.cerrar()
            self.dbf = None
        self.db.cerrar()

    def creaTabla(self):
        tb = Base.TablaBase(self.tabla)
        tb.nuevoCampo("FECHA", "VARCHAR", notNull=True, primaryKey=True)
        tb.nuevoCampo("SEGUNDOS", "FLOAT")
        tb.nuevoIndice("IND_SEGUNDOS%d" % self.nivel, "SEGUNDOS")
        self.db.generarTabla(tb)

    def calculaMedia(self):
        ts = 0.0
        n = self.dbf.reccount()
        self.mejor = 99999999.0
        for x in range(n):
            self.dbf.goto(x)
            s = self.dbf.SEGUNDOS
            if s < self.mejor:
                self.mejor = s
            ts += s
        self.media = ts * 1.0 / n if n else 0.0

    def __len__(self):
        return self.dbf.reccount()

    def goto(self, num):
        self.dbf.goto(num)

    def ponOrden(self, key):
        nat, orden = self.orden
        if key == nat:
            orden = "DESC" if orden == "ASC" else "ASC"
        else:
            nat = key
            orden = "DESC" if key == "FECHA" else "ASC"
        self.dbf.ponOrden(nat + " " + orden)
        self.orden = nat, orden

        self.dbf.leer()
        self.dbf.gotop()

    def fecha2txt(self, fecha):
        return "%4d%02d%02d%02d%02d%02d" % (fecha.year, fecha.month, fecha.day, fecha.hour, fecha.minute, fecha.second)

    def txt2fecha(self, txt):
        def x(d, h):
            return int(txt[d:h])

        year = x(0, 4)
        month = x(4, 6)
        day = x(6, 8)
        hour = x(8, 10)
        minute = x(10, 12)
        second = x(12, 14)
        fecha = datetime.datetime(year, month, day, hour, minute, second)
        return fecha

    def append(self, fecha, segundos):
        br = self.dbf.baseRegistro()
        br.FECHA = self.fecha2txt(fecha)
        br.SEGUNDOS = segundos
        self.dbf.insertar(br)
        self.calculaMedia()

    def __getitem__(self, num):
        self.dbf.goto(num)
        reg = self.dbf.registroActual()
        reg.FECHA = self.txt2fecha(reg.FECHA)
        return reg

    def borrarLista(self, liNum):
        self.dbf.borrarLista(liNum)
        self.dbf.pack()
        self.dbf.leer()
        self.calculaMedia()


class EDCelda(Controles.ED):
    def focusOutEvent(self, event):
        self.parent.focusOut(self)
        Controles.ED.focusOutEvent(self, event)


class WEdMove(QtWidgets.QWidget):
    def __init__(self, owner, conj_piezas, is_white):
        QtWidgets.QWidget.__init__(self)

        self.owner = owner

        self.conj_piezas = conj_piezas

        self.filaPromocion = (7, 8) if is_white else (2, 1)

        self.menuPromocion = self.creaMenuPiezas("QRBN ", is_white)

        self.promocion = " "

        self.origen = (
            EDCelda(self, "")
            .caracteres(2)
            .controlrx("(|[a-h][1-8])")
            .anchoFijo(32)
            .alinCentrado()
            .capturaCambiado(self.miraPromocion)
        )

        self.flecha = flecha = Controles.LB(self).ponImagen(Iconos.pmMover())

        self.destino = (
            EDCelda(self, "")
            .caracteres(2)
            .controlrx("(|[a-h][1-8])")
            .anchoFijo(32)
            .alinCentrado()
            .capturaCambiado(self.miraPromocion)
        )

        self.pbPromocion = Controles.PB(self, "", self.pulsadoPromocion, plano=False).anchoFijo(24)

        ly = (
            Colocacion.H()
            .relleno()
            .control(self.origen)
            .espacio(2)
            .control(flecha)
            .espacio(2)
            .control(self.destino)
            .control(self.pbPromocion)
            .margen(0)
            .relleno()
        )
        self.setLayout(ly)

        self.miraPromocion()

    def focusOut(self, quien):
        self.owner.ponUltimaCelda(quien)

    def activa(self):
        self.setFocus()
        self.origen.setFocus()

    def activaDestino(self):
        self.setFocus()
        self.destino.setFocus()

    def resultado(self):
        from_sq = to_sq = ""

        from_sq = self.origen.texto()
        if len(from_sq) != 2:
            from_sq = ""

        to_sq = self.destino.texto()
        if len(to_sq) != 2:
            from_sq = ""

        return from_sq, to_sq, self.promocion.strip()

    def deshabilita(self):
        self.origen.deshabilitado(True)
        self.destino.deshabilitado(True)
        self.pbPromocion.setEnabled(False)
        if not self.origen.texto() or not self.destino.texto():
            self.origen.hide()
            self.destino.hide()
            self.pbPromocion.hide()
            self.flecha.hide()

    def habilita(self):
        self.origen.deshabilitado(False)
        self.destino.deshabilitado(False)
        self.pbPromocion.setEnabled(True)
        self.origen.show()
        self.destino.show()
        self.flecha.show()
        self.miraPromocion()

    def limpia(self):
        self.origen.ponTexto("")
        self.destino.ponTexto("")
        self.habilita()

    def miraPromocion(self):
        show = True
        ori, dest = self.filaPromocion
        txtO = self.origen.texto()
        if len(txtO) < 2 or int(txtO[-1]) != ori:
            show = False
        if show:
            txtD = self.destino.texto()
            if len(txtD) < 2 or int(txtD[-1]) != dest:
                show = False
        self.pbPromocion.setVisible(show)
        return show

    def pulsadoPromocion(self):
        if not self.miraPromocion():
            return
        resp = self.menuPromocion.exec_(QtGui.QCursor.pos())
        if resp is not None:
            icono = self.conj_piezas.icono(resp.key) if resp.key else QtGui.QIcon()
            self.pbPromocion.ponIcono(icono)
            self.promocion = resp.key

    def creaMenuPiezas(self, lista, is_white):
        menu = QtWidgets.QMenu(self)

        dic = {"K": _("King"), "Q": _("Queen"), "R": _("Rook"), "B": _("Bishop"), "N": _("Knight"), "P": _("Pawn")}

        for pz in lista:
            if pz == " ":
                icono = QtGui.QIcon()
                txt = _("Remove")
            else:
                txt = dic[pz]
                if not is_white:
                    pz = pz.lower()
                icono = self.conj_piezas.icono(pz)

            accion = QtWidgets.QAction(icono, txt, menu)

            accion.key = pz.strip()
            menu.addAction(accion)

        return menu


class WPuenteBase(QTVarios.WDialogo):
    def __init__(self, procesador, nivel):

        titulo = "%s. %s %d" % (_("Moves between two positions"), _("Level"), nivel)
        QTVarios.WDialogo.__init__(self, procesador.main_window, titulo, Iconos.Puente(), "puenteBase")

        self.procesador = procesador
        self.configuracion = procesador.configuracion
        self.nivel = nivel

        self.historico = PuenteHistorico(self.configuracion.ficheroPuente, nivel)

        self.colorMejorFondo = QTUtil.qtColorRGB(150, 104, 145)
        self.colorBien = QTUtil.qtColorRGB(0, 0, 255)
        self.colorMal = QTUtil.qtColorRGB(255, 72, 72)
        self.colorMejor = QTUtil.qtColorRGB(255, 255, 255)

        # Historico
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("FECHA", _("Date"), 120, centered=True)
        o_columns.nueva("SEGUNDOS", _("Second(s)"), 120, centered=True)
        self.ghistorico = Grid.Grid(self, o_columns, siSelecFilas=True, siSeleccionMultiple=True)
        self.ghistorico.setMinimumWidth(self.ghistorico.anchoColumnas() + 20)

        # Tool bar
        li_acciones = (
            (_("Close"), Iconos.MainMenu(), "terminar"),
            None,
            (_("Start"), Iconos.Empezar(), "empezar"),
            (_("Remove"), Iconos.Borrar(), "borrar"),
            None,
        )
        self.tb = Controles.TB(self, li_acciones)
        self.pon_toolbar("terminar", "empezar", "borrar")

        # Colocamos
        lyTB = Colocacion.H().control(self.tb).margen(0)
        ly = Colocacion.V().otro(lyTB).control(self.ghistorico).margen(3)

        self.setLayout(ly)

        self.register_grid(self.ghistorico)
        self.restore_video(siTam=False)

        self.ghistorico.gotop()

    def grid_doble_clickCabecera(self, grid, oColumna):
        self.historico.ponOrden(oColumna.clave)
        self.ghistorico.gotop()
        self.ghistorico.refresh()

    def grid_num_datos(self, grid):
        return len(self.historico)

    def grid_dato(self, grid, fila, oColumna):
        col = oColumna.clave
        reg = self.historico[fila]
        if col == "FECHA":
            return Util.localDateT(reg.FECHA)
        elif col == "SEGUNDOS":
            return "%.02f" % reg.SEGUNDOS

    def grid_color_texto(self, grid, fila, oColumna):
        segs = self.historico[fila].SEGUNDOS

        if segs == self.historico.mejor:
            return self.colorMejor
        if segs > self.historico.media:
            return self.colorMal
        return self.colorBien

    def grid_color_fondo(self, grid, fila, oColumna):
        segs = self.historico[fila].SEGUNDOS

        if segs == self.historico.mejor:
            return self.colorMejorFondo
        return None

    def process_toolbar(self):
        accion = self.sender().clave
        if accion == "terminar":
            self.save_video()
            self.historico.close()
            self.reject()

        elif accion == "empezar":
            self.empezar()

        elif accion == "borrar":
            self.borrar()

    def borrar(self):
        li = self.ghistorico.recnosSeleccionados()
        if len(li) > 0:
            if QTUtil2.pregunta(self, _("Do you want to delete all selected records?")):
                self.historico.borrarLista(li)
        self.ghistorico.gotop()
        self.ghistorico.refresh()

    def pon_toolbar(self, *li_acciones):

        self.tb.clear()
        for k in li_acciones:
            self.tb.dicTB[k].setVisible(True)
            self.tb.dicTB[k].setEnabled(True)
            self.tb.addAction(self.tb.dicTB[k])

        self.tb.li_acciones = li_acciones
        self.tb.update()

    def dameOtro(self):
        game, dicPGN, info, jugadaInicial, linea = PantallaPotencia.lee_linea_mfn()
        # Tenemos 10 num_moves validas from_sq jugadaInicial
        n = random.randint(jugadaInicial, jugadaInicial + 10 - self.nivel)
        fenIni = game.move(n).position_before.fen()
        liMV = []
        for x in range(self.nivel):
            move = game.move(x + n)
            mv = move.movimiento()
            liMV.append(mv)
        fenFin = game.move(n + self.nivel).position_before.fen()
        return fenIni, fenFin, liMV, info

    def empezar(self):
        fenIni, fenFin, liMV, info = self.dameOtro()
        w = WPuente(self, fenIni, fenFin, liMV, info)
        w.exec_()
        self.ghistorico.gotop()
        self.ghistorico.refresh()


class WPuente(QTVarios.WDialogo):
    def __init__(self, owner, fenIni, fenFin, liMV, info):

        QTVarios.WDialogo.__init__(self, owner, _("Moves between two positions"), Iconos.Puente(), "puente")

        self.owner = owner
        self.historico = owner.historico
        self.procesador = owner.procesador
        self.configuracion = self.procesador.configuracion

        self.liMV = liMV
        self.fenIni = fenIni
        self.fenFin = fenFin

        nivel = len(liMV)

        # Tableros
        config_board = self.configuracion.config_board("PUENTE", 32)

        cpIni = Position.Position()
        cpIni.read_fen(fenIni)
        is_white = cpIni.is_white
        self.tableroIni = Tablero.TableroEstatico(self, config_board)
        self.tableroIni.crea()
        self.tableroIni.ponerPiezasAbajo(is_white)
        self.tableroIni.ponPosicion(cpIni)

        cpFin = Position.Position()
        cpFin.read_fen(fenFin)
        self.tableroFin = Tablero.TableroEstatico(self, config_board)
        self.tableroFin.crea()
        self.tableroFin.ponerPiezasAbajo(is_white)  # esta bien
        self.tableroFin.ponPosicion(cpFin)

        # Rotulo informacion
        self.lbInformacion = Controles.LB(self, self.textoLBInformacion(info, cpIni)).alinCentrado()

        # Rotulo vtime
        self.lbTiempo = Controles.LB(self, "").alinCentrado()

        # Movimientos
        self.liwm = []
        conj_piezas = self.tableroIni.piezas
        ly = Colocacion.V().margen(4).relleno()
        for i in range(nivel):
            wm = WEdMove(self, conj_piezas, is_white)
            self.liwm.append(wm)
            is_white = not is_white
            ly.control(wm)
        ly.relleno()
        gbMovs = Controles.GB(self, _("Next moves"), ly).ponFuente(Controles.TipoLetra(puntos=10, peso=75))

        # Botones
        f = Controles.TipoLetra(puntos=12, peso=75)
        self.btComprobar = (
            Controles.PB(self, _("Check"), self.comprobar, plano=False)
            .ponIcono(Iconos.Check(), tamIcon=32)
            .ponFuente(f)
        )
        self.btSeguir = (
            Controles.PB(self, _("Continue"), self.seguir, plano=False)
            .ponIcono(Iconos.Pelicula_Seguir(), tamIcon=32)
            .ponFuente(f)
        )
        self.btTerminar = (
            Controles.PB(self, _("Close"), self.terminar, plano=False)
            .ponIcono(Iconos.MainMenu(), tamIcon=32)
            .ponFuente(f)
        )
        self.btCancelar = (
            Controles.PB(self, _("Cancel"), self.terminar, plano=False)
            .ponIcono(Iconos.Cancelar(), tamIcon=32)
            .ponFuente(f)
        )

        # Layout
        lyC = (
            Colocacion.V()
            .control(self.btCancelar)
            .control(self.btTerminar)
            .relleno()
            .control(gbMovs)
            .relleno(1)
            .control(self.btComprobar)
            .control(self.btSeguir)
            .relleno()
        )
        lyTM = Colocacion.H().control(self.tableroIni).otro(lyC).control(self.tableroFin).relleno()

        ly = Colocacion.V().otro(lyTM).controlc(self.lbInformacion).controlc(self.lbTiempo).relleno().margen(3)

        self.setLayout(ly)

        self.restore_video()
        self.adjustSize()

        # Tiempo
        self.time_base = time.time()

        self.btSeguir.hide()
        self.btTerminar.hide()

        self.liwm[0].activa()

        self.ultimaCelda = None

    def pulsada_celda(self, celda):
        if self.ultimaCelda:
            self.ultimaCelda.ponTexto(celda)

            ucld = self.ultimaCelda
            for num, wm in enumerate(self.liwm):
                if wm.origen == ucld:
                    wm.miraPromocion()
                    wm.activaDestino()
                    self.ultimaCelda = wm.destino
                    return
                elif wm.destino == ucld:
                    wm.miraPromocion()
                    if num < (len(self.liwm) - 1):
                        x = num + 1
                    else:
                        x = 0
                    wm = self.liwm[x]
                    wm.activa()
                    self.ultimaCelda = wm.origen
                    return

    def ponUltimaCelda(self, wmcelda):
        self.ultimaCelda = wmcelda

    def closeEvent(self, event):
        self.save_video()
        event.accept()

    def process_toolbar(self):
        accion = self.sender().clave
        if accion in ["terminar", "cancelar"]:
            self.save_video()
            self.reject()
        elif accion == "comprobar":
            self.comprobar()
        elif accion == "seguir":
            self.seguir()

    def terminar(self):
        self.save_video()
        self.reject()

    def seguir(self):

        fenIni, fenFin, liMV, info = self.owner.dameOtro()
        self.liMV = liMV
        self.fenIni = fenIni
        self.fenFin = fenFin

        # Tableros
        cpIni = Position.Position()
        cpIni.read_fen(fenIni)
        is_white = cpIni.is_white
        self.tableroIni.ponerPiezasAbajo(is_white)
        self.tableroIni.ponPosicion(cpIni)

        cpFin = Position.Position()
        cpFin.read_fen(fenFin)
        self.tableroFin.ponerPiezasAbajo(is_white)  # esta bien
        self.tableroFin.ponPosicion(cpFin)

        # Rotulo informacion
        self.lbInformacion.ponTexto(self.textoLBInformacion(info, cpIni))

        # Rotulo vtime
        self.lbTiempo.ponTexto("")

        for wm in self.liwm:
            wm.limpia()

        self.time_base = time.time()

        self.btComprobar.show()
        self.btSeguir.hide()
        self.btCancelar.show()
        self.btTerminar.hide()

        self.liwm[0].activa()

    def correcto(self):
        segundos = float(time.time() - self.time_base)
        self.lbTiempo.ponTexto("<h2>%s</h2>" % _X(_("Right, it took %1 seconds."), "%.02f" % segundos))

        self.historico.append(Util.today(), segundos)

        self.btComprobar.hide()
        self.btSeguir.show()
        self.btCancelar.hide()
        self.btTerminar.show()

    def incorrecto(self):
        QTUtil2.mensajeTemporal(self, _("Wrong"), 2)
        for wm in self.liwm:
            wm.habilita()
        self.liwm[0].activa()

    def comprobar(self):
        for wm in self.liwm:
            wm.deshabilita()

        cp = Position.Position()
        cp.read_fen(self.fenIni)
        for wm in self.liwm:
            from_sq, to_sq, promotion = wm.resultado()
            if not from_sq or not to_sq:
                self.incorrecto()
                return

            siBien, mensaje = cp.mover(from_sq, to_sq, promotion)
            if not siBien:
                self.incorrecto()
                return
        if cp.fen() == self.fenFin:
            self.correcto()
        else:
            self.incorrecto()

    def textoLBInformacion(self, info, cp):

        color, colorR = _("White"), _("Black")
        cK, cQ, cKR, cQR = "K", "Q", "k", "q"

        mens = ""

        if cp.castles:

            def menr(ck, cq):
                enr = ""
                if ck in cp.castles:
                    enr += "O-O"
                if cq in cp.castles:
                    if enr:
                        enr += "  +  "
                    enr += "O-O-O"
                return enr

            enr = menr(cK, cQ)
            if enr:
                mens += "  %s : %s" % (color, enr)
            enr = menr(cKR, cQR)
            if enr:
                mens += " %s : %s" % (colorR, enr)
        if cp.en_passant != "-":
            mens += "     %s : %s" % (_("En passant"), cp.en_passant)

        if mens:
            mens = "<b>%s</b><br>" % mens
        mens += info

        mens = "<center>%s</center>" % mens

        return mens


def pantallaPuente(procesador, nivel):
    w = WPuenteBase(procesador, nivel)
    w.exec_()