import time

from PySide2 import QtCore, QtWidgets

import Code
from Code import Position
from Code.QT import Colocacion, Controles, Iconos, QTUtil, QTVarios, Tablero, QTUtil2
from Code.Coordinates import CoordinatesBasic


class WRunCoordinatesBasic(QTVarios.WDialogo):
    def __init__(self, owner, db_coordinates, is_white):

        QTVarios.WDialogo.__init__(self, owner, _("Coordinates"), Iconos.Blocks(), "runcoordinatesbasic")

        self.configuracion = Code.configuracion
        self.is_white = is_white
        self.db_coordinates = db_coordinates
        self.coordinates = None
        self.current_score = 0
        self.working = False
        self.time_ini = None

        conf_board = self.configuracion.config_board("RUNCOORDINATESBASIC", self.configuracion.size_base())

        self.board = Tablero.TableroEstaticoMensaje(self, conf_board, None, 0.6)
        self.board.crea()
        self.board.bloqueaRotacion(True)
        self.cp_initial = Position.Position()
        self.cp_initial.set_pos_initial()
        self.board.ponerPiezasAbajo(self.is_white)
        self.board.ponPosicion(self.cp_initial)

        font = Controles.TipoLetra(puntos=self.configuracion.x_sizefont_infolabels)

        lb_score_k = Controles.LB(self, _("Score") + ":").ponFuente(font)
        self.lb_score = Controles.LB(self).ponFuente(font)

        li_acciones = ((_("Close"), Iconos.MainMenu(), self.terminar), None, (_("Begin"), Iconos.Empezar(), self.begin), (_("Continue"), Iconos.Pelicula_Seguir(), self.seguir))
        self.tb = QTVarios.LCTB(self, li_acciones)
        self.show_tb(self.terminar, self.begin)

        separacion = 20
        ly_info = Colocacion.G()
        ly_info.controld(lb_score_k, 0, 0).controld(self.lb_score, 0, 1)

        ly_right = Colocacion.V().control(self.tb).relleno().otro(ly_info).relleno()

        w = QtWidgets.QWidget(self)
        w.setLayout(ly_right)
        w.setMinimumWidth(240)

        ly_center = Colocacion.H().control(self.board).control(w).margen(3)

        self.setLayout(ly_center)

        self.restore_video()
        self.adjustSize()

    def new_try(self):
        self.coordinates = CoordinatesBasic.CoordinatesBasic(self.is_white)
        self.coordinates.new_try()
        self.current_score = 0
        self.lb_score.ponTexto("0")
        self.working = True
        self.time_ini = time.time()
        QtCore.QTimer.singleShot(1000, self.comprueba_time)

    def end_work(self):
        self.working = False
        self.coordinates.new_done(self.current_score)
        self.db_coordinates.save(self.coordinates)
        QTUtil2.message(self, "%s\n\n%s: %d\n" % (_("Ended"), _("Result"), self.coordinates.score))
        self.board.pon_textos("", "", 1)
        self.show_tb(self.terminar, self.seguir)

    def comprueba_time(self):
        if self.working:
            dif_time = time.time() - self.time_ini
            if dif_time >= 30.0:
                self.end_work()
            else:
                tm = 1000 if dif_time > 1.0 else dif_time * 1000
                QtCore.QTimer.singleShot(tm, self.comprueba_time)

    def begin(self):
        self.seguir()

    def seguir(self):
        self.new_try()
        self.show_tb(self.terminar)
        self.go_next()

    def go_next(self):
        if self.working:
            self.square_object, self.square_next = self.coordinates.next()
            self.board.pon_textos(self.square_object, self.square_next, 0.8)
            QTUtil.refresh_gui()

    def pulsada_celda(self, celda):
        if celda == self.square_object and self.working:
            self.current_score += 1
            self.lb_score.ponTexto("%d" % self.current_score)
            self.go_next()

    def closeEvent(self, event):
        self.working = False
        self.save_video()
        event.accept()

    def terminar(self):
        self.working = False
        self.save_video()
        self.reject()

    def show_tb(self, *lista):
        for opc in self.tb.dicTB:
            self.tb.setAccionVisible(opc, opc in lista)
        QTUtil.refresh_gui()
