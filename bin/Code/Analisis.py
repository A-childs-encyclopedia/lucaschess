import copy
import os

from typing import List, Tuple

from Code import AnalisisIndexes
from Code import BMT
from Code import Move
from Code import Game
from Code.Engines import EngineResponse
from Code.QT import PantallaAnalisis
from Code.Databases import WDB_Utils
from Code.QT import PantallaAnalisisParam
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code import Util
from Code.Constantes import NAG_3


class AnalizaPartida:
    def __init__(self, procesador, alm, is_massiv, li_moves=None):
        self.procesador = procesador
        self.alm = alm

        self.si_bmt_blunders = False
        self.si_bmt_brilliancies = False

        self.configuracion = procesador.configuracion
        conf_engine = copy.deepcopy(self.configuracion.buscaRival(alm.engine))
        if alm.multiPV:
            conf_engine.actMultiPV(alm.multiPV)
        self.xgestor = procesador.creaGestorMotor(conf_engine, alm.vtime, alm.depth, True, priority=alm.priority)
        self.vtime = alm.vtime
        self.depth = alm.depth
        self.with_variations = alm.include_variations

        self.stability = alm.stability
        self.st_centipawns = alm.st_centipawns
        self.st_depths = alm.st_depths
        self.st_timelimit = alm.st_timelimit

        # Asignacion de variables para blunders:
        # kblunders: puntos de perdida para considerar un blunder
        # tacticblunders: folder donde guardar tactic
        # pgnblunders: fichero pgn donde guardar la partidas
        # oriblunders: si se guarda la game original
        # bmtblunders: name del entrenamiento BMT a crear
        self.kblunders = alm.kblunders
        self.tacticblunders = (
            os.path.join(self.configuracion.dirPersonalTraining, "Tactics", alm.tacticblunders)
            if alm.tacticblunders
            else None
        )
        self.pgnblunders = alm.pgnblunders
        self.oriblunders = alm.oriblunders
        self.bmtblunders = alm.bmtblunders
        self.bmt_listaBlunders = None

        self.siTacticBlunders = False

        self.rut_dispatch_bp = None

        self.delete_previous = True

        # dpbrilliancies: depth de control para saber si es brilliancie
        # ptbrilliancies: puntos de ganancia
        # fnsbrilliancies: fichero fns donde guardar posiciones fen
        # pgnbrilliancies: fichero pgn donde guardar la partidas
        # oribrilliancies: si se guarda la game original
        # bmtbrilliancies: name del entrenamiento BMT a crear
        self.dpbrilliancies = alm.dpbrilliancies
        self.ptbrilliancies = alm.ptbrilliancies
        self.fnsbrilliancies = alm.fnsbrilliancies
        self.pgnbrilliancies = alm.pgnbrilliancies
        self.oribrilliancies = alm.oribrilliancies
        self.bmtbrilliancies = alm.bmtbrilliancies
        self.bmt_listaBrilliancies = None

        # Asignacion de variables comunes
        # white: si se analizan las white
        # black: si se analizan las black
        # liJugadores: si solo se miran los movimiento de determinados jugadores
        # book: si se usa un libro de aperturas para no analizar los iniciales
        # li_selected: si se indica un alista de movimientos concreta que analizar
        # from_last_move: se determina si se empieza de atras adelante o al reves
        # delete_previous: si la game tiene un analisis previo, se determina si se hace o no
        self.white = alm.white
        self.black = alm.black
        self.li_players = alm.li_players if is_massiv else None
        self.book = alm.book
        if self.book:
            self.book.polyglot()
        self.li_selected = li_moves
        self.from_last_move = alm.from_last_move
        self.delete_previous = alm.delete_previous

    def terminar_bmt(self, bmt_lista, name):
        """
        Si se estan creando registros para el entrenamiento BMT (Best move Training), al final hay que grabarlos
        @param bmt_lista: lista a grabar
        @param name: name del entrenamiento
        """
        if bmt_lista and len(bmt_lista) > 0:
            bmt = BMT.BMT(self.configuracion.ficheroBMT)
            dbf = bmt.read_dbf(False)

            reg = dbf.baseRegistro()
            reg.ESTADO = "0"
            reg.NOMBRE = name
            reg.EXTRA = ""
            reg.TOTAL = len(bmt_lista)
            reg.HECHOS = 0
            reg.PUNTOS = 0
            reg.MAXPUNTOS = bmt_lista.max_puntos()
            reg.FINICIAL = Util.dtos(Util.today())
            reg.FFINAL = ""
            reg.SEGUNDOS = 0
            reg.BMT_LISTA = Util.var2zip(bmt_lista)
            reg.HISTORIAL = Util.var2zip([])
            reg.REPE = 0
            reg.ORDEN = 0

            dbf.insertarReg(reg, siReleer=False)

            bmt.cerrar()

    def terminar(self, si_bmt):
        """
        Proceso final, para cerrar el engine que hemos usado
        @param si_bmt: si hay que grabar el registro de BMT
        """
        self.xgestor.terminar()
        if si_bmt:
            self.terminar_bmt(self.bmt_listaBlunders, self.bmtblunders)
            self.terminar_bmt(self.bmt_listaBrilliancies, self.bmtbrilliancies)

    def dispatch_bp(self, rut_dispatch_bp):
        """
        Se determina la rutina que se llama cada analisis
        """
        self.rut_dispatch_bp = rut_dispatch_bp

    def save_fns(self, fichero, fen):
        """
        Graba cada fen encontrado en el fichero "fichero"
        """
        if not fichero:
            return

        f = open(fichero, "ab")
        f.write("%s\r\n" % fen)
        f.close()
        self.procesador.entrenamientos.menu = None

    def graba_tactic(self, game, njg, mrm, pos_act):
        if not self.tacticblunders:
            return

        # Esta creado el folder
        before = "AvoidBlunders.fns"
        after = "ExploitBlunders.fns"
        if not os.path.isdir(self.tacticblunders):
            dtactics = os.path.join(self.configuracion.dirPersonalTraining, "Tactics")
            if not os.path.isdir(dtactics):
                os.mkdir(dtactics)
            os.mkdir(self.tacticblunders)
            with open(os.path.join(self.tacticblunders, "Config.ini"), "wt") as f:
                f.write(
                    """[COMMON]
    ed_reference=20
    REPEAT=0
    SHOWTEXT=1
    [TACTIC1]
    MENU=%s
    FILESW=%s:100
    [TACTIC2]
    MENU=%s
    FILESW=%s:100
    """
                    % (_("Avoid the blunder"), before, _("Take advantage of blunder"), after)
                )

        cab = ""
        for k, v in game.dicTags().items():
            ku = k.upper()
            if not (ku in ("RESULT", "FEN")):
                cab += '[%s "%s"]' % (k, v)
        move = game.move(njg)

        fen = move.position_before.fen()
        p = Game.Game(fen=fen)
        rm = mrm.li_rm[0]
        p.read_pv(rm.pv)
        f = open(os.path.join(self.tacticblunders, before), "at")
        f.write("%s||%s|%s%s\n" % (fen, p.pgnBaseRAW(), cab, game.pgnBaseRAWcopy(None, njg - 1)))
        f.close()

        fen = move.position.fen()
        p = Game.Game(fen=fen)
        rm = mrm.li_rm[pos_act]
        li = rm.pv.split(" ")
        p.read_pv(" ".join(li[1:]))
        f = open(os.path.join(self.tacticblunders, after), "at")
        f.write("%s||%s|%s%s\n" % (fen, p.pgnBaseRAW(), cab, game.pgnBaseRAWcopy(None, njg)))
        f.close()

        self.siTacticBlunders = True
        self.procesador.entrenamientos.menu = None

    def save_pgn(self, fichero, name, dic_cab, fen, move, rm, mj):
        """
        Graba una game en un pgn

        @param fichero: pgn donde grabar
        @param name: name del engine que hace el analisis
        @param dic_cab: etiquetas de cabecera del PGN
        @param fen: fen de la position
        @param move: move analizada
        @param rm: respuesta engine
        @param mj: respuesta engine con la mejor move, usado en caso de blunders, para incluirla
        """
        if not fichero:
            return False

        p = Game.Game()

        if mj:  # blunder
            p.set_position(move.position_before)
            p.read_pv(rm.pv)
            jg0 = p.move(0)
            jg0.comment = rm.texto()

        p.set_position(move.position_before)
        if mj:  # blunder
            rm = mj
        p.read_pv(rm.pv)
        if p.is_finished():
            result = p.resultado()
            mas = ""  # ya lo anade en la ultima move
        else:
            mas = " *"
            result = "*"

        jg0 = p.move(0)
        t = "%0.2f" % (float(self.vtime) / 1000.0,)
        t = t.rstrip("0")
        if t[-1] == ".":
            t = t[:-1]
        eti_t = "%s %s" % (t, _("Second(s)"))

        jg0.comment = "%s %s: %s\n" % (name, eti_t, rm.texto())
        if mj:
            jg0.add_variation(p)

        cab = ""
        for k, v in dic_cab.items():
            ku = k.upper()
            if not (ku in ("RESULT", "FEN")):
                cab += '[%s "%s"]\n' % (k, v)
        # Nos protegemos de que se hayan escrito en el pgn original de otra forma
        cab += '[FEN "%s"]\n' % fen
        cab += '[Result "%s"]\n' % result

        with open(fichero, "at", encoding="utf-8", errors="ignore") as q:
            texto = (cab + "\n" + p.pgnBase() + mas + "\n\n").replace("\n", "\r\n")
            q.write(texto)

        return True

    def save_bmt(self, si_blunder, fen, mrm, pos_act, cl_game, txt_game):
        """
        Se graba una position en un entrenamiento BMT
        @param si_blunder: si es blunder o brilliancie
        @param fen: position
        @param mrm: multirespuesta del engine
        @param pos_act: position de la position elegida en mrm
        @param cl_game: clave de la game
        @param txt_game: la game completa en texto
        """

        previa = 999999999
        nprevia = -1
        tniv = 0
        partida_bmt = Game.Game()
        cp = partida_bmt.first_position
        cp.read_fen(fen)

        if len(mrm.li_rm) > 16:
            mrm_bmt = copy.deepcopy(mrm)
            if pos_act > 15:
                mrm_bmt.li_rm[15] = mrm_bmt.li_rm[pos_act]
                pos_act = 15
            mrm_bmt.li_rm = mrm_bmt.li_rm[:16]
        else:
            mrm_bmt = mrm

        for n, rm in enumerate(mrm_bmt.li_rm):
            pts = rm.centipawns_abs()
            if pts != previa:
                previa = pts
                nprevia += 1
            tniv += nprevia
            rm.nivelBMT = nprevia
            rm.siElegida = False
            rm.siPrimero = n == pos_act
            partida_bmt.set_position(cp)
            partida_bmt.read_pv(rm.pv)
            rm.txtPartida = partida_bmt.save()

        bmt_uno = BMT.BMTUno(fen, mrm_bmt, tniv, cl_game)

        bmt_lista = self.bmt_listaBlunders if si_blunder else self.bmt_listaBrilliancies
        bmt_lista.nuevo(bmt_uno)
        bmt_lista.check_game(cl_game, txt_game)

    def xprocesa(self, game, tmp_bp):
        self.si_bmt_blunders = False
        self.si_bmt_brilliancies = False

        si_bp2 = hasattr(tmp_bp, "bp2")  # Para diferenciar el analisis de una game que usa una progressbar unica del
        # analisis de muchas, que usa doble

        def gui_dispatch(xrm):
            return not tmp_bp.is_canceled()

        self.xgestor.ponGuiDispatch(gui_dispatch)  # Dispatch del engine, si esta puesto a 4 minutos por ejemplo que
        # compruebe si se ha indicado que se cancele.

        si_blunders = self.kblunders > 0
        si_brilliancies = self.fnsbrilliancies or self.pgnbrilliancies or self.bmtbrilliancies

        if self.bmtblunders and self.bmt_listaBlunders is None:
            self.bmt_listaBlunders = BMT.BMTLista()

        if self.bmtbrilliancies and self.bmt_listaBrilliancies is None:
            self.bmt_listaBrilliancies = BMT.BMTLista()

        xlibro_aperturas = self.book

        is_white = self.white
        is_black = self.black

        if self.li_players:
            for x in ["BLACK", "WHITE"]:
                player = game.get_tag(x)
                if player:
                    si = False
                    for uno in self.li_players:
                        si_z = uno.endswith("*")
                        si_a = uno.startswith("*")
                        uno = uno.replace("*", "").strip().upper()
                        if si_a:
                            if player.endswith(uno):
                                si = True
                            if si_z:  # form para poner si_a y si_z
                                si = uno in player
                        elif si_z:
                            if player.startswith(uno):
                                si = True
                        elif uno == player:
                            si = True
                        if si:
                            break
                    if not si:
                        if x == "BLACK":
                            is_black = False
                        else:
                            is_white = False

        if not (is_white or is_black):
            return

        cl_game = Util.microsegundos_rnd()
        txt_game = game.save()
        si_poner_pgn_original_blunders = False
        si_poner_pgn_original_brilliancies = False

        n_jugadas = len(game)
        if self.li_selected:
            li_moves = self.li_selected
        else:
            li_moves = list(range(n_jugadas))

        if xlibro_aperturas:
            li_borrar = []
            for pos, njg in enumerate(li_moves):

                if tmp_bp.is_canceled():
                    self.xgestor.remove_gui_dispatch()
                    return

                # # Si esta en el libro
                move = game.move(njg)
                if xlibro_aperturas.miraListaJugadas(move.position_before.fen()):
                    li_borrar.append(pos)
                    continue
                else:
                    break
            if li_borrar:
                li_borrar.reverse()
                for x in li_borrar:
                    del li_moves[x]

        if self.from_last_move:
            li_moves.reverse()

        n_jugadas = len(li_moves)
        if si_bp2:
            tmp_bp.ponTotal(2, n_jugadas)
        else:
            tmp_bp.ponTotal(n_jugadas)

        for npos, njg in enumerate(li_moves):

            if tmp_bp.is_canceled():
                self.xgestor.remove_gui_dispatch()
                return

            move = game.move(njg)
            if si_bp2:
                tmp_bp.pon(2, npos + 1)
            else:
                tmp_bp.pon(npos)

            if self.rut_dispatch_bp:
                self.rut_dispatch_bp(npos, n_jugadas, njg)

            if tmp_bp.is_canceled():
                self.xgestor.remove_gui_dispatch()
                return

                # # Fin de game
                # if move.siJaqueMate or move.is_draw:
                # continue

            # # white y black
            is_white = move.position_before.is_white
            if is_white:
                if not is_white:
                    continue
            else:
                if not is_black:
                    continue

            # -# previos
            if self.delete_previous:
                move.analysis = None

            # -# Procesamos
            if move.analysis is None:
                resp = self.xgestor.analizaJugadaPartida(
                    game,
                    njg,
                    self.vtime,
                    depth=self.depth,
                    brDepth=self.dpbrilliancies,
                    brPuntos=self.ptbrilliancies,
                    stability=self.stability,
                    st_centipawns=self.st_centipawns,
                    st_depths=self.st_depths,
                    st_timelimit=self.st_timelimit,
                )
                if not resp:
                    self.xgestor.remove_gui_dispatch()
                    return

                move.analysis = resp
            cp = move.position_before
            mrm, pos_act = move.analysis
            move.complexity = AnalisisIndexes.calc_complexity(cp, mrm)
            move.winprobability = AnalisisIndexes.calc_winprobability(cp, mrm)
            move.narrowness = AnalisisIndexes.calc_narrowness(cp, mrm)
            move.efficientmobility = AnalisisIndexes.calc_efficientmobility(cp, mrm)
            move.piecesactivity = AnalisisIndexes.calc_piecesactivity(cp, mrm)
            move.exchangetendency = AnalisisIndexes.calc_exchangetendency(cp, mrm)

            if si_blunders or si_brilliancies or self.with_variations:
                rm = mrm.li_rm[pos_act]
                rm.ponBlunder(0)
                mj = mrm.li_rm[0]
                rm_pts = rm.centipawns_abs()

                dif = mj.centipawns_abs() - rm_pts
                fen = move.position_before.fen()

                if self.with_variations:
                    limite = self.alm.limit_include_variations
                    if (limite == 0) or (dif >= limite):
                        if not (self.alm.best_variation and dif == 0):
                            move.analisis2variantes(self.alm, self.delete_previous)

                if dif >= self.kblunders:
                    rm.ponBlunder(dif)

                    self.graba_tactic(game, njg, mrm, pos_act)

                    if self.save_pgn(self.pgnblunders, mrm.name, game.dicTags(), fen, move, rm, mj):
                        si_poner_pgn_original_blunders = True

                    if self.bmtblunders:
                        self.save_bmt(True, fen, mrm, pos_act, cl_game, txt_game)
                        self.si_bmt_blunders = True

                if rm.level_brilliant():
                    move.add_nag(NAG_3)
                    self.save_fns(self.fnsbrilliancies, fen)

                    if self.save_pgn(self.pgnbrilliancies, mrm.name, game.dicTags(), fen, move, rm, None):
                        si_poner_pgn_original_brilliancies = True

                    if self.bmtbrilliancies:
                        self.save_bmt(False, fen, mrm, pos_act, cl_game, txt_game)
                        self.si_bmt_brilliancies = True
                else:
                    nag, color = mrm.set_nag_color(self.configuracion, rm)
                    if nag:
                        move.add_nag(nag)

        # Ponemos el texto original en la ultima
        if si_poner_pgn_original_blunders and self.oriblunders:
            with open(self.pgnblunders, "at", encoding="utf-8", errors="ignore") as q:
                q.write("\n%s\n\n" % game.pgn())

        if si_poner_pgn_original_brilliancies and self.oribrilliancies:
            with open(self.pgnbrilliancies, "at", encoding="utf-8", errors="ignore") as q:
                q.write("\n%s\n\n" % game.pgn())

        self.xgestor.remove_gui_dispatch()


class TabAnalysis:
    wmu: None
    rm: EngineResponse.EngineResponse
    game: Game.Game
    mrm: EngineResponse.MultiEngineResponse
    list_rm_name: List[Tuple[EngineResponse.EngineResponse, str, int]]

    def __init__(self, tb_analysis, mrm, pos_selected, number, xengine):

        self.tb_analysis = tb_analysis
        self.number = number
        self.xengine = xengine
        self.siFigurines = tb_analysis.configuracion.x_pgn_withfigurines

        self.mrm = mrm
        self.pos_selected = pos_selected

        self.pos_rm_active = pos_selected
        self.pos_mov_active = 0

        self.move = tb_analysis.move

        self.is_active = False

        self.list_rm_name = self.do_lirm()  # rm, name, centpawns

    def time_engine(self):
        return self.mrm.name

    def time_label(self):
        if self.mrm.max_time:
            t = "%0.2f" % (float(self.mrm.max_time) / 1000.0,)
            t = t.rstrip("0")
            if t[-1] == ".":
                t = t[:-1]
            eti_t = "%s: %s" % (_("Second(s)"), t)
        elif self.mrm.max_depth:
            eti_t = "%s: %d" % (_("Depth"), self.mrm.max_depth)
        else:
            eti_t = ""
        return eti_t

    def do_lirm(self) -> List[Tuple[EngineResponse.EngineResponse, str, int]]:
        li = []
        pb = self.move.position_before
        for rm in self.mrm.li_rm:
            pv1 = rm.pv.split(" ")[0]
            from_sq = pv1[:2]
            to_sq = pv1[2:4]
            promotion = pv1[4].lower() if len(pv1) == 5 else None

            txt = rm.abrTextoBase()
            if txt:
                txt = "(%s)" % txt
            if self.siFigurines:
                name = pb.pgn(from_sq, to_sq, promotion) + txt

            else:
                name = pb.pgn_translated(from_sq, to_sq, promotion) + txt
            li.append((rm, name, rm.centipawns_abs()))

        return li

    def set_wmu(self, wmu):
        self.wmu = wmu
        self.is_active = True

    def desactiva(self):
        self.wmu.hide()
        self.is_active = False

    def is_selected(self, pos_rm):
        return pos_rm == self.pos_selected

    def set_pos_rm_active(self, pos_rm):
        self.pos_rm_active = pos_rm
        self.rm = self.list_rm_name[self.pos_rm_active][0]
        self.game = Game.Game(self.move.position_before)
        self.game.read_pv(self.rm.pv)
        self.game.is_finished()
        self.pos_mov_active = 0

    def pgn_active(self):
        return self.game.pgn_html(self.tb_analysis.pos_move / 2 + 1, siFigurines=self.siFigurines)

    def score_active(self):
        rm = self.list_rm_name[self.pos_rm_active][0]
        return rm.texto()

    def complexity(self):
        return AnalisisIndexes.get_complexity(self.move.position_before, self.mrm)

    def winprobability(self):
        return AnalisisIndexes.get_winprobability(self.move.position_before, self.mrm)

    def narrowness(self):
        return AnalisisIndexes.get_narrowness(self.move.position_before, self.mrm)

    def efficientmobility(self):
        return AnalisisIndexes.get_efficientmobility(self.move.position_before, self.mrm)

    def piecesactivity(self):
        return AnalisisIndexes.get_piecesactivity(self.move.position_before, self.mrm)

    def active_position(self):
        n_movs = len(self.game)
        if self.pos_mov_active >= n_movs:
            self.pos_mov_active = n_movs - 1
        if self.pos_mov_active < 0:
            self.pos_mov_active = -1
            return self.game.move(0).position_before, None, None
        else:
            move_active = self.game.move(self.pos_mov_active)
            return move_active.position, move_active.from_sq, move_active.to_sq

    def active_base_position(self):
        n_movs = len(self.game)
        if self.pos_mov_active >= n_movs:
            self.pos_mov_active = n_movs - 1
        if self.pos_mov_active < 0:
            self.pos_mov_active = -1
            return self.game.move(0).position_before, None, None
        else:
            move_active = self.game.move(self.pos_mov_active)
            return move_active.position_before, move_active.from_sq, move_active.to_sq

    def change_mov_active(self, accion):
        if accion == "Adelante":
            self.pos_mov_active += 1
        elif accion == "Atras":
            self.pos_mov_active -= 1
        elif accion == "Inicio":
            self.pos_mov_active = -1
        elif accion == "Final":
            self.pos_mov_active = len(self.game) - 1

    def is_final_position(self):
        return self.pos_mov_active >= len(self.game) - 1

    def fen_active(self):
        move = self.game.move(self.pos_mov_active if self.pos_mov_active > 0 else 0)
        return move.position.fen()

    def external_analysis(self, wowner, is_white):
        move = self.game.move(self.pos_mov_active if self.pos_mov_active >= 0 else 0)
        pts = self.score_active()
        AnalisisVariantes(wowner, self.xengine, move, is_white, pts, max_recursion=self.tb_analysis.max_recursion)

    def save_base(self, game, rm):
        name = self.time_engine()
        vtime = self.time_label()
        comment = " {%s %s %s} " % (rm.abrTexto(), name, vtime)

        variation = game.copiaDesde(self.move.position_before.num_moves)
        if len(variation) > 0:
            variation.move(0).comment = comment
        self.move.add_variation(variation)

    def put_view_gestor(self):
        self.tb_analysis.procesador.gestor.put_view()


class MuestraAnalisis:
    def __init__(self, procesador, move, max_recursion, pos_move):

        self.procesador = procesador
        self.configuracion = procesador.configuracion
        self.move = move
        self.pos_move = pos_move  # Para mostrar el pgn con los numeros correctos
        self.max_recursion = max_recursion
        self.li_tabs_analysis = []

    def create_initial_show(self, main_window, xengine):
        move = self.move
        if move.analysis is None:
            me = QTUtil2.mensEspera.inicio(
                main_window, _("Analyzing the move...."), position="ad"
                , siCancelar=True)

            def mira(rm):
                return not me.cancelado()

            xengine.ponGuiDispatch(mira)
            mrm, pos = xengine.analyse_move(move, xengine.motorTiempoJugada, xengine.motorProfundidad)
            move.analysis = mrm, pos
            si_cancelado = me.cancelado()
            me.final()
            if si_cancelado:
                return None
        mrm, pos = move.analysis

        um = TabAnalysis(self, mrm, pos, 0, xengine)
        self.li_tabs_analysis.append(um)
        return um

    def create_show(self, main_window, alm):
        xengine = None
        busca = alm.engine[1:] if alm.engine.startswith("*") else alm.engine
        for um in self.li_tabs_analysis:
            if um.xengine.clave == busca:
                xengine = um.xengine
                xengine.actMultiPV(alm.multiPV)
                break
        if xengine is None:
            conf_engine = self.configuracion.buscaRival(alm.engine)
            conf_engine.actMultiPV(alm.multiPV)
            xengine = self.procesador.creaGestorMotor(conf_engine, alm.vtime, alm.depth, siMultiPV=True)

        me = QTUtil2.mensEspera.inicio(main_window, _("Analyzing the move...."), position="ad")
        mrm, pos = xengine.analyse_move(self.move, alm.vtime, alm.depth)
        me.final()

        um = TabAnalysis(self, mrm, pos, self.li_tabs_analysis[-1].number + 1, xengine)
        self.li_tabs_analysis.append(um)
        return um


def show_analysis(procesador, xtutor, move, is_white, max_recursion, pos_move, main_window=None, must_save=True):
    main_window = procesador.main_window if main_window is None else main_window

    ma = MuestraAnalisis(procesador, move, max_recursion, pos_move)
    if xtutor is None:
        xtutor = procesador.XTutor()
    um0 = ma.create_initial_show(main_window, xtutor)
    if not um0:
        return
    si_libre = max_recursion > 0
    wa = PantallaAnalisis.WAnalisis(ma, main_window, is_white, si_libre, must_save, um0)
    wa.exec_()

    busca = True
    for uno in ma.li_tabs_analysis:
        if busca:
            if uno.is_active:
                move.analysis = uno.mrm, uno.pos_selected

                busca = False
        xengine = uno.xengine
        if not xtutor or xengine.clave != xtutor.clave:
            xengine.terminar()


class AnalisisVariantes:
    def __init__(self, owner, xtutor, move, is_white, cbase_points, max_recursion=100000):

        self.owner = owner
        self.xtutor = xtutor
        self.move = move
        self.is_white = is_white
        self.position_before = move.position_before
        self.is_moving_time = False

        self.time_function = None
        self.time_pos_max = None
        self.time_pos = None
        self.time_others_tb = None
        self.rm = None
        self.pos_tutor = None
        self.max_tutor = None
        self.game_tutor = None

        if self.xtutor.motorTiempoJugada:
            segundos_pensando = self.xtutor.motorTiempoJugada / 1000  # esta en milesimas
            if self.xtutor.motorTiempoJugada % 1000 > 0:
                segundos_pensando += 1
        else:
            segundos_pensando = 3

        self.w = PantallaAnalisis.WAnalisisVariantes(
            self, self.owner, segundos_pensando, self.is_white, cbase_points, max_recursion
        )
        self.reset()
        self.w.exec_()

    def reset(self):
        self.w.tablero.ponPosicion(self.position_before)
        self.w.tablero.ponFlechaSC(self.move.from_sq, self.move.to_sq)
        self.w.tablero.set_dispatcher(self.mueve_humano)
        self.w.tablero.activaColor(not self.move.position.is_white)

    def mueve_humano(self, from_sq, to_sq, promotion=None):

        # Peon coronando
        if not promotion and self.position_before.siPeonCoronando(from_sq, to_sq):
            promotion = self.w.tablero.peonCoronando(not self.move.position.is_white)
            if promotion is None:
                return False

        si_bien, mens, new_move = Move.dameJugada(None, self.position_before, from_sq, to_sq, promotion)

        if si_bien:

            self.move_the_pieces(new_move.liMovs)
            self.w.tablero.ponFlechaSC(new_move.from_sq, new_move.to_sq)
            self.analyse_move(new_move)
            return True
        else:
            return False

    def analyse_move(self, new_move):
        me = QTUtil2.mensEspera.inicio(self.w, _("Analyzing the move...."))

        secs = self.w.dameSegundos()
        self.rm = self.xtutor.analizaVariante(new_move, secs * 1000, self.is_white)
        me.final()

        self.game_tutor = Game.Game(new_move.position)
        self.game_tutor.read_pv(self.rm.pv)

        if len(self.game_tutor):
            self.w.tableroT.ponPosicion(self.game_tutor.move(0).position)

        self.w.ponPuntuacion(self.rm.texto())

        self.pos_tutor = 0
        self.max_tutor = len(self.game_tutor)

        self.moving_tutor(si_inicio=True)

    def move_the_pieces(self, li_movs):
        """
        Hace los movimientos de piezas en el tablero
        """
        for movim in li_movs:
            if movim[0] == "b":
                self.w.tablero.borraPieza(movim[1])
            elif movim[0] == "m":
                self.w.tablero.muevePieza(movim[1], movim[2])
            elif movim[0] == "c":
                self.w.tablero.cambiaPieza(movim[1], movim[2])

        self.w.tablero.disable_all()

        self.w.tablero.escena.update()
        self.w.update()
        QTUtil.refresh_gui()

    def process_toolbar(self, accion, max_recursion):
        if self.rm:
            if accion == "MoverAdelante":
                self.moving_tutor(n_saltar=1)
            elif accion == "MoverAtras":
                self.moving_tutor(n_saltar=-1)
            elif accion == "MoverInicio":
                self.moving_tutor(si_inicio=True)
            elif accion == "MoverFinal":
                self.moving_tutor(si_final=True)
            elif accion == "MoverTiempo":
                self.move_timed()
            elif accion == "MoverLibre":
                self.external_analysis(max_recursion)
            elif accion == "MoverFEN":
                move = self.game_tutor.move(self.pos_tutor)
                QTUtil.ponPortapapeles(move.position.fen())
                QTUtil2.message_bold(self.w, _("FEN is in clipboard"))

    def moving_tutor(self, si_inicio=False, n_saltar=0, si_final=False, is_base=False):
        if n_saltar:
            pos = self.pos_tutor + n_saltar
            if 0 <= pos < self.max_tutor:
                self.pos_tutor = pos
            else:
                return
        elif si_inicio or is_base:
            self.pos_tutor = 0
        elif si_final:
            self.pos_tutor = self.max_tutor - 1
        if self.game_tutor.num_moves():
            move = self.game_tutor.move(self.pos_tutor)
            if is_base:
                self.w.tableroT.ponPosicion(move.position_before)
            else:
                self.w.tableroT.ponPosicion(move.position)
                self.w.tableroT.ponFlechaSC(move.from_sq, move.to_sq)
        self.w.tableroT.escena.update()
        self.w.update()
        QTUtil.refresh_gui()

    def move_timed(self):
        if self.is_moving_time:
            self.is_moving_time = False
            self.time_others_tb(True)
            self.w.stop_clock()
            return

        def otros_tb(si_habilitar):
            for accion in self.w.tb.li_acciones:
                if not accion.clave.endswith("MoverTiempo"):
                    accion.setEnabled(si_habilitar)

        self.time_function = self.moving_tutor
        self.time_pos_max = self.max_tutor
        self.time_pos = -1
        self.time_others_tb = otros_tb
        self.is_moving_time = True
        otros_tb(False)
        self.moving_tutor(is_base=True)
        self.w.start_clock(self.moving_time_1)

    def moving_time_1(self):
        self.time_pos += 1
        if self.time_pos == self.time_pos_max:
            self.is_moving_time = False
            self.time_others_tb(True)
            self.w.stop_clock()
            return
        if self.time_pos == 0:
            self.time_function(siInicio=True)
        else:
            self.time_function(nSaltar=1)

    def external_analysis(self, max_recursion):
        move = self.game_tutor.move(self.pos_tutor)
        pts = self.rm.texto()
        AnalisisVariantes(self.w, self.xtutor, move, self.is_white, pts, max_recursion)


def analyse_game(gestor):
    game = gestor.game
    procesador = gestor.procesador
    main_window = gestor.main_window

    alm = PantallaAnalisisParam.paramAnalisis(main_window, procesador.configuracion, True)

    if alm is None:
        return

    li_moves = []
    lni = Util.ListaNumerosImpresion(alm.num_moves)
    num_move = int(game.primeraJugada())
    is_white = not game.siEmpiezaConNegras
    for nRaw in range(game.num_moves()):
        must_save = lni.siEsta(num_move)
        if must_save:
            if is_white:
                if not alm.white:
                    must_save = False
            elif not alm.black:
                must_save = False
        if must_save:
            li_moves.append(nRaw)
        is_white = not is_white
        if is_white:
            num_move += 1

    mensaje = _("Analyzing the move....")
    num_moves = len(li_moves)
    tmp_bp = QTUtil2.BarraProgreso(main_window, _("Analysis"), mensaje, num_moves).show_top_right()

    ap = AnalizaPartida(procesador, alm, False, li_moves)

    def dispatch_bp(pos, ntotal, njg):
        tmp_bp.mensaje(mensaje + " %d/%d" % (pos + 1, ntotal))
        move = game.move(njg)
        gestor.ponPosicion(move.position)
        gestor.main_window.pgnColocate(njg / 2, (njg + 1) % 2)
        gestor.tablero.ponFlechaSC(move.from_sq, move.to_sq)
        gestor.put_view()

    ap.dispatch_bp(dispatch_bp)

    ap.xprocesa(game, tmp_bp)

    not_canceled = not tmp_bp.is_canceled()
    ap.terminar(not_canceled)

    if not_canceled:
        li_creados = []
        li_no_creados = []

        if alm.tacticblunders:
            if ap.siTacticBlunders:
                li_creados.append(alm.tacticblunders)
            else:
                li_no_creados.append(alm.tacticblunders)

        for x in (alm.pgnblunders, alm.fnsbrilliancies, alm.pgnbrilliancies):
            if x:
                if Util.exist_file(x):
                    li_creados.append(x)
                else:
                    li_no_creados.append(x)

        if alm.bmtblunders:
            if ap.si_bmt_blunders:
                li_creados.append(alm.bmtblunders)
            else:
                li_no_creados.append(alm.bmtblunders)
        if alm.bmtbrilliancies:
            if ap.si_bmt_brilliancies:
                li_creados.append(alm.bmtbrilliancies)
            else:
                li_no_creados.append(alm.bmtbrilliancies)

        if li_creados or li_no_creados:
            WDB_Utils.mensajeEntrenamientos(main_window, li_creados, li_no_creados)

    tmp_bp.cerrar()

    gestor.goto_end()

    if not_canceled:
        if alm.show_graphs:
            gestor.show_analysis()
