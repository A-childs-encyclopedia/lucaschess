import os
import random
import time

import FasterCode

import Code
from Code import Manager
from Code import Util
from Code.Base import Position
from Code.Base.Constantes import *
from Code.CompetitionWithTutor import WCompetitionWithTutor
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.QT import Iconos


class ControlFindAllMoves:
    def __init__(self, manager, siJugador):

        self.db = eval(open(Code.path_resource("IntFiles", "findallmoves.dkv")).read())
        mas = "P" if siJugador else "R"
        self.fichPuntos = "%s/score60%s.dkv" % (manager.configuration.carpeta_results, mas)
        if os.path.isfile(self.fichPuntos):
            self.liPuntos = Util.restore_pickle(self.fichPuntos)
        else:
            self.liPuntos = []
            for level in range(len(self.db)):
                self.liPuntos.append([0, 0])

        # import random
        # self.liPuntos = []
        # for level in range(len(self.db)):
        #     self.liPuntos.append([0, 0])
        # for level in range(59):
        #     self.liPuntos[level][0] = random.randint(150, 450)*(level+1)

    def guardar(self):
        Util.save_pickle(self.fichPuntos, self.liPuntos)

    def num_rows(self):
        return len(self.db)

    def primeroSinHacer(self):
        nd = self.num_rows()
        for i in range(nd):
            if self.liPuntos[i][0] == 0:
                return i
        return nd - 1

    def pos_with_error(self):
        nd = self.num_rows()
        for i in range(nd):
            if self.liPuntos[i][1] > 0:
                return i
        return 999

    def analysis(self, row, key):  # compatibilidad
        return ""

    def only_move(self, row, key):  # compatibilidad
        return None

    def mueve(self, row, key):  # compatibilidad
        return False

    def dato(self, row, key):
        if key == "LEVEL":
            return str(row + 1)
        vtime, errores = self.liPuntos[row]
        if key == "TIME":
            if vtime == 0:
                return "-"
            tiempo = vtime / 100.0
            tm = tiempo / (row + 1)
            return "%0.02f / %0.02f" % (tiempo, tm)
        else:
            return "-" if vtime == 0 else str(errores)

    def dame(self, number):
        li = self.db[number]
        pos = random.randint(0, len(li) - 1)
        return li[pos] + " 0 1"

    def mensResultado(self, number, vtime, errores):
        tm = vtime / (number + 1)

        if self.liPuntos[number][0] > 0:
            t0, e0 = self.liPuntos[number]
            siRecord = False
            if e0 > errores:
                siRecord = True
            elif e0 == errores:
                siRecord = vtime < t0
        else:
            siRecord = True

        mensaje = "<b>%s</b> : %d<br><b>%s</b> : %d<br><b>%s</b> : %.02f/%.02f" % (
            _("Level"),
            number + 1,
            _("Errors"),
            errores,
            _("Time"),
            vtime / 100.0,
            tm / 100.0,
        )
        if siRecord:
            mensaje += "<br><br><b>%s</b><br>" % _("New record!")
            self.liPuntos[number] = [vtime, errores]
            self.guardar()

        return mensaje, siRecord

    def remove_all(self):
        Util.remove_file(self.fichPuntos)
        self.liPuntos = [[0, 0]] * len(self.db)

    def average_time(self):
        num = 0
        tm = 0.0
        for row in range(self.num_rows()):
            vtime, errores = self.liPuntos[row]
            if vtime > 0:
                num += row + 1
                tm += vtime
        return tm / (num * 100) if num > 0 else 0.0


class ManagerFindAllMoves(Manager.Manager):
    def start(self, siJugador):

        self.siJugador = siJugador

        self.pgn = ControlFindAllMoves(self, siJugador)

        self.main_window.columnas60(True)

        self.finJuego()

        self.main_window.activaJuego(True, False, siAyudas=False)
        self.remove_hints(True, False)
        self.main_window.set_label1(None)
        self.main_window.set_label2(None)
        self.show_side_indicator(False)
        self.put_pieces_bottom(True)
        self.set_dispatcher(self.player_has_moved)
        self.pgnRefresh(True)
        self.main_window.base.pgn.gotop()
        self.main_window.board.siPosibleRotarBoard = False

        self.board.exePulsadoNum = None
        self.remove_info()
        self.ponRotulotm()
        self.refresh()

    def num_rows(self):
        return self.pgn.num_rows()

    def run_action(self, key):

        if key == TB_CLOSE:
            self.fin60()

        elif key == TB_PLAY:
            self.jugar()

        elif key == TB_RESIGN:
            self.finJuego()

        elif key == TB_CONFIG:
            self.config()

        else:
            Manager.Manager.rutinaAccionDef(self, key)

    def config(self):
        menu = QTVarios.LCMenu(self.main_window)
        menu.opcion("remove", _("Remove all results of all levels"), Iconos.Cancelar())

        resp = menu.lanza()
        if resp:
            if resp == "remove":
                if QTUtil2.pregunta(
                    self.main_window, _("Are you sure you want to delete all results of all levels and start again from scratch?")
                ):
                    self.pgn.remove_all()
                    self.pgnRefresh(True)
                    self.main_window.base.pgn.gotop()
                    self.ponRotulotm()

    def fin60(self):
        self.main_window.board.siPosibleRotarBoard = True
        self.board.remove_arrows()
        self.main_window.columnas60(False)
        self.procesador.start()

    def finJuego(self):
        self.main_window.pon_toolbar((TB_CLOSE, TB_PLAY, TB_CONFIG))
        self.disable_all()
        self.state = ST_ENDGAME
        self.ponRotulotm()

    def jugar(self, number=None):
        if self.state == ST_PLAYING:
            self.state = ST_ENDGAME
            self.disable_all()

        if number is None:

            pos = self.pgn.primeroSinHacer() + 1
            pos_with_error = self.pgn.pos_with_error() + 1
            if pos_with_error <= pos:
                pos = pos_with_error
            number = WCompetitionWithTutor.edit_training_position(
                self.main_window,
                _("Find all moves"),
                pos,
                etiqueta=_("Level"),
                pos=pos,
                mensAdicional="<b><red>"
                + _("Movements must be indicated in the following order: King, Queen, Rook, Bishop, Knight and Pawn.")
                + "</red></b>",
            )
            if number is None:
                return
            number -= 1

        fen = self.pgn.dame(number)
        self.number = number
        cp = Position.Position()
        cp.read_fen(fen)
        self.human_side = self.is_white = cp.is_white
        if self.is_white:
            siP = self.siJugador
        else:
            siP = not self.siJugador
        self.put_pieces_bottom(siP)
        self.set_position(cp)
        self.cp = cp
        self.refresh()

        FasterCode.set_fen(fen)
        self.liMovs = FasterCode.get_exmoves()

        # Creamos un avariable para controlar que se mueven en orden
        d = {}
        fchs = "KQRBNP"
        if not cp.is_white:
            fchs = fchs.lower()
        for k in fchs:
            d[k] = ""
        for mov in self.liMovs:
            mov.is_selected = False
            pz = mov.piece()
            d[pz] += pz
        self.ordenPZ = ""
        for k in fchs:
            self.ordenPZ += d[k]

        self.errores = 0
        self.iniTiempo = time.time()
        self.pendientes = len(self.liMovs)
        self.state = ST_PLAYING

        self.board.remove_arrows()

        mens = ""
        if cp.castles:
            if ("K" if cp.is_white else "k") in cp.castles:
                mens = "O-O"
            if ("Q" if cp.is_white else "q") in cp.castles:
                if mens:
                    mens += " + "
                mens += "O-O-O"
            if mens:
                mens = _("Castling moves possible") + ": " + mens
        if cp.en_passant != "-":
            mens += " " + _("En passant") + ": " + cp.en_passant

        self.main_window.set_label1(mens)

        self.nivel = number
        self.is_white = cp.is_white
        self.ponRotulo2n()

        self.main_window.pon_toolbar((TB_RESIGN,))
        self.main_window.base.pgn.goto(number, 0)
        self.activate_side(self.is_white)

    def ponRotulo2n(self):
        self.main_window.set_label2(
            "<h3>%s - %s %d - %s : %d</h3>"
            % (_("White") if self.is_white else _("Black"), _("Level"), self.nivel + 1, _("Errors"), self.errores)
        )

    def ponRotulotm(self):
        self.main_window.set_label1("")
        tm = self.pgn.average_time()
        if tm == 0.0:
            txt = ""
        else:
            txt = "<h3>%s/%s: %0.02f</h3>" % (_("Time"), _("Move"), tm)
        self.main_window.set_label2(txt)
        self.refresh()

    def final_x(self):
        self.procesador.start()
        return False

    def player_has_moved(self, from_sq, to_sq, promotion=""):
        if from_sq == to_sq:
            return
        a1h8 = from_sq + to_sq
        for mov in self.liMovs:
            if (mov.xfrom() + mov.xto()) == a1h8:
                if not mov.is_selected:
                    if mov.piece() == self.ordenPZ[0]:
                        self.board.creaFlechaMulti(a1h8, False, opacity=0.4)
                        mov.is_selected = True
                        self.ordenPZ = self.ordenPZ[1:]
                        if len(self.ordenPZ) == 0:
                            self.put_result()
                    else:
                        break
                self.atajosRatonReset()
                return
        self.errores += 1
        self.ponRotulo2n()
        self.atajosRatonReset()

    def put_result(self):
        vtime = int((time.time() - self.iniTiempo) * 100.0)
        self.finJuego()

        mensaje, siRecord = self.pgn.mensResultado(self.number, vtime, self.errores)
        self.ponRotulotm()

        if self.number == 59 and siRecord and self.errores == 0:
            mens = '<b><span style="color:green">%s</span></b>' % _("Congratulations, goal achieved")
            QTUtil2.message(self.main_window, mens)
        else:
            QTUtil2.mensajeTemporal(self.main_window, mensaje, 3 if siRecord else 2, background="#FFCD43" if siRecord else None)

    def analizaPosicion(self, row, key):
        if self.state == ST_PLAYING:
            self.finJuego()
            return
        if row <= self.pgn.primeroSinHacer():
            pos_with_error = self.pgn.pos_with_error()
            if pos_with_error < row:
                QTUtil2.message(self.main_window, _("To be able to play at this level, the previous levels must be solved without errors."))
                return
            self.jugar(row)

    def mueveJugada(self, tipo):
        row, col = self.main_window.pgnPosActual()
        if tipo == "+":
            if row > 0:
                row -= 1
        elif tipo == "-":
            if row < (self.pgn.num_rows() - 1):
                row += 1
        elif tipo == "p":
            row = 0
        elif tipo == "f":
            row = self.pgn.num_rows() - 1

        self.main_window.base.pgn.goto(row, 0)

    def pgnInformacion(self):
        pass  # Para anular el efecto del boton derecho
