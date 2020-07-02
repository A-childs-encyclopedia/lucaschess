import os
import sys
import time

from Code import Game
from Code import Position
from Code import Gestor
from Code.QT import Controles
from Code.QT import Iconos
from Code.Openings import PantallaOpenings
from Code.Engines import PlayAgainstEngine
from Code.QT import PantallaSolo
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code import TrListas
from Code import Util
from Code.QT import Voyager
from Code.Constantes import *


def pgn_lcsb(estado, pgn, jugada_inicial=None):
    ok, game = Game.pgn_game(pgn)
    if jugada_inicial:
        move = game.move(jugada_inicial)
        si_blancas_abajo = move.position_before.is_white
    else:
        si_blancas_abajo = True

    return dict(ESTADO=estado, GAME=game.save(), WHITEBOTTOM=si_blancas_abajo)


def partida_lcsb(estado, game):
    return dict(ESTADO=estado, GAME=game.save())


class GestorSolo(Gestor.Gestor):
    def inicio(self, dic=None):
        self.game_type = GT_ALONE

        game_new = True
        if dic:
            if "GAME" in dic:
                self.game.restore(dic["GAME"])
                game_new = False
        else:
            dic = {}

        if game_new:
            self.new_game()
            self.game.add_tag("Event", _("Create your own game"))

        self.reinicio = dic
        self.exit_when_finished = dic.get("EXIT_WHEN_FINISHED", False)

        self.human_is_playing = True
        self.is_human_side_white = True

        self.tablero.setAcceptDropPGNs(self.dropPGN)

        self.plays_instead_of_me_option = True
        self.dicRival = {}

        self.play_against_engine = dic.get("PLAY_AGAINST_ENGINE", False) if not self.xrival else True

        self.ultimoFichero = dic.get("LAST_FILE", "")
        self.changed = False

        self.auto_rotate = dic.get("AUTO_ROTATE", False)

        self.state = dic.get("STATE", ST_PLAYING)

        self.bloqueApertura = dic.get("BLOQUEAPERTURA", None)

        if self.bloqueApertura:
            self.game.set_position()
            self.game.read_pv(self.bloqueApertura.a1h8)
            self.game.assign_opening()

        self.pon_toolbar()

        self.main_window.activaJuego(True, False, siAyudas=False)
        self.quitaAyudas(True, False)
        self.main_window.ponRotulo1(dic.get("ROTULO1", None))
        self.pon_rotulo()
        self.set_dispatcher(self.mueve_humano)
        # self.ponPosicion(self.game.last_position)
        self.mostrarIndicador(True)
        self.ponPiezasAbajo(dic.get("WHITEBOTTOM", True))
        self.pgnRefresh(True)
        self.ponCapInfoPorDefecto()

        self.dgt_setposition()

        self.goto_end()

        if "SICAMBIORIVAL" in dic:
            self.cambioRival()
            del dic["SICAMBIORIVAL"]  # que no lo vuelva a pedir

        self.valor_inicial = self.dame_valor_actual()

        self.siguiente_jugada()

    def pon_rotulo(self):
        li = []
        for label, rotulo in self.game.li_tags:
            if label.upper() == "WHITE":
                li.append("%s: %s" % (_("White"), rotulo))
            elif label.upper() == "BLACK":
                li.append("%s: %s" % (_("Black"), rotulo))
            elif label.upper() == "RESULT":
                li.append("%s: %s" % (_("Result"), rotulo))
        mensaje = "\n".join(li)
        self.ponRotulo2(mensaje)

    def dropPGN(self, pgn):
        game = self.procesador.select_1_pgn(self.main_window)
        if game:
            self.leerpgn(game)

    def run_action(self, key):
        if key == TB_CLOSE:
            self.finPartida()

        elif key == TB_TAKEBACK:
            self.atras()

        elif key == TB_FILE:
            self.file()

        elif key == TB_REINIT:
            self.reiniciar(self.reinicio)

        elif key == TB_CONFIG:
            self.configurarGS()

        elif key == TB_UTILITIES:
            liMasOpciones = (
                ("libros", _("Consult a book"), Iconos.Libros()),
                (None, None, None),
                ("play", _("Play current position"), Iconos.MoverJugar()),
            )

            resp = self.utilidades(liMasOpciones)
            if resp == "libros":
                liMovs = self.librosConsulta(True)
                if liMovs:
                    for x in range(len(liMovs) - 1, -1, -1):
                        from_sq, to_sq, promotion = liMovs[x]
                        self.mueve_humano(from_sq, to_sq, promotion)
            elif resp == "play":
                self.jugarPosicionActual()

        elif key == TB_PGN_LABELS:
            self.informacion()

        elif key in (TB_CANCEL, TB_END_GAME):
            self.main_window.reject()

        elif key == TB_SAVE_AS:
            self.grabarComo()

        elif key == TB_HELP_TO_MOVE:
            self.ayudaMover(999)

        else:
            Gestor.Gestor.rutinaAccionDef(self, key)

    def pon_toolbar(self):
        li = [TB_CLOSE, TB_FILE, TB_PGN_LABELS, TB_TAKEBACK, TB_HELP_TO_MOVE, TB_REINIT, TB_CONFIG, TB_UTILITIES]
        if self.exit_when_finished:
            li[0] = TB_END_GAME
        self.main_window.pon_toolbar(li)

    def finPartida(self):
        self.tablero.setAcceptDropPGNs(None)

        # Comprobamos que no haya habido cambios from_sq el ultimo grabado
        self.changed = self.changed or self.valor_inicial != self.dame_valor_actual()
        if self.changed and len(self.game):
            resp = QTUtil2.preguntaCancelar(
                self.main_window, _("Do you want to save changes to a file?"), _("Yes"), _("No")
            )
            if resp is None:
                return
            elif resp:
                self.grabarComo()

        if self.exit_when_finished:
            self.procesador.run_action(TB_QUIT)
            self.procesador.pararMotores()
            self.procesador.quitaKibitzers()
            self.procesador.main_window.accept()
            sys.exit(0)
        else:
            self.procesador.inicio()

    def final_x(self):
        self.finPartida()
        return False

    def siguiente_jugada(self):
        if self.state == ST_ENDGAME:
            return

        self.state = ST_PLAYING
        self.human_is_playing = True  # necesario

        self.put_view()

        is_white = self.game.last_position.is_white
        self.is_human_side_white = is_white  # Compatibilidad, sino no funciona el cambio en pgn

        if self.auto_rotate:
            time.sleep(1)
            if is_white != self.tablero.is_white_bottom:
                self.tablero.rotaTablero()

        if self.game.is_finished():
            self.muestra_resultado()
            return

        self.ponIndicador(is_white)
        self.refresh()

        self.activaColor(is_white)

    def mueve_humano(self, from_sq, to_sq, promotion=None):
        self.human_is_playing = True
        move = self.checkmueve_humano(from_sq, to_sq, promotion)
        if not move:
            return False

        self.move_the_pieces(move.liMovs)

        self.add_move(move, True)

        if self.play_against_engine and not self.game.siEstaTerminada():
            self.play_against_engine = False
            self.disable_all()
            self.juegaRival()
            self.play_against_engine = True  # Como juega por mi pasa por aqui, para que no se meta en un bucle infinito

        self.siguiente_jugada()
        return True

    def add_move(self, move, siNuestra):
        self.changed = True

        self.game.add_move(move)

        self.ponFlechaSC(move.from_sq, move.to_sq)
        self.beepExtendido(siNuestra)

        self.pgnRefresh(self.game.last_position.is_white)
        self.refresh()

        self.dgt_setposition()

    def muestra_resultado(self):
        self.state = ST_ENDGAME
        self.disable_all()

    def dame_valor_actual(self):
        dic = self.creaDic()
        dic["GAME"] = self.game.save()
        return Util.var2txt(dic)

    def creaDic(self):
        dic = {}
        dic["AUTO_ROTATE"] = self.auto_rotate
        dic["GAME"] = self.game.save()
        dic["STATE"] = self.state
        dic["BLOQUEAPERTURA"] = self.bloqueApertura
        dic["PLAY_AGAINST_ENGINE"] = self.play_against_engine
        if self.dicRival and self.play_against_engine:
            dic["ROTULO1"] = self.dicRival["ROTULO1"]
        return dic

    def reiniciar(self, dic=None):
        if dic is None:
            dic = self.creaDic()
        self.inicio(dic)

    def editarEtiquetasPGN(self):
        resp = PantallaSolo.editarEtiquetasPGN(self.procesador, self.game.li_tags)
        if resp:
            self.game.set_tags(resp)
            self.changed = True
            self.pon_rotulo()

    def guardaDir(self, resp):
        direc = os.path.dirname(resp)
        if direc != self.configuracion.save_lcsb():
            self.configuracion.save_lcsb(direc)
            self.configuracion.graba()

    def grabarFichero(self, fichero):
        dic = self.creaDic()
        dic["GAME"] = self.game.save()
        dic["LAST_FILE"] = Util.dirRelativo(fichero)
        dic["WHITEBOTTOM"] = self.tablero.is_white_bottom
        if Util.save_pickle(fichero, dic):
            self.valor_inicial = self.dame_valor_actual()
            self.guardaDir(fichero)
            self.changed = False
            name = os.path.basename(fichero)
            QTUtil2.mensajeTemporal(self.main_window, _X(_("Saved to %1"), name), 0.8)
            self.guardarHistorico(fichero)
            return True
        else:
            QTUtil2.message_error(self.main_window, "%s : %s" % (_("Unable to save"), fichero))
            return False

    def grabarComo(self):
        extension = "lcsb"
        siConfirmar = True
        if self.ultimoFichero:
            fichero = self.ultimoFichero
        else:
            fichero = self.configuracion.save_lcsb()
        while True:
            resp = QTUtil2.salvaFichero(
                self.main_window,
                _("File to save"),
                fichero,
                _("File") + " %s (*.%s)" % (extension, extension),
                siConfirmarSobreescritura=siConfirmar,
            )
            if resp:
                resp = str(resp)
                if not siConfirmar:
                    if os.path.abspath(resp) != os.path.abspath(self.ultimoFichero) and os.path.isfile(resp):
                        yn = QTUtil2.preguntaCancelar(
                            self.main_window,
                            _X(_("The file %1 already exists, what do you want to do?"), resp),
                            si=_("Overwrite"),
                            no=_("Choose another"),
                        )
                        if yn is None:
                            break
                        if not yn:
                            continue
                if self.grabarFichero(resp):
                    self.ultimoFichero = resp
                    self.pon_toolbar()
                return resp
            break
        return None

    def grabar(self):
        if self.ultimoFichero:
            self.grabarFichero(self.ultimoFichero)
        else:
            resp = self.grabarComo()
            if resp:
                self.ultimoFichero = resp
                self.pon_toolbar()
        self.guardarHistorico(self.ultimoFichero)

    def leeFichero(self, fich):
        dic = Util.restore_pickle(fich)
        self.guardaDir(fich)
        dic["LAST_FILE"] = fich
        self.xfichero = None
        self.xpgn = None
        self.xjugadaInicial = None
        self.reiniciar(dic)
        self.pon_toolbar()
        self.guardarHistorico(fich)

    def file(self):
        menu = QTVarios.LCMenu(self.main_window)
        if self.ultimoFichero:
            menuR = menu.submenu(_("Save"), Iconos.Grabar())
            rpath = self.ultimoFichero
            if os.curdir[:1] == rpath[:1]:
                rpath = Util.relative_path(rpath)
                if rpath.count("..") > 0:
                    rpath = self.ultimoFichero
            menuR.opcion("save", "%s: %s" % (_("Save"), rpath), Iconos.Grabar())
            menuR.separador()
            menuR.opcion("saveas", _("Save as"), Iconos.GrabarComo())
        else:
            menu.opcion("save", _("Save"), Iconos.Grabar())
        menu.separador()
        menu.opcion("new", _("New"), Iconos.TutorialesCrear())
        menu.separador()
        menu.opcion("open", _("Open"), Iconos.Recuperar())
        menu.separador()
        li = self.listaHistorico()
        if li:
            menu.separador()
            menuR = menu.submenu(_("Reopen"), Iconos.Historial())
            for path in li:
                menuR.opcion("reopen_%s" % path, path, Iconos.PuntoNaranja())
                menuR.separador()
        resp = menu.lanza()
        if resp is None:
            return
        if resp == "open":
            self.restore_lcsb()
        elif resp == "new":
            self.nuevo()
        elif resp.startswith("reopen_"):
            return self.leeFichero(resp[7:])
        elif resp == "save":
            self.grabar()
        elif resp == "saveas":
            self.grabarComo()

    def nuevo(self):
        self.xfichero = None
        self.xpgn = None
        self.xjugadaInicial = None
        self.reiniciar({})
        self.pon_toolbar()

    def restore_lcsb(self):
        resp = QTUtil2.leeFichero(self.main_window, self.configuracion.save_lcsb(), "lcsb")
        if resp:
            self.leeFichero(resp)

    def listaHistorico(self):
        dic = self.configuracion.leeVariables("FICH_GESTORSOLO")
        if dic:
            li = dic.get("HISTORICO")
            if li:
                return [f for f in li if os.path.isfile(f)]
        return []

    def guardarHistorico(self, path):
        path = Util.dirRelativo(path)

        dic = self.configuracion.leeVariables("FICH_GESTORSOLO")
        if not dic:
            dic = {}
        lista = dic.get("HISTORICO", [])
        if path in lista:
            lista.pop(lista.index(path))
        lista.insert(0, path)
        dic["HISTORICO"] = lista[:20]
        self.configuracion.escVariables("FICH_GESTORSOLO", dic)

    def informacion(self):
        menu = QTVarios.LCMenu(self.main_window)
        f = Controles.TipoLetra(puntos=10, peso=75)
        menu.ponFuente(f)

        siOpening = False
        for key, valor in self.game.li_tags:
            trad = TrListas.pgnLabel(key)
            if trad != key:
                key = trad
            menu.opcion(key, "%s : %s" % (key, valor), Iconos.PuntoAzul())
            if key.upper() == "OPENING":
                siOpening = True

        if not siOpening:
            opening = self.game.opening
            if opening:
                menu.separador()
                nom = opening.trNombre
                ape = _("Opening")
                rotulo = nom if ape.upper() in nom.upper() else ("%s : %s" % (ape, nom))
                menu.opcion("opening", rotulo, Iconos.PuntoNaranja())

        menu.separador()
        menu.opcion("pgn", _("Edit PGN labels"), Iconos.PGN())

        resp = menu.lanza()
        if resp:
            self.editarEtiquetasPGN()

    def configurarGS(self):
        mt = _("Engine").lower()
        mt = _X(_("Disable %1"), mt) if self.play_against_engine else _X(_("Enable %1"), mt)

        sep = (None, None, None)

        liMasOpciones = [
            ("rotacion", _("Auto-rotate board"), Iconos.JS_Rotacion()),
            sep,
            ("opening", _("Opening"), Iconos.Apertura()),
            sep,
            ("position", _("Edit start position"), Iconos.Datos()),
            sep,
            ("pasteposicion", _("Paste FEN position"), Iconos.Pegar16()),
            sep,
            ("leerpgn", _("Read PGN"), Iconos.PGN_Importar()),
            sep,
            ("pastepgn", _("Paste PGN"), Iconos.Pegar16()),
            sep,
            ("engine", mt, Iconos.Motores()),
            sep,
            ("voyager", _("Voyager 2"), Iconos.Voyager1()),
        ]
        resp = self.configurar(liMasOpciones, siCambioTutor=True, siSonidos=True)

        if resp == "rotacion":
            self.auto_rotate = not self.auto_rotate
            is_white = self.game.last_position.is_white
            if self.auto_rotate:
                if is_white != self.tablero.is_white_bottom:
                    self.tablero.rotaTablero()
        elif resp == "opening":
            me = self.unMomento()
            w = PantallaOpenings.WAperturas(self.main_window, self.configuracion, self.bloqueApertura)
            me.final()
            if w.exec_():
                self.bloqueApertura = w.resultado()
                self.xfichero = None
                self.xpgn = None
                self.xjugadaInicial = None
                self.reiniciar()

        elif resp == "position":
            self.startPosition()

        elif resp == "pasteposicion":
            texto = QTUtil.traePortapapeles()
            if texto:
                cp = Position.Position()
                try:
                    cp.read_fen(str(texto))
                    self.xfichero = None
                    self.xpgn = None
                    self.xjugadaInicial = None
                    self.new_game()
                    self.game.set_position(first_position=cp)
                    self.bloqueApertura = None
                    self.reiniciar()
                except:
                    pass

        elif resp == "leerpgn":
            self.leerpgn()

        elif resp == "pastepgn":
            texto = QTUtil.traePortapapeles()
            if texto:
                ok, game = Game.pgn_game(texto)
                if not ok:
                    QTUtil2.message_error(
                        self.main_window, _("The text from the clipboard does not contain a chess game in PGN format")
                    )
                    return
                self.xfichero = None
                self.xpgn = None
                self.xjugadaInicial = None
                self.bloqueApertura = None
                dic = self.creaDic()
                dic["GAME"] = game.save()
                dic["WHITEBOTTOM"] = game.last_position.is_white
                self.reiniciar(dic)

        elif resp == "engine":
            self.ponRotulo1("")
            if self.play_against_engine:
                if self.xrival:
                    self.xrival.terminar()
                    self.xrival = None
                self.play_against_engine = False
            else:
                self.cambioRival()

        elif resp == "voyager":
            ptxt = Voyager.voyagerPartida(self.main_window, self.game)
            if ptxt:
                self.xfichero = None
                self.xpgn = None
                self.xjugadaInicial = None
                dic = self.creaDic()
                dic["GAME"] = ptxt.save()
                dic["WHITEBOTTOM"] = self.tablero.is_white_bottom
                self.reiniciar(dic)

    def leerpgn(self, game=None):
        if game is None:
            game = self.procesador.select_1_pgn()
        if game:
            dic = self.creaDic()
            dic["GAME"] = game.save()
            dic["WHITEBOTTOM"] = self.tablero.is_white_bottom
            self.reiniciar(dic)

    def control_teclado(self, nkey):
        if nkey == ord("V"):
            self.paste(QTUtil.traePortapapeles())
        elif nkey == ord("T"):
            li = [self.game.first_position.fen(), "", self.game.pgnBaseRAW()]
            self.saveSelectedPosition("|".join(li))
        elif nkey == ord("S"):
            self.startPosition()

    def listHelpTeclado(self):
        return [
            ("V", _("Paste position")),
            ("T", _("Save position in 'Selected positions' file")),
            ("S", _("Set start position")),
        ]

    def startPosition(self):
        position = Voyager.voyager_position(self.main_window, self.game.first_position)
        if position is not None:
            if self.game.first_position == position:
                return
            self.game = Game.Game(ini_posicion=position, li_tags=self.game.li_tags)
            self.game.add_tag("FEN", None if self.game.siFenInicial() else position.fen())
            self.game.order_tags()
            self.xfichero = None
            self.xpgn = None
            self.xjugadaInicial = None
            self.bloqueApertura = None

            self.reiniciar()

    def paste(self, texto):
        try:
            if "." in texto or '"' in texto:
                ok, game = Game.pgn_game(texto)
                if not ok:
                    return
            elif "/" in texto:
                game = Game.Game(fen=texto)
            else:
                return
            self.bloqueApertura = None
            self.xfichero = None
            self.xpgn = None
            self.xjugadaInicial = None
            dic = self.creaDic()
            dic["GAME"] = game.save()
            dic["WHITEBOTTOM"] = game.last_position.is_white
            self.reiniciar(dic)
        except:
            pass

    def juegaRival(self):
        if not self.is_finished():
            self.pensando(True)
            rm = self.xrival.juega(nAjustado=self.xrival.nAjustarFuerza)
            self.pensando(False)
            if rm.from_sq:
                self.mueve_humano(rm.from_sq, rm.to_sq, rm.promotion)

    def cambioRival(self):
        if self.dicRival:
            dicBase = self.dicRival
        else:
            dicBase = self.configuracion.leeVariables("ENG_GESTORSOLO")

        dic = self.dicRival = PlayAgainstEngine.cambioRival(
            self.main_window, self.configuracion, dicBase, siGestorSolo=True
        )

        if dic:
            for k, v in dic.items():
                self.reinicio[k] = v

            dr = dic["RIVAL"]
            rival = dr["CM"]
            if hasattr(rival, "icono"):
                delattr(rival, "icono")  # problem with configuracion.escVariables and saving qt variables
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
            self.configuracion.escVariables("ENG_GESTORSOLO", dic)
            self.is_human_side_white = dic["SIBLANCAS"]
            if self.game.last_position.is_white != self.is_human_side_white and not self.game.siEstaTerminada():
                self.play_against_engine = False
                self.disable_all()
                self.juegaRival()
                self.play_against_engine = True

    def atras(self):
        if len(self.game):
            self.game.anulaSoloUltimoMovimiento()
            if self.play_against_engine:
                self.game.anulaSoloUltimoMovimiento()
            self.game.assign_opening()   # aunque no sea fen inicial
            self.goto_end()
            self.state = ST_PLAYING
            self.refresh()
            self.siguiente_jugada()
