from Code import Albums
from Code import Gestor
from Code import Move
from Code import Adjourns
from Code.QT import QTUtil2
from Code.Constantes import *


class GestorAlbum(Gestor.Gestor):
    def inicio(self, album, cromo):
        self.base_inicio(album, cromo)
        self.siguiente_jugada()

    def base_inicio(self, album, cromo):
        self.reinicio = {"ALBUM": album, "CROMO": cromo, "ISWHITE": cromo.is_white}

        is_white = cromo.is_white

        self.game_type = GT_ALBUM

        self.album = album
        self.cromo = cromo

        self.resultado = None
        self.human_is_playing = False
        self.state = ST_PLAYING

        self.is_human_side_white = is_white
        self.is_engine_side_white = not is_white

        self.is_tutor_enabled = False
        self.main_window.ponActivarTutor(False)
        self.ayudas_iniciales = self.ayudas = 0

        self.xrival = Albums.GestorMotorAlbum(self, self.cromo)
        self.main_window.pon_toolbar((TB_RESIGN, TB_ADJOURN, TB_CONFIG, TB_UTILITIES))

        self.main_window.activaJuego(True, False, siAyudas=False)
        self.set_dispatcher(self.mueve_humano)
        self.setposition(self.game.last_position)
        self.ponPiezasAbajo(is_white)
        self.quitaAyudas(True, siQuitarAtras=True)
        self.mostrarIndicador(True)

        self.main_window.base.lbRotulo1.ponImagen(self.cromo.pixmap_level())
        self.main_window.base.lbRotulo2.ponImagen(self.cromo.pixmap())
        self.pgnRefresh(True)
        self.ponCapInfoPorDefecto()

        self.dgt_setposition()

        player = self.configuracion.nom_player()
        other = self.cromo.name
        w, b = (player, other) if self.is_human_side_white else (_F(other), player)

        self.game.add_tag("White", w)
        self.game.add_tag("Black", b)

    def save_state(self):
        dic = {
            "ALBUMES_PRECLAVE": self.album.claveDB.split("_")[0],
            "ALBUM_ALIAS": self.album.alias,
            "POS_CROMO": self.cromo.pos,
            "GAME_SAVE": self.game.save(),
        }
        return dic

    def restore_state(self, dic):
        preclave = dic["ALBUMES_PRECLAVE"]
        alias = dic["ALBUM_ALIAS"]
        pos_cromo = dic["POS_CROMO"]
        game_save = dic["GAME_SAVE"]
        if preclave == "animales":
            albumes = Albums.AlbumesAnimales()
        else:
            albumes = Albums.AlbumesVehicles()

        album = albumes.get_album(alias)
        cromo = album.get_cromo(pos_cromo)
        self.base_inicio(album, cromo)
        self.game.restore(game_save)
        self.goto_end()

    def run_adjourn(self, dic):
        self.restore_state(dic)
        self.siguiente_jugada()

    def adjourn(self):
        if QTUtil2.pregunta(self.main_window, _("Do you want to adjourn the game?")):
            dic = self.save_state()

            label_menu = "%s %s/%s" % (_("Album"), _F(self.album.name), _F(self.cromo.name))
            self.state = ST_ENDGAME

            with Adjourns.Adjourns() as adj:
                adj.add(self.game_type, dic, label_menu)
                adj.si_seguimos(self)

    def run_action(self, key):
        if key in (TB_RESIGN, TB_CANCEL):
            self.resign()

        elif key == TB_CONFIG:
            self.configurar(siSonidos=True)

        elif key == TB_UTILITIES:
            self.utilidades()

        elif key == TB_ADJOURN:
            self.adjourn()

        elif key == TB_CLOSE:
            self.procesador.inicio()
            self.procesador.reabrirAlbum(self.album)

        elif key in self.procesador.li_opciones_inicio:
            self.procesador.run_action(key)

        else:
            Gestor.Gestor.rutinaAccionDef(self, key)

    def final_x(self):
        return self.resign()

    def resign(self):
        if self.state == ST_ENDGAME:
            return True
        if len(self.game) > 1:
            if not QTUtil2.pregunta(self.main_window, _("Do you want to resign?")):
                return False  # no abandona
            self.game.resign(self.is_human_side_white)
            self.guardarGanados(False)
            self.ponFinJuego()
            self.xrival.cerrar()
            self.main_window.pon_toolbar((TB_CLOSE, TB_CONFIG, TB_UTILITIES))
        else:
            self.procesador.inicio()

        return False

    def siguiente_jugada(self):
        if self.state == ST_ENDGAME:
            return

        self.state = ST_PLAYING

        self.human_is_playing = False
        self.put_view()

        if self.game.is_finished():
            self.muestra_resultado()
            return

        is_white = self.game.last_position.is_white

        is_rival = is_white == self.is_engine_side_white
        self.ponIndicador(is_white)

        self.refresh()

        if is_rival:
            self.pensando(True)
            self.disable_all()

            fen = self.fenUltimo()
            rm_rival = self.xrival.juega(fen)

            self.pensando(False)
            if self.mueve_rival(rm_rival):
                self.siguiente_jugada()

        else:
            self.human_is_playing = True
            self.activaColor(is_white)

    def mueve_humano(self, from_sq, to_sq, promotion=None):
        move = self.checkmueve_humano(from_sq, to_sq, promotion)
        if not move:
            return False

        self.move_the_pieces(move.liMovs)

        self.add_move(move, True)
        self.error = ""
        self.siguiente_jugada()
        return True

    def add_move(self, move, siNuestra):
        self.game.add_move(move)

        self.ponFlechaSC(move.from_sq, move.to_sq)
        self.beepExtendido(siNuestra)

        self.pgnRefresh(self.game.last_position.is_white)
        self.refresh()

        self.dgt_setposition()

    def mueve_rival(self, respMotor):
        from_sq = respMotor.from_sq
        to_sq = respMotor.to_sq

        promotion = respMotor.promotion

        siBien, mens, move = Move.dameJugada(self.game, self.game.last_position, from_sq, to_sq, promotion)
        if siBien:
            self.add_move(move, False)
            self.move_the_pieces(move.liMovs, True)

            self.error = ""

            return True
        else:
            self.error = mens
            return False

    def muestra_resultado(self):
        self.state = ST_ENDGAME
        self.disable_all()
        self.human_is_playing = False

        mensaje, beep, player_win = self.game.label_resultado_player(self.is_human_side_white)

        self.beepResultado(beep)
        self.guardarGanados(player_win)
        self.mensaje(mensaje)

        if player_win:
            mensaje = _X(_("Congratulations you have a new sticker %1."), self.cromo.name)
            self.cromo.hecho = True
            self.album.guarda()
            if self.album.test_finished():
                mensaje += "\n\n%s" % _("You have finished this album.")
                nuevo = self.album.siguiente
                if nuevo:
                    mensaje += "\n\n%s" % _X(_("Now you can play with album %1"), _F(nuevo))

            self.mensaje(mensaje)
        self.ponFinJuego()
        self.xrival.cerrar()
        self.main_window.pon_toolbar((TB_CLOSE, TB_CONFIG, TB_UTILITIES))
