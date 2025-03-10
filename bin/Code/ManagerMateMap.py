from Code import Manager
from Code.Base import Move, Position
from Code.QT import QTUtil
from Code.Base.Constantes import *


class ManagerMateMap(Manager.Manager):
    def start(self, workmap):
        self.workmap = workmap

        self.hints = 0

        self.player_win = False

        fenInicial = workmap.fenAim()

        self.is_rival_thinking = False

        etiqueta = ""
        if "|" in fenInicial:
            li = fenInicial.split("|")

            fenInicial = li[0]
            if fenInicial.endswith(" 0"):
                fenInicial = fenInicial[:-1] + "1"

            nli = len(li)
            if nli >= 2:
                etiqueta = li[1]

        cp = Position.Position()
        cp.read_fen(fenInicial)

        self.fen = fenInicial

        is_white = cp.is_white

        self.game.set_position(cp)

        self.game.pending_opening = False

        self.game_type = GT_WORLD_MAPS

        self.human_is_playing = False
        self.state = ST_PLAYING
        self.plays_instead_of_me_option = False

        self.human_side = is_white
        self.is_engine_side_white = not is_white

        self.rm_rival = None

        self.is_tutor_enabled = False
        self.main_window.set_activate_tutor(False)

        self.ayudas_iniciales = 0

        li_options = [TB_CLOSE, TB_REINIT, TB_CONFIG, TB_UTILITIES]
        self.main_window.pon_toolbar(li_options)

        self.main_window.activaJuego(True, False, siAyudas=False)
        self.main_window.remove_hints(True, True)
        self.set_dispatcher(self.player_has_moved)
        self.set_position(self.game.last_position)
        self.show_side_indicator(True)
        self.put_pieces_bottom(is_white)
        self.set_label1(etiqueta)
        self.set_label2(workmap.nameAim())
        self.pgnRefresh(True)
        QTUtil.refresh_gui()

        self.xrival = self.procesador.creaManagerMotor(self.configuration.tutor, self.configuration.x_tutor_mstime, None)

        self.is_analyzed_by_tutor = False

        self.check_boards_setposition()

        self.reiniciando = False
        self.is_rival_thinking = False
        self.play_next_move()

    def run_action(self, key):
        if key == TB_CLOSE:
            self.end_game()
            self.procesador.trainingMap(self.workmap.mapa)

        elif key == TB_REINIT:
            self.reiniciar()

        elif key == TB_CONFIG:
            self.configurar(siSonidos=True, siCambioTutor=True)

        elif key == TB_UTILITIES:
            self.utilidades()

        else:
            Manager.Manager.rutinaAccionDef(self, key)

    def reiniciar(self):
        if self.is_rival_thinking:
            return
        self.start(self.workmap)

    def end_game(self):
        self.procesador.start()

    def final_x(self):
        self.end_game()
        return False

    def play_next_move(self):
        if self.state == ST_ENDGAME:
            return
        self.siPiensaHumano = False

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()

        is_white = self.game.last_position.is_white

        if self.game.is_finished():
            self.muestra_resultado()
            return

        self.set_side_indicator(is_white)
        self.refresh()

        siRival = is_white == self.is_engine_side_white
        if siRival:
            self.piensa_rival()

        else:
            self.human_is_playing = True
            self.activate_side(is_white)

    def piensa_rival(self):
        self.is_rival_thinking = True
        self.thinking(True)
        self.disable_all()

        self.rm_rival = self.xrival.play_game(self.game)

        self.thinking(False)
        from_sq, to_sq, promotion = self.rm_rival.from_sq, self.rm_rival.to_sq, self.rm_rival.promotion

        if self.play_rival(from_sq, to_sq, promotion):
            self.is_rival_thinking = False
            self.play_next_move()
        else:
            self.is_rival_thinking = False

    def player_has_moved(self, from_sq, to_sq, promotion=""):
        move = self.check_human_move(from_sq, to_sq, promotion)
        if not move:
            return False

        self.move_the_pieces(move.liMovs)
        self.add_move(move, True)
        self.error = ""
        self.play_next_move()
        return True

    def add_move(self, move, siNuestra):
        self.game.add_move(move)

        self.put_arrow_sc(move.from_sq, move.to_sq)
        self.beepExtendido(siNuestra)

        self.pgnRefresh(self.game.last_position.is_white)
        self.refresh()

        self.check_boards_setposition()

    def play_rival(self, from_sq, to_sq, promotion):
        ok, mens, move = Move.get_game_move(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if ok:
            self.add_move(move, False)
            self.move_the_pieces(move.liMovs, True)

            self.error = ""

            return True
        else:
            self.error = mens
            return False

    def muestra_resultado(self):
        self.disable_all()
        self.human_is_playing = False
        self.state = ST_ENDGAME

        mensaje, beep, player_win = self.game.label_resultado_player(self.human_side)

        self.player_win = player_win

        self.beepResultado(beep)
        mensaje = _("Game ended")
        if player_win:
            mensaje = _("Congratulations you have won %s.") % self.workmap.nameAim()
            self.workmap.winAim(self.game.pv())

        self.mensajeEnPGN(mensaje)

        self.disable_all()
        self.refresh()

    def analizaPosicion(self, row, key):
        if self.player_win:
            Manager.Manager.analizaPosicion(self, row, key)
