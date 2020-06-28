import os

from PySide2 import QtCore, QtWidgets

from Code import Util
from Code.SQL import UtilSQL
from Code.Polyglots import Books
from Code import Position
from Code import Personalidades
from Code.QT import Colocacion
from Code.QT import Controles
from Code.QT import FormLayout
from Code.QT import Iconos
from Code.QT import Motores
from Code.Openings import PantallaOpenings
from Code.Engines import WEngines
from Code.QT import PantallaTutor
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.QT import Grid
from Code.QT import Columnas
from Code.QT import Voyager
from Code.QT import Delegados
from Code.Constantes import *


class WEntMaquina(QTVarios.WDialogo):
    def __init__(self, procesador, titulo):

        QTVarios.WDialogo.__init__(self, procesador.main_window, titulo, Iconos.Libre(), "entMaquina")

        font = Controles.TipoLetra(puntos=procesador.configuracion.x_menu_points)

        self.setFont(font)

        self.configuracion = procesador.configuracion
        self.procesador = procesador

        self.personalidades = Personalidades.Personalidades(self, self.configuracion)

        self.motores = Motores.Motores(self.configuracion)

        # Toolbar
        li_acciones = [
            (_("Accept"), Iconos.Aceptar(), self.aceptar),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.cancelar),
            None,
            (_("Configurations"), Iconos.Configurar(), self.configuraciones),
            None,
        ]
        tb = QTVarios.LCTB(self, li_acciones)

        # Tab
        tab = Controles.Tab()
        tab.dispatchChange(self.cambiada_tab)

        self.tab_advanced = 4  # está en la posición 4
        self.tab_advanced_active = (
            False
        )  # Para no tener que leer las opciones uci to_sq que no sean necesarias, afecta a gridNumDatos

        def nueva_tab(layout, titulo):
            ly = Colocacion.V()
            ly.otro(layout)
            ly.relleno()
            w = QtWidgets.QWidget(self)
            w.setLayout(ly)
            w.setFont(font)
            tab.nuevaTab(w, titulo)

        def nuevoG():
            ly_g = Colocacion.G()
            ly_g.filaActual = 0
            ly_g.setMargin(10)
            return ly_g

        gbStyle = """
            QGroupBox {
                font: bold 16px;
                background-color: #F2F2EC;/*qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #E0E0E0, stop: 1 #FFFFFF);*/
                border: 1px solid gray;
                border-radius: 3px;
                padding: 18px;
                margin-top: 5ex; /* leave space at the top for the title */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left; /* position at the top center */
                padding: 8px;
                border: 1px solid gray;
             }
        """

        def _label(ly_g, txt, xlayout, rutinaCHB=None, siCheck: object = False):
            groupbox = Controles.GB(self, txt, xlayout)
            if rutinaCHB:
                groupbox.conectar(rutinaCHB)
            elif siCheck:
                groupbox.setCheckable(True)
                groupbox.setChecked(False)

            groupbox.setStyleSheet(gbStyle)
            groupbox.setMinimumWidth(640)
            groupbox.setFont(font)
            ly_g.controlc(groupbox, ly_g.filaActual, 0)
            ly_g.filaActual += 1
            return groupbox

        # ##################################################################################################################################
        # TAB General
        # ##################################################################################################################################

        lyG = nuevoG()

        # # Motores

        # ## Rival
        self.rival = self.procesador.XTutor().confMotor
        self.rivalTipo = Motores.INTERNO
        self.btRival = Controles.PB(self, "", self.cambiaRival, plano=False).ponFuente(font).altoFijo(48)

        lbTiempoSegundosR = Controles.LB2P(self, _("Fixed time in seconds")).ponFuente(font)
        self.edRtiempo = (
            Controles.ED(self).tipoFloat().anchoMaximo(50).ponFuente(font).capturaCambiado(self.cambiadoTiempo)
        )
        bt_cancelar_tiempo = Controles.PB(self, "", rutina=self.cancelar_tiempo).ponIcono(Iconos.S_Cancelar())
        ly_tiempo = Colocacion.H().control(self.edRtiempo).control(bt_cancelar_tiempo).relleno(1)

        lb_depth = Controles.LB2P(self, _("Fixed depth")).ponFuente(font)
        self.edRdepth = Controles.ED(self).tipoInt().anchoMaximo(50).ponFuente(font).capturaCambiado(self.cambiadoDepth)
        bt_cancelar_depth = Controles.PB(self, "", rutina=self.cancelar_depth).ponIcono(Iconos.S_Cancelar())
        ly_depth = Colocacion.H().control(self.edRdepth).control(bt_cancelar_depth).relleno(1)

        ly = Colocacion.G()
        ly.controld(lbTiempoSegundosR, 0, 0).otro(ly_tiempo, 0, 1)
        ly.controld(lb_depth, 1, 0).otro(ly_depth, 1, 1)
        self.gb_thinks = Controles.GB(self, _("Limits of engine thinking"), ly)
        self.gb_thinks.setStyleSheet(
            """
            QGroupBox {
                font: bold %d;
                background-color: #F2F2EC;/*qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #E0E0E0, stop: 1 #FFFFFF);*/
                border: 1px solid gray;
                border-radius: 3px;
                padding: 18px;
                margin-top: 5ex; /* leave space at the top for the title */
            }
            QGroupBox::title {
                subcontrol-position: top center; /* position at the top center */
                padding: 8px;
                border: 1px solid gray;
             }
        """
            % procesador.configuracion.x_menu_points
        )
        lyV = Colocacion.V().espacio(20).control(self.btRival).espacio(20).control(self.gb_thinks)

        _label(lyG, _("Opponent"), lyV)

        # # Color
        self.rbBlancas = Controles.RB(self, "").activa()
        self.rbBlancas.setIcon(Iconos.PeonBlanco())
        self.rbBlancas.setIconSize(QtCore.QSize(32, 32))
        self.rbNegras = Controles.RB(self, "")
        self.rbNegras.setIcon(Iconos.PeonNegro())
        self.rbNegras.setIconSize(QtCore.QSize(32, 32))
        self.rbRandom = Controles.RB(self, _("Random"))
        self.rbRandom.setFont(Controles.TipoLetra(puntos=16))
        hbox = (
            Colocacion.H()
            .relleno()
            .control(self.rbBlancas)
            .espacio(30)
            .control(self.rbNegras)
            .espacio(30)
            .control(self.rbRandom)
            .relleno()
        )
        _label(lyG, _("Side you play with"), hbox)

        nueva_tab(lyG, _("Basic configuration"))

        # ##################################################################################################################################
        # TAB Ayudas
        # ##################################################################################################################################
        self.chbSummary = Controles.CHB(
            self, _("Save a summary when the game is finished in the main comment"), False
        ).ponFuente(font)

        # # Tutor
        lbAyudas = Controles.LB2P(self, _("Available hints")).ponFuente(font)
        liAyudas = [(_("Maximum"), 999)]
        for i in range(1, 21):
            liAyudas.append((str(i), i))
        for i in range(25, 51, 5):
            liAyudas.append((str(i), i))
        self.cbAyudas = Controles.CB(self, liAyudas, 999).ponFuente(font)
        self.chbChance = Controles.CHB(self, _("Second chance"), True).ponFuente(font)
        btTutorChange = (
            Controles.PB(self, _("Tutor change"), self.tutorChange, plano=False)
            .ponIcono(Iconos.Tutor(), tamIcon=16)
            .ponFuente(font)
        )

        liThinks = [(_("Nothing"), -1), (_("Score"), 0)]
        for i in range(1, 5):
            liThinks.append(("%d %s" % (i, _("ply") if i == 1 else _("plies")), i))
        liThinks.append((_("All"), 9999))
        lbThoughtTt = Controles.LB(self, _("It is showed") + ":").ponFuente(font)
        self.cbThoughtTt = Controles.CB(self, liThinks, -1).ponFuente(font)

        self.chbContinueTt = Controles.CHB(self, _("The tutor thinks while you think"), True).ponFuente(font)

        lbBoxHeight = Controles.LB2P(self, _("Box height")).ponFuente(font)
        self.sbBoxHeight = Controles.SB(self, 7, 0, 999).tamMaximo(50).ponFuente(font)

        lbArrows = Controles.LB2P(self, _("Arrows with the best moves")).ponFuente(font)
        self.sbArrowsTt = Controles.SB(self, 3, 0, 999).tamMaximo(50).ponFuente(font)

        lyT1 = Colocacion.H().control(lbAyudas).control(self.cbAyudas).relleno()
        lyT1.control(self.chbChance).relleno().control(btTutorChange)
        lyT2 = Colocacion.H().control(self.chbContinueTt).relleno()
        lyT2.control(lbBoxHeight).control(self.sbBoxHeight).relleno()
        lyT3 = Colocacion.H().control(lbThoughtTt).control(self.cbThoughtTt).relleno()
        lyT3.control(lbArrows).control(self.sbArrowsTt)

        ly = Colocacion.V().otro(lyT1).espacio(16).otro(lyT2).otro(lyT3).relleno()

        self.gbTutor = Controles.GB(self, _("Activate the tutor's help"), ly)
        self.gbTutor.setCheckable(True)
        self.gbTutor.setStyleSheet(gbStyle)

        lb = Controles.LB(self, _("It is showed") + ":").ponFuente(font)
        self.cbThoughtOp = Controles.CB(self, liThinks, -1).ponFuente(font)
        lbArrows = Controles.LB2P(self, _("Arrows to show")).ponFuente(font)
        self.sbArrows = Controles.SB(self, 7, 0, 999).tamMaximo(50).ponFuente(font)
        ly = Colocacion.H().control(lb).control(self.cbThoughtOp).relleno()
        ly.control(lbArrows).control(self.sbArrows).relleno()
        gbThoughtOp = Controles.GB(self, _("Opponent's thought information"), ly)
        gbThoughtOp.setStyleSheet(gbStyle)

        ly = Colocacion.V().espacio(16).control(self.gbTutor).control(gbThoughtOp)
        ly.espacio(16).control(self.chbSummary).margen(6)

        nueva_tab(ly, _("Help configuration"))

        # ##################################################################################################################################
        # TAB Tiempo
        # ##################################################################################################################################
        lyG = nuevoG()

        self.lbMinutos = Controles.LB(self, _("Total minutes") + ":").ponFuente(font)
        self.edMinutos = Controles.ED(self).tipoFloat(10.0).ponFuente(font).anchoFijo(50)
        self.edSegundos, self.lbSegundos = QTUtil2.spinBoxLB(
            self, 6, -999, 999, maxTam=54, etiqueta=_("Seconds added per move"), fuente=font
        )
        self.edMinExtra, self.lbMinExtra = QTUtil2.spinBoxLB(
            self, 0, -999, 999, maxTam=70, etiqueta=_("Extra minutes for the player"), fuente=font
        )
        self.edZeitnot, self.lbZeitnot = QTUtil2.spinBoxLB(
            self, 0, -999, 999, maxTam=54, etiqueta=_("Zeitnot: alarm sounds when remaining seconds"), fuente=font
        )
        lyH = Colocacion.H()
        lyH.control(self.lbMinutos).control(self.edMinutos).espacio(30)
        lyH.control(self.lbSegundos).control(self.edSegundos).relleno()
        lyH2 = Colocacion.H()
        lyH2.control(self.lbMinExtra).control(self.edMinExtra).relleno()
        lyH3 = Colocacion.H()
        lyH3.control(self.lbZeitnot).control(self.edZeitnot).relleno()
        ly = Colocacion.V().otro(lyH).otro(lyH2).otro(lyH3)
        self.chbTiempo = _label(lyG, _("Activate the time control"), ly, siCheck=True)

        nueva_tab(lyG, _("Time"))

        # ##################################################################################################################################
        # TAB Initial moves
        # ##################################################################################################################################
        lyG = nuevoG()

        # Posicion
        self.btPosicion = (
            Controles.PB(self, " " * 5 + _("Change") + " " * 5, self.posicionEditar).ponPlano(False).ponFuente(font)
        )
        self.fen = ""
        self.btPosicionQuitar = Controles.PB(self, "", self.posicionQuitar).ponIcono(Iconos.Motor_No()).ponFuente(font)
        self.btPosicionPegar = (
            Controles.PB(self, "", self.posicionPegar).ponIcono(Iconos.Pegar16()).ponToolTip(_("Paste FEN position"))
        ).ponFuente(font)
        hbox = (
            Colocacion.H()
            .relleno()
            .control(self.btPosicionQuitar)
            .control(self.btPosicion)
            .control(self.btPosicionPegar)
            .relleno()
        )
        _label(lyG, _("Start position"), hbox)

        # Aperturas
        self.btApertura = (
            Controles.PB(self, " " * 5 + _("Undetermined") + " " * 5, self.editarApertura)
            .ponPlano(False)
            .ponFuente(font)
        )
        self.bloqueApertura = None
        self.btAperturasFavoritas = Controles.PB(self, "", self.aperturasFavoritas).ponIcono(Iconos.Favoritos())
        self.btAperturasQuitar = Controles.PB(self, "", self.aperturasQuitar).ponIcono(Iconos.Motor_No())
        hbox = (
            Colocacion.H()
            .relleno()
            .control(self.btAperturasQuitar)
            .control(self.btApertura)
            .control(self.btAperturasFavoritas)
            .relleno()
        )
        _label(lyG, _("Opening"), hbox)

        # Libros
        fvar = self.configuracion.ficheroBooks
        self.listaLibros = Books.ListaLibros()
        self.listaLibros.restore_pickle(fvar)
        self.listaLibros.comprueba()

        li_books = [(x.name, x) for x in self.listaLibros.lista]
        libInicial = li_books[0][1] if li_books else None

        li_resp_book = [
            (_("Selected by the player"), "su"),
            (_("Uniform random"), "au"),
            (_("Proportional random"), "ap"),
            (_("Always the highest percentage"), "mp"),
        ]

        ## Rival
        self.cbBooksR = QTUtil2.comboBoxLB(self, li_books, libInicial).ponFuente(font)
        self.btNuevoBookR = Controles.PB(self, "", self.nuevoBook, plano=True).ponIcono(Iconos.Mas(), tamIcon=16)
        self.cbBooksRR = QTUtil2.comboBoxLB(self, li_resp_book, "mp").ponFuente(font)
        self.lbDepthBookR = Controles.LB2P(self, _("Max depth")).ponFuente(font)
        self.edDepthBookR = Controles.ED(self).ponFuente(font).tipoInt(0).anchoFijo(30)

        hbox = (
            Colocacion.H()
            .control(self.cbBooksR)
            .control(self.btNuevoBookR)
            .relleno()
            .control(self.cbBooksRR)
            .relleno()
            .control(self.lbDepthBookR)
            .control(self.edDepthBookR)
        )
        self.chbBookR = _label(lyG, "%s: %s" % (_("Activate book"), _("Opponent")), hbox, siCheck=True)

        ## Player
        self.cbBooksP = QTUtil2.comboBoxLB(self, li_books, libInicial).ponFuente(font)
        self.btNuevoBookP = Controles.PB(self, "", self.nuevoBook, plano=True).ponIcono(Iconos.Mas(), tamIcon=16)
        self.lbDepthBookP = Controles.LB2P(self, _("Max depth")).ponFuente(font)
        self.edDepthBookP = Controles.ED(self).ponFuente(font).tipoInt(0).anchoFijo(30)
        hbox = (
            Colocacion.H()
            .control(self.cbBooksP)
            .control(self.btNuevoBookP)
            .relleno()
            .control(self.lbDepthBookP)
            .control(self.edDepthBookP)
        )
        self.chbBookP = _label(
            lyG, "%s: %s" % (_("Activate book"), self.configuracion.nom_player()), hbox, siCheck=True
        )

        nueva_tab(lyG, _("Initial moves"))

        # ##################################################################################################################################
        # TAB avanzada
        # ##################################################################################################################################
        lyG = nuevoG()

        liAjustes = self.personalidades.listaAjustes(True)
        self.cbAjustarRival = (
            Controles.CB(self, liAjustes, ADJUST_BETTER).capturaCambiado(self.ajustesCambiado).ponFuente(font)
        )
        lbAjustarRival = Controles.LB2P(self, _("Set strength")).ponFuente(font)
        self.btAjustarRival = (
            Controles.PB(self, _("Personality"), self.cambiaPersonalidades, plano=True)
            .ponIcono(Iconos.Mas(), tamIcon=16)
            .ponFuente(font)
        )

        # ## Resign
        lbResign = Controles.LB2P(self, _("Resign/draw by engine")).ponFuente(font)
        liResign = (
            (_("Very early"), -100),
            (_("Early"), -300),
            (_("Average"), -500),
            (_("Late"), -800),
            (_("Very late"), -1000),
            (_("Never"), -9999999),
        )
        self.cbResign = Controles.CB(self, liResign, -800).ponFuente(font)

        self.lb_path_engine = Controles.LB(self, "").ponWrap()

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("OPTION", _("UCI option"), 240, centered=True)
        o_columns.nueva("VALUE", _("Value"), 200, centered=True, edicion=Delegados.MultiEditor(self))
        self.grid_uci = Grid.Grid(self, o_columns, siEditable=True)
        self.grid_uci.ponFuente(font)
        self.register_grid(self.grid_uci)

        lyH2 = (
            Colocacion.H().control(lbAjustarRival).control(self.cbAjustarRival).control(self.btAjustarRival).relleno()
        )
        lyH3 = Colocacion.H().control(lbResign).control(self.cbResign).relleno()
        ly = Colocacion.V().otro(lyH2).otro(lyH3).espacio(16).control(self.lb_path_engine).control(self.grid_uci)
        _label(lyG, _("Opponent"), ly)

        nueva_tab(lyG, _("Advanced"))

        layout = Colocacion.V().control(tb).control(tab).relleno().margen(3)

        self.setLayout(layout)

        self.liAperturasFavoritas = []
        self.btAperturasFavoritas.hide()

        dic = Util.restore_pickle(self.configuracion.ficheroEntMaquina)
        if not dic:
            dic = {}
        self.restore_dic(dic)

        self.ajustesCambiado()
        # self.ayudasCambiado()
        self.ponRival()

        self.restore_video()

    def grid_num_datos(self, grid):
        return len(self.rival.li_uci_options_editable()) if self.tab_advanced_active else 0

    def grid_dato(self, grid, fila, oColumna):
        col = oColumna.clave
        if col == "OPTION":
            return self.rival.li_uci_options_editable()[fila].name
        else:
            name = self.rival.li_uci_options_editable()[fila].name
            valor = self.rival.li_uci_options_editable()[fila].valor
            for xnombre, xvalor in self.rival.liUCI:
                if xnombre == name:
                    valor = xvalor
                    break
            tv = type(valor)
            if tv == bool:
                valor = str(valor).lower()
            else:
                valor = str(valor)
            return valor

    def me_set_editor(self, parent):
        recno = self.grid_uci.recno()
        opcion = self.rival.li_uci_options_editable()[recno]
        key = opcion.name
        value = opcion.valor
        for xkey, xvalue in self.rival.liUCI:
            if xkey == key:
                value = xvalue
                break
        if key is None:
            return None

        control = lista = minimo = maximo = None
        tipo = opcion.tipo
        if tipo == "spin":
            control = "sb"
            minimo = opcion.minimo
            maximo = opcion.maximo
        elif tipo in ("check", "button"):
            self.rival.ordenUCI(key, not value)
            self.grid_uci.refresh()
        elif tipo == "combo":
            lista = [(var, var) for var in opcion.li_vars]
            control = "cb"
        elif tipo == "string":
            control = "ed"

        self.me_control = control
        self.me_key = key

        if control == "ed":
            return Controles.ED(parent, value)
        elif control == "cb":
            return Controles.CB(parent, lista, value)
        elif control == "sb":
            return Controles.SB(parent, value, minimo, maximo)
        return None

    def me_ponValor(self, editor, valor):
        if self.me_control == "ed":
            editor.setText(str(valor))
        elif self.me_control in ("cb", "sb"):
            editor.ponValor(valor)

    def me_leeValor(self, editor):
        if self.me_control == "ed":
            return editor.texto()
        elif self.me_control in ("cb", "sb"):
            return editor.valor()

    def grid_setvalue(self, grid, nfila, columna, valor):
        opcion = self.rival.li_uci_options_editable()[nfila]
        self.rival.ordenUCI(opcion.name, valor)

    def configuraciones(self):
        dbc = UtilSQL.DictSQL(self.configuracion.ficheroEntMaquinaConf)
        liConf = dbc.keys(si_ordenados=True)
        menu = Controles.Menu(self)
        SELECCIONA, BORRA, AGREGA = range(3)
        for x in liConf:
            menu.opcion((SELECCIONA, x), x, Iconos.PuntoAzul())
        menu.separador()
        menu.opcion((AGREGA, None), _("Save current configuration"), Iconos.Mas())
        if liConf:
            menu.separador()
            submenu = menu.submenu(_("Remove"), Iconos.Delete())
            for x in liConf:
                submenu.opcion((BORRA, x), x, Iconos.PuntoRojo())
        resp = menu.lanza()

        if resp:
            op, k = resp

            if op == SELECCIONA:
                dic = dbc[k]
                self.restore_dic(dic)
            elif op == BORRA:
                if QTUtil2.pregunta(self, _X(_("Delete %1 ?"), k)):
                    del dbc[k]
            elif op == AGREGA:
                liGen = [(None, None)]

                liGen.append((_("Name") + ":", ""))

                resultado = FormLayout.fedit(liGen, title=_("Name"), parent=self, icon=Iconos.Libre())
                if resultado:
                    accion, liGen = resultado

                    name = liGen[0].strip()
                    if name:
                        dbc[name] = self.save_dic()

        dbc.close()

    def cambiaRival(self):
        resp = self.motores.menu(self)
        if resp:
            tp, cm = resp
            if tp == Motores.EXTERNO and cm is None:
                self.motoresExternos()
                return
            elif tp == Motores.MICPER:
                cm = WEngines.select_engine_entmaq(self)
                if not cm:
                    return
            self.rivalTipo = tp
            self.rival = cm
            self.ponRival()

    def ponRival(self):
        self.btRival.ponTexto("   %s   " % self.rival.name)
        self.btRival.ponIcono(self.motores.dicIconos[self.rivalTipo])
        self.si_edit_uci = False
        si_multi = False
        limpia_time_depth = True
        hide_time_depth = False

        if self.rivalTipo == Motores.IRINA:
            hide_time_depth = False

        elif self.rivalTipo == Motores.FIXED:
            hide_time_depth = True

        elif self.rivalTipo == Motores.ELO:
            self.edRtiempo.ponFloat(0.0)
            self.edRdepth.ponInt(self.rival.fixed_depth)
            limpia_time_depth = False
            hide_time_depth = True

        elif self.rivalTipo == Motores.MICGM:
            hide_time_depth = True

        elif self.rivalTipo == Motores.MICPER:
            hide_time_depth = True

        elif self.rivalTipo == Motores.INTERNO:
            si_multi = self.rival.has_multipv()
            limpia_time_depth = False

        elif self.rivalTipo == Motores.EXTERNO:
            si_multi = self.rival.has_multipv()

        if limpia_time_depth:
            self.edRtiempo.ponFloat(0.0)
            self.edRdepth.ponInt(0)

        self.gb_thinks.setVisible(not hide_time_depth)

        self.cbAjustarRival.ponValor(ADJUST_BETTER)
        self.btAjustarRival.setVisible(si_multi)
        self.cbAjustarRival.setEnabled(si_multi)

        self.lb_path_engine.ponTexto(Util.relative_path(self.rival.path_exe))
        self.tab_advanced_active = False

    def cambiada_tab(self, num):
        if num == self.tab_advanced:
            self.tab_advanced_active = True
            self.grid_uci.refresh()

    def cambiaPersonalidades(self):
        siRehacer = self.personalidades.lanzaMenu()
        if siRehacer:
            actual = self.cbAjustarRival.valor()
            self.cbAjustarRival.rehacer(self.personalidades.listaAjustes(True), actual)

    def ajustesCambiado(self):
        resp = self.cbAjustarRival.valor()
        if resp is None:
            self.cbAjustarRival.ponValor(ADJUST_HIGH_LEVEL)

    def cambiadoDepth(self):
        num = self.edRdepth.textoInt()
        if num > 0:
            self.edRtiempo.ponFloat(0.0)
        self.edRtiempo.setEnabled(num == 0)

    def cambiadoTiempo(self):
        num = self.edRtiempo.textoFloat()
        if num > 0.0:
            self.edRdepth.ponInt(0)
        self.edRdepth.setEnabled(num == 0.0)

    def cancelar_tiempo(self):
        self.edRtiempo.ponFloat(0.0)
        self.cambiadoTiempo()

    def cancelar_depth(self):
        self.edRdepth.ponInt(0)
        self.cambiadoDepth()

    def posicionEditar(self):
        cp = Position.Position()
        cp.read_fen(self.fen)
        resp = Voyager.voyager_position(self, cp, wownerowner=self.procesador.main_window)
        if resp is not None:
            self.fen = resp.fen()
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

    def muestraPosicion(self):
        if self.fen:
            rotulo = self.fen
            self.btPosicionQuitar.show()
            self.btPosicionPegar.show()
            self.bloqueApertura = None
            self.muestraApertura()
        else:
            rotulo = _("Change")
            self.btPosicionQuitar.hide()
            self.btPosicionPegar.show()
        rotulo = " " * 5 + rotulo + " " * 5
        self.btPosicion.ponTexto(rotulo)

    def editarApertura(self):
        self.btApertura.setDisabled(True)  # Puede tardar bastante vtime
        me = QTUtil2.unMomento(self)
        w = PantallaOpenings.WAperturas(self, self.configuracion, self.bloqueApertura)
        me.final()
        self.btApertura.setDisabled(False)
        if w.exec_():
            self.bloqueApertura = w.resultado()
            self.muestraApertura()

    def aperturasFavoritas(self):
        if len(self.liAperturasFavoritas) == 0:
            return
        menu = QTVarios.LCMenu(self)
        menu.setToolTip(_("To choose: <b>left button</b> <br>To erase: <b>right button</b>"))
        f = Controles.TipoLetra(puntos=8, peso=75)
        menu.ponFuente(f)
        nPos = 0
        for nli, bloque in enumerate(self.liAperturasFavoritas):
            if type(bloque) == tuple:  # compatibilidad con versiones anteriores
                bloque = bloque[0]
                self.liAperturasFavoritas[nli] = bloque
            menu.opcion(bloque, bloque.trNombre, Iconos.PuntoVerde())
            nPos += 1

        resp = menu.lanza()
        if resp:
            if menu.siIzq:
                self.bloqueApertura = resp
                self.muestraApertura()
            elif menu.siDer:
                bloqueApertura = resp
                if QTUtil2.pregunta(
                    self,
                    _X(
                        _("Do you want to delete the opening %1 from the list of favourite openings?"),
                        bloqueApertura.trNombre,
                    ),
                ):
                    del self.liAperturasFavoritas[nPos]

    def muestraApertura(self):
        if self.bloqueApertura:
            rotulo = self.bloqueApertura.trNombre + "\n" + self.bloqueApertura.pgn
            self.btAperturasQuitar.show()
            self.fen = ""
            self.muestraPosicion()
        else:
            rotulo = " " * 3 + _("Undetermined") + " " * 3
            self.btAperturasQuitar.hide()
        self.btApertura.ponTexto(rotulo)

    def save_dic(self):
        dic = {}

        # Básico
        dic["SIDE"] = "B" if self.rbBlancas.isChecked() else ("N" if self.rbNegras.isChecked() else "R")

        dr = dic["RIVAL"] = {}
        dr["ENGINE"] = self.rival.clave
        dr["TYPE"] = self.rivalTipo
        dr["LIUCI"] = self.rival.liUCI

        dr["ENGINE_TIME"] = int(self.edRtiempo.textoFloat() * 10)
        dr["ENGINE_DEPTH"] = self.edRdepth.textoInt()

        # Ayudas
        dic["HINTS"] = self.cbAyudas.valor() if self.gbTutor.isChecked() else 0
        dic["ARROWS"] = self.sbArrows.valor()
        dic["BOXHEIGHT"] = self.sbBoxHeight.valor()
        dic["THOUGHTOP"] = self.cbThoughtOp.valor()
        dic["THOUGHTTT"] = self.cbThoughtTt.valor()
        dic["ARROWSTT"] = self.sbArrowsTt.valor()
        dic["CONTINUETT"] = self.chbContinueTt.isChecked()
        dic["2CHANCE"] = self.chbChance.isChecked()
        dic["SUMMARY"] = self.chbSummary.isChecked()

        # Tiempo
        dic["WITHTIME"] = self.chbTiempo.isChecked()
        if dic["WITHTIME"]:
            dic["MINUTES"] = self.edMinutos.textoFloat()
            dic["SECONDS"] = self.edSegundos.value()
            dic["MINEXTRA"] = self.edMinExtra.value()
            dic["ZEITNOT"] = self.edZeitnot.value()

        # Mov. iniciales
        dic["OPENIGSFAVORITES"] = self.liAperturasFavoritas
        dic["OPENING"] = self.bloqueApertura
        dic["FEN"] = self.fen

        siBook = self.chbBookR.isChecked()
        dic["BOOKR"] = self.cbBooksR.valor() if siBook else None
        dic["BOOKRR"] = self.cbBooksRR.valor() if siBook else None
        dic["BOOKRDEPTH"] = self.edDepthBookR.textoInt() if siBook else None

        siBook = self.chbBookP.isChecked()
        dic["BOOKP"] = self.cbBooksP.valor() if siBook else None
        dic["BOOKPDEPTH"] = self.edDepthBookP.textoInt() if siBook else None

        # Avanzado
        dic["ADJUST"] = self.cbAjustarRival.valor()
        dic["RESIGN"] = self.cbResign.valor()

        return dic

    def restore_dic(self, dic):

        # Básico
        color = dic.get("SIDE", "B")
        self.rbBlancas.activa(color == "B")
        self.rbNegras.activa(color == "N")
        self.rbRandom.activa(color == "R")

        dr = dic.get("RIVAL", {})
        engine = dr.get("ENGINE", self.configuracion.x_rival_inicial)
        tipo = dr.get("TYPE", Motores.INTERNO)
        self.rivalTipo, self.rival = self.motores.busca(tipo, engine)
        if dr.get("LIUCI"):
            self.rival.liUCI = dr.get("LIUCI")
        self.ponRival()

        tm_s = float(dr.get("ENGINE_TIME", 0)) / 10.0
        self.edRtiempo.ponFloat(tm_s)
        self.edRdepth.ponInt(dr.get("ENGINE_DEPTH", 0))

        # Ayudas
        ayudas = dic.get("HINTS", 7)

        self.gbTutor.setChecked(ayudas > 0)
        self.cbAyudas.ponValor(ayudas)
        self.sbArrows.ponValor(dic.get("ARROWS", 7))
        self.sbBoxHeight.ponValor(dic.get("BOXHEIGHT", 64))
        self.cbThoughtOp.ponValor(dic.get("THOUGHTOP", -1))
        self.cbThoughtTt.ponValor(dic.get("THOUGHTTT", -1))
        self.sbArrowsTt.ponValor(dic.get("ARROWSTT", 0))
        self.chbContinueTt.setChecked(dic.get("CONTINUETT", True))
        self.chbChance.setChecked(dic.get("2CHANCE", True))
        self.chbSummary.setChecked(dic.get("SUMMARY", False))

        # Tiempo
        if dic.get("WITHTIME", False):
            self.chbTiempo.setChecked(True)
            self.edMinutos.ponFloat(float(dic["MINUTES"]))
            self.edSegundos.setValue(dic["SECONDS"])
            self.edMinExtra.setValue(dic.get("MINEXTRA", 0))
            self.edZeitnot.setValue(dic.get("ZEITNOT", 0))
        else:
            self.chbTiempo.setChecked(False)

        # Mov. iniciales
        if dic.get("BOOKR"):
            self.chbBookR.setChecked(True)
            self.cbBooksR.ponValor(dic["BOOKR"])
            self.cbBooksRR.ponValor(dic["BOOKRR"])
            self.edDepthBookR.ponInt(dic["BOOKRDEPTH"])

        if dic.get("BOOKP"):
            self.chbBookP.setChecked(True)
            self.cbBooksP.ponValor(dic["BOOKP"])
            self.edDepthBookP.ponInt(dic["BOOKPDEPTH"])

        self.liAperturasFavoritas = dic.get("OPENIGSFAVORITES", [])
        self.bloqueApertura = dic.get("OPENING", None)
        self.fen = dic.get("FEN", "")

        if self.bloqueApertura:
            nEsta = -1
            for npos, bl in enumerate(self.liAperturasFavoritas):
                if bl.a1h8 == self.bloqueApertura.a1h8:
                    nEsta = npos
                    break
            if nEsta != 0:
                if nEsta != -1:
                    del self.liAperturasFavoritas[nEsta]
                self.liAperturasFavoritas.insert(0, self.bloqueApertura)
            while len(self.liAperturasFavoritas) > 10:
                del self.liAperturasFavoritas[10]
        if len(self.liAperturasFavoritas):
            self.btAperturasFavoritas.show()

        bookR = dic.get("BOOKR", None)
        bookRR = dic.get("BOOKRR", None)
        self.chbBookR.setChecked(bookR is not None)
        if bookR:
            for bk in self.listaLibros.lista:
                if bk.path == bookR.path:
                    bookR = bk
                    break
            self.cbBooksR.ponValor(bookR)
            self.cbBooksRR.ponValor(bookRR)
            self.edDepthBookR.ponInt(dic.get("BOOKRDEPTH", 0))

        bookP = dic.get("BOOKP", None)
        self.chbBookP.setChecked(bookP is not None)
        if bookP:
            for bk in self.listaLibros.lista:
                if bk.path == bookP.path:
                    bookP = bk
                    break
            self.cbBooksP.ponValor(bookP)
            self.edDepthBookP.ponInt(dic.get("BOOKPDEPTH", 0))

        # Avanzado
        self.cbAjustarRival.ponValor(dic.get("AJUSTAR", ADJUST_BETTER))
        self.cbResign.ponValor(dr.get("RESIGN", -800))

        self.muestraApertura()
        self.muestraPosicion()

    def aceptar(self):
        self.dic = self.save_dic()
        Util.save_pickle(self.configuracion.ficheroEntMaquina, self.dic)

        # Info para el gestor, después de grabar, para que no haga falta salvar esto
        dr = self.dic["RIVAL"]
        dr["CM"] = self.rival

        self.save_video()

        self.accept()

    def cancelar(self):
        self.save_video()
        self.reject()

    def motoresExternos(self):
        w = WEngines.WEngines(self, self.configuracion)
        if w.exec_():
            self.ajustesCambiado()
            self.motores.rehazMotoresExternos()

    def nuevoBook(self):
        fbin = QTUtil2.leeFichero(self, self.listaLibros.path, "bin", titulo=_("Polyglot book"))
        if fbin:
            self.listaLibros.path = os.path.dirname(fbin)
            name = os.path.basename(fbin)[:-4]
            b = Books.Libro("P", name, fbin, False)
            self.listaLibros.nuevo(b)
            fvar = self.configuracion.ficheroBooks
            self.listaLibros.save_pickle(fvar)
            li = [(x.name, x) for x in self.listaLibros.lista]
            self.cbBooks.rehacer(li, b)

    def aperturasQuitar(self):
        self.bloqueApertura = None
        self.muestraApertura()

    def posicionQuitar(self):
        self.fen = ""
        self.muestraPosicion()

    def tutorChange(self):
        if PantallaTutor.cambioTutor(self, self.configuracion):
            self.procesador.cambiaXTutor()


def entrenamientoMaquina(procesador, titulo):
    w = WEntMaquina(procesador, titulo)
    if w.exec_():
        return w.dic
    else:
        return None


class WCambioRival(QtWidgets.QDialog):
    def __init__(self, wParent, configuracion, dic, siGestorSolo):
        super(WCambioRival, self).__init__(wParent)

        if not dic:
            dic = {}

        self.setWindowTitle(_("Change opponent"))
        self.setWindowIcon(Iconos.Motor())
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.Dialog | QtCore.Qt.WindowTitleHint)

        self.configuracion = configuracion
        self.personalidades = Personalidades.Personalidades(self, configuracion)

        # Toolbar
        li_acciones = [
            (_("Accept"), Iconos.Aceptar(), "aceptar"),
            None,
            (_("Cancel"), Iconos.Cancelar(), "cancelar"),
            None,
        ]
        tb = Controles.TB(self, li_acciones)

        # Blancas o negras
        self.rbBlancas = Controles.RB(self, _("White")).activa()
        self.rbNegras = Controles.RB(self, _("Black"))

        # Motores
        self.motores = Motores.Motores(configuracion)

        liDepths = [("--", 0)]
        for x in range(1, 31):
            liDepths.append((str(x), x))

        # # Rival
        self.rival = configuracion.x_rival_inicial
        self.rivalTipo = Motores.INTERNO
        self.btRival = Controles.PB(self, "", self.cambiaRival, plano=False)
        self.edRtiempo = Controles.ED(self).tipoFloat().anchoMaximo(50)
        self.cbRdepth = Controles.CB(self, liDepths, 0).capturaCambiado(self.cambiadoDepth)
        lbTiempoSegundosR = Controles.LB2P(self, _("Time"))
        lbNivel = Controles.LB2P(self, _("Depth"))

        # # Ajustar rival
        liAjustes = self.personalidades.listaAjustes(True)
        self.cbAjustarRival = Controles.CB(self, liAjustes, ADJUST_BETTER).capturaCambiado(self.ajustesCambiado)
        lbAjustarRival = Controles.LB2P(self, _("Set strength"))
        self.btAjustarRival = Controles.PB(self, "", self.cambiaPersonalidades, plano=False).ponIcono(
            Iconos.Nuevo(), tamIcon=16
        )
        self.btAjustarRival.ponToolTip(_("Personalities"))

        # Layout
        # Color
        hbox = Colocacion.H().relleno().control(self.rbBlancas).espacio(30).control(self.rbNegras).relleno()
        gbColor = Controles.GB(self, _("Play with"), hbox)

        # #Color
        hAC = Colocacion.H().control(gbColor)

        # Motores
        # Rival
        ly = Colocacion.G()
        ly.controlc(self.btRival, 0, 0, 1, 4)
        ly.controld(lbTiempoSegundosR, 1, 0).controld(self.edRtiempo, 1, 1)
        ly.controld(lbNivel, 1, 2).control(self.cbRdepth, 1, 3)
        lyH = Colocacion.H().control(lbAjustarRival).control(self.cbAjustarRival).control(self.btAjustarRival).relleno()
        ly.otroc(lyH, 2, 0, 1, 4)
        gbR = Controles.GB(self, _("Opponent"), ly)

        lyResto = Colocacion.V()
        lyResto.otro(hAC).espacio(3)
        lyResto.control(gbR).espacio(1)
        lyResto.margen(8)

        layout = Colocacion.V().control(tb).otro(lyResto).relleno().margen(3)

        self.setLayout(layout)

        self.dic = dic
        self.recuperaDic()

        self.ajustesCambiado()
        self.ponRival()

    def cambiaRival(self):
        resp = self.motores.menu(self)
        if resp:
            tp, cm = resp
            if tp == Motores.EXTERNO and cm is None:
                self.motoresExternos()
                return
            self.rivalTipo = tp
            self.rival = cm
            self.ponRival()

    def ponRival(self):
        self.btRival.ponTexto("   %s   " % self.rival.name)
        self.btRival.ponIcono(self.motores.dicIconos[self.rivalTipo])

    def ajustesCambiado(self):
        resp = self.cbAjustarRival.valor()
        if resp is None:
            self.cbAjustarRival.ponValor(ADJUST_HIGH_LEVEL)

    def cambiadoDepth(self, num):
        if num > 0:
            self.edRtiempo.ponFloat(0.0)
        self.edRtiempo.setEnabled(num == 0)

    def process_toolbar(self):
        accion = self.sender().clave
        if accion == "aceptar":
            self.aceptar()

        elif accion == "cancelar":
            self.reject()

        elif accion == "motores":
            self.motoresExternos()

    def aceptar(self):
        dic = self.dic
        dic["SIBLANCAS"] = self.rbBlancas.isChecked()

        dr = dic["RIVAL"] = {}
        dr["MOTOR"] = self.rival.clave
        dr["TIEMPO"] = int(self.edRtiempo.textoFloat() * 10)
        dr["PROFUNDIDAD"] = self.cbRdepth.valor()
        dr["CM"] = self.rival
        dr["TIPO"] = self.rivalTipo

        dic["AJUSTAR"] = self.cbAjustarRival.valor()

        self.accept()

    def motoresExternos(self):
        w = WEngines.WEngines(self, self.configuracion)
        if w.exec_():
            self.ajustesCambiado()
            self.motores.rehazMotoresExternos()

    def recuperaDic(self):
        dic = self.dic
        is_white = dic.get("SIBLANCAS", True)
        self.rbBlancas.activa(is_white)
        self.rbNegras.activa(not is_white)

        dr = dic.get("RIVAL", {})
        engine = dr.get("MOTOR", self.configuracion.tutor.clave)
        tipo = dr.get("TIPO", Motores.INTERNO)
        self.rivalTipo, self.rival = self.motores.busca(tipo, engine)
        self.ponRival()

        self.edRtiempo.ponFloat(float(dr.get("TIEMPO", self.configuracion.x_tutor_mstime / 100)) / 10.0)
        self.cbRdepth.ponValor(dr.get("PROFUNDIDAD", 0))
        self.cbAjustarRival.ponValor(dic.get("AJUSTAR", ADJUST_BETTER))

    def cambiaPersonalidades(self):
        siRehacer = self.personalidades.lanzaMenu()
        if siRehacer:
            actual = self.cbAjustarRival.valor()
            self.cbAjustarRival.rehacer(self.personalidades.listaAjustes(True), actual)


def cambioRival(parent, configuracion, dic, siGestorSolo=False):
    w = WCambioRival(parent, configuracion, dic, siGestorSolo)

    if w.exec_():
        return w.dic
    else:
        return None


def dameMinutosExtra(main_window):
    liGen = [(None, None)]

    config = FormLayout.Spinbox(_("Extra minutes for the player"), 1, 99, 50)
    liGen.append((config, 5))

    resultado = FormLayout.fedit(liGen, title=_("Time"), parent=main_window, icon=Iconos.MoverTiempo())
    if resultado:
        accion, liResp = resultado
        return liResp[0]

    return None
