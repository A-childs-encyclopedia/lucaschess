from Code import Gestor
from Code import Move
from Code.QT import Iconos
from Code.Constantes import *


class GestorVariantes(Gestor.Gestor):
    def inicio(self, game, is_white_bottom, siEngineActivo, siCompetitivo):

        self.pensando(True)

        self.kibitzers_manager = self.procesador.kibitzers_manager

        self.siAceptado = False

        self.siCompetitivo = siCompetitivo

        self.game = game

        self.game_type = GT_ALONE

        self.human_is_playing = True
        self.plays_instead_of_me_option = True
        self.dicRival = {}

        self.play_against_engine = False

        self.state = ST_PLAYING

        self.siRevision = False

        self.main_window.pon_toolbar((TB_ACCEPT, TB_CANCEL, TB_TAKEBACK, TB_REINIT, TB_CONFIG, TB_UTILITIES))

        self.is_human_side_white = is_white_bottom
        self.main_window.activaJuego(True, False, siAyudas=False)
        self.quitaAyudas(True, False)
        self.main_window.ponRotulo1(None)
        self.main_window.ponRotulo2(None)
        self.mostrarIndicador(True)
        self.ponPiezasAbajo(self.is_human_side_white)
        self.set_dispatcher(self.mueve_humano)
        self.pgnRefresh(True)
        self.ponCapInfoPorDefecto()

        self.refresh()

        if len(self.game):
            self.mueveJugada(GO_START)
            move = self.game.move(0)
            self.ponFlechaSC(move.from_sq, move.to_sq)
            self.disable_all()
        else:
            self.setposition(self.game.last_position)

        self.pensando(False)

        is_white = self.game.last_position.is_white
        self.is_human_side_white = is_white
        self.human_is_playing = True

        if siEngineActivo and not siCompetitivo:
            self.activeEngine()

        if not len(self.game):
            self.siguiente_jugada()

    def run_action(self, key):
        if key == TB_ACCEPT:
            self.siAceptado = True
            # self.resultado =
            self.procesador.pararMotores()
            self.main_window.accept()

        elif key == TB_CANCEL:
            self.procesador.pararMotores()
            self.main_window.reject()

        elif key == TB_TAKEBACK:
            self.atras()

        elif key == TB_REINIT:
            self.reiniciar()

        elif key == TB_CONFIG:
            self.configurar()

        elif key == TB_UTILITIES:
            liMasOpciones = (("libros", _("Consult a book"), Iconos.Libros()),)
            resp = self.utilidades(liMasOpciones)
            if resp == "libros":
                liMovs = self.librosConsulta(True)
                if liMovs:
                    for x in range(len(liMovs) - 1, -1, -1):
                        from_sq, to_sq, promotion = liMovs[x]
                        self.mueve_humano(from_sq, to_sq, promotion)

        else:
            Gestor.Gestor.rutinaAccionDef(self, key)

    def valor(self):
        if self.siAceptado:
            return self.game
        else:
            return None

    def final_x(self):
        self.procesador.pararMotores()
        return True

    def atras(self):
        if len(self.game):
            self.game.anulaSoloUltimoMovimiento()
            if not self.fen:
                self.game.assign_opening()
            self.goto_end()
            self.refresh()
            self.siguiente_jugada()

    def siguiente_jugada(self):
        if self.state == ST_ENDGAME:
            return

        self.state = ST_PLAYING

        self.put_view()

        is_white = self.game.last_position.is_white
        self.is_human_side_white = is_white
        self.human_is_playing = True

        if self.game.is_finished():
            return

        self.ponIndicador(is_white)

        self.activaColor(is_white)
        self.refresh()

    def mueve_humano(self, from_sq, to_sq, promotion=None):
        move = self.checkmueve_humano(from_sq, to_sq, promotion)
        if not move:
            return False
        self.move_the_pieces(move.liMovs)

        self.add_move(move)
        if self.play_against_engine:
            self.play_against_engine = False
            self.disable_all()
            self.juegaRival()
            self.play_against_engine = True  # Como juega por mi pasa por aqui, para que no se meta en un bucle infinito

        self.siguiente_jugada()
        return True

    def add_move(self, move):

        self.beepExtendido(True)

        self.changed = True

        self.game.add_move(move)

        self.ponFlechaSC(move.from_sq, move.to_sq)

        self.pgnRefresh(self.game.last_position.is_white)
        self.refresh()

    def reiniciar(self):
        self.inicio(self.fen, self.lineaPGN, self.okMasOpciones, self.is_human_side_white)

    def configurar(self):

        mt = _("Engine").lower()
        mt = _X(_("Disable %1"), mt) if self.play_against_engine else _X(_("Enable %1"), mt)

        if not self.siCompetitivo:
            liMasOpciones = (("engine", mt, Iconos.Motores()),)
        else:
            liMasOpciones = []

        resp = Gestor.Gestor.configurar(self, liMasOpciones, siCambioTutor=not self.siCompetitivo)

        if resp == "engine":
            self.ponRotulo1("")
            if self.play_against_engine:
                self.xrival.terminar()
                self.xrival = None
                self.play_against_engine = False
            else:
                self.cambioRival()

    def juegaRival(self):
        if not self.is_finished():
            self.pensando(True)
            rm = self.xrival.juega(nAjustado=self.xrival.nAjustarFuerza)
            if rm.from_sq:
                siBien, self.error, move = Move.dameJugada(
                    self.game, self.game.last_position, rm.from_sq, rm.to_sq, rm.promotion
                )
                self.add_move(move)
                self.move_the_pieces(move.liMovs)
            self.pensando(False)

    def activeEngine(self):
        dicBase = self.configuracion.leeVariables("ENG_VARIANTES")
        if dicBase:
            self.ponRival(dicBase)
        else:
            self.cambioRival()

    def cambioRival(self):

        if self.dicRival:
            dicBase = self.dicRival
        else:
            dicBase = self.configuracion.leeVariables("ENG_VARIANTES")

        import Code.Engines.PlayAgainstEngine as PantallaEntMaq

        dic = self.dicRival = PantallaEntMaq.cambioRival(
            self.main_window, self.configuracion, dicBase, siGestorSolo=True
        )

        if dic:
            self.ponRival(dic)

    def ponRival(self, dic):
        dr = dic["RIVAL"]
        rival = dr["CM"]
        r_t = dr["TIEMPO"] * 100  # Se guarda en decimas -> milesimas
        r_p = dr["PROFUNDIDAD"]
        if r_t <= 0:
            r_t = None
        if r_p <= 0:
            r_p = None
        if r_t is None and r_p is None and not dic["SITIEMPO"]:
            r_t = 1000

        nAjustarFuerza = dic["AJUSTAR"]
        self.xrival = self.procesador.creaGestorMotor(rival, r_t, r_p, nAjustarFuerza != ADJUST_BETTER)
        self.xrival.nAjustarFuerza = nAjustarFuerza

        dic["ROTULO1"] = _("Opponent") + ": <b>" + self.xrival.name
        self.ponRotulo1(dic["ROTULO1"])
        self.play_against_engine = True
        self.configuracion.escVariables("ENG_VARIANTES", dic)
