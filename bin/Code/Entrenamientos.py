import os
import random
import shutil

import Code
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.QT import Controles
from Code import TrListas
from Code import Util
from Code.SQL import UtilSQL
from Code.Constantes import *
from Code import Resistance
from Code import GestorFindAllMoves
from Code import GestorResistance
from Code import GestorTurnOnLights
from Code import GestorGM
from Code import GestorMate
from Code import TurnOnLights
from Code import Memoria
from Code import CompetitionWithTutor
from Code.QT import WCompetitionWithTutor
from Code.QT import Iconos
from Code.QT import PantallaBMT
from Code.QT import PantallaResistance
from Code.QT import PantallaDailyTest
from Code.QT import PantallaEverest
from Code.QT import PantallaGM
from Code.QT import PantallaHorses
from Code.QT import PantallaLearnPGN
from Code.QT import PantallaPotencia
from Code.QT import PantallaPuente
from Code.QT import PantallaVisualiza
from Code.QT import PantallaTurnOnLights
from Code.CountsCaptures import WCountsCaptures
from Code.Tactics import Tactics, GestorTacticas, PantallaTacticas
from Code.Mate15 import WMate15
from Code.Coordinates import WCoordinatesBlocks, WCoordinatesBasic


class TrainingFNS:
    def __init__(self, path, name):
        self.name = name
        self.path = path


class TrainingDir:
    def __init__(self, carpeta):
        dicTraining = TrListas.dicTraining()

        def trTraining(txt):
            return dicTraining.get(txt, txt)

        self.tr = trTraining

        self.name = trTraining(os.path.basename(carpeta))
        self.read(carpeta)

    def read(self, carpeta):
        folders = []
        files = []
        for elem in os.scandir(carpeta):
            if elem.is_dir():
                folders.append(TrainingDir(elem.path))
            elif elem.name.endswith(".fns"):
                name = self.tr(elem.name[:-4])
                files.append(TrainingFNS(elem.path, name))
        self.folders = sorted(folders, key=lambda td: td.name)
        self.files = sorted(files, key=lambda td: td.name)

    def addOtherFolder(self, folder):
        self.folders.append(TrainingDir(folder))

    def vacio(self):
        return (len(self.folders) + len(self.files)) == 0

    def reduce(self):
        liBorrar = []
        for n, folder in enumerate(self.folders):
            folder.reduce()
            if folder.vacio():
                liBorrar.append(n)
        if liBorrar:
            for n in range(len(liBorrar) - 1, -1, -1):
                del self.folders[liBorrar[n]]

    def menu(self, bmenu, xopcion):
        icoOp = Iconos.PuntoNaranja()
        icoDr = Iconos.Carpeta()
        for folder in self.folders:
            submenu1 = bmenu.submenu(folder.name, icoDr)
            folder.menu(submenu1, xopcion)
        for xfile in self.files:
            xopcion(bmenu, "ep_%s" % xfile.path, xfile.name, icoOp)


class Entrenamientos:
    def __init__(self, procesador):
        self.procesador = procesador
        self.parent = procesador.main_window
        self.configuracion = procesador.configuracion
        self.menu = None
        self.dicMenu = None

    def menuFNS(self, menu, rotulo, xopcion):
        td = TrainingDir(Code.path_resource("Trainings"))
        td.addOtherFolder(self.procesador.configuracion.dirPersonalTraining)
        bmenu = menu.submenu(rotulo, Iconos.Carpeta())
        td.reduce()  # Elimina carpetas vacias
        td.menu(bmenu, xopcion)

    def creaMenu(self):
        dicMenu = {}
        menu = QTVarios.LCMenu(self.parent)

        talpha = Controles.TipoLetra("Chess Alpha 2", self.configuracion.x_menu_points + 4)

        def xopcion(menu, key, texto, icono, is_disabled=False):
            if "KP" in texto:
                k2 = texto.index("K", 2)
                texto = texto[:k2] + texto[k2:].lower()
                menu.opcion(key, texto, icono, is_disabled, tipoLetra=talpha)
            else:
                menu.opcion(key, texto, icono, is_disabled)
            dicMenu[key] = (self.menu_run, texto, icono, is_disabled)

        # Posiciones de entrenamiento --------------------------------------------------------------------------
        self.menuFNS(menu, _("Training positions"), xopcion)
        menu.separador()

        # GM ---------------------------------------------------------------------------------------------------
        xopcion(menu, "gm", _("Play like a GrandMaster"), Iconos.GranMaestro())
        menu.separador()

        # Mate --------------------------------------------------------------------------------------------------
        menu1 = menu.submenu(_("Training mates"), Iconos.Mate())
        for mate in range(1, 8):
            xopcion(menu1, "mate%d" % mate, _X(_("Mate in %1"), str(mate)), Iconos.PuntoAzul())
            menu1.separador()
        menu.separador()

        # BMT -------------------------------------------------------------------------------------------
        xopcion(menu, "bmt", _("Find best move"), Iconos.BMT())
        menu.separador()

        # Resistencia ------------------------------------------------------------------------------------------
        menu1 = menu.submenu(_("Resistance Test"), Iconos.Resistencia())
        nico = Util.Rondo(Iconos.Verde(), Iconos.Azul(), Iconos.Amarillo(), Iconos.Naranja())
        xopcion(menu1, "resistance", _("Normal"), nico.otro())
        xopcion(menu1, "resistancec", _("Blindfold chess"), nico.otro())
        xopcion(menu1, "resistancep1", _("Hide only our pieces"), nico.otro())
        xopcion(menu1, "resistancep2", _("Hide only opponent pieces"), nico.otro())
        menu.separador()

        # DailyTest ------------------------------------------------------------------------------------------------
        xopcion(menu, "dailytest", _("Your daily test"), Iconos.DailyTest())
        menu.separador()

        # Tacticas ---------------------------------------------------------------------------------------------
        menu1 = menu.submenu(_("Learn tactics by repetition"), Iconos.Tacticas())
        nico = Util.Rondo(Iconos.Amarillo(), Iconos.Naranja(), Iconos.Verde(), Iconos.Azul(), Iconos.Magenta())
        dicTraining = TrListas.dicTraining()

        def trTraining(txt):
            return dicTraining.get(txt, txt)

        def menu_tacticas(submenu, tipo, carpeta_base, lista):
            if os.path.isdir(carpeta_base):
                for entry in os.scandir(carpeta_base):
                    if entry.is_dir():
                        carpeta = entry.path
                        ini = os.path.join(carpeta, "Config.ini")
                        if os.path.isfile(ini):
                            name = entry.name
                            xopcion(
                                submenu,
                                "tactica|%s|%s|%s|%s" % (tipo, name, carpeta, ini),
                                trTraining(name),
                                nico.otro(),
                            )
                            menu1.separador()
                            lista.append((carpeta, name))
                        else:
                            submenu1 = submenu.submenu(entry.name, nico.otro())
                            menu_tacticas(submenu1, tipo, carpeta, lista)
            return lista

        menu_tacticas(menu1, TACTICS_BASIC, Code.path_resource("Tactics"), [])
        lista = []
        carpetaTacticasP = os.path.join(self.configuracion.dirPersonalTraining, "Tactics")
        if os.path.isdir(carpetaTacticasP):
            submenu1 = menu1.submenu(_("Personal tactics"), nico.otro())
            lista = menu_tacticas(submenu1, TACTICS_PERSONAL, carpetaTacticasP, lista)
            if lista:
                ico = Iconos.Delete()
                menub = menu1.submenu(_("Remove"), ico)
                for carpeta, name in lista:
                    xopcion(menub, "remtactica|%s|%s" % (carpeta, name), trTraining(name), ico)

        menu.separador()

        # Longs ----------------------------------------------------------------------------------------
        menu1 = menu.submenu(_("Long-term trainings"), Iconos.Longhaul())
        # Maps
        menu2 = menu1.submenu(_("Training on a map"), Iconos.Maps())
        xopcion(menu2, "map_Africa", _("Africa map"), Iconos.Africa())
        menu2.separador()
        xopcion(menu2, "map_WorldMap", _("World map"), Iconos.WorldMap())
        # Rail
        menu1.separador()
        xopcion(menu1, "transsiberian", _("Transsiberian Railway"), Iconos.Train())
        # Everest
        menu1.separador()
        xopcion(menu1, "everest", _("Expeditions to the Everest"), Iconos.Trekking())
        # TOL
        menu1.separador()
        menu2 = menu1.submenu(_("Turn on the lights"), Iconos.TOL())
        menu.separador()
        menu3 = menu2.submenu(_("Memory mode"), Iconos.TOL())
        xopcion(menu3, "tol_uned_easy", "%s (%s)" % (_("UNED chess school"), _("Initial")), Iconos.Uned())
        menu3.separador()
        xopcion(menu3, "tol_uned", "%s (%s)" % (_("UNED chess school"), _("Complete")), Iconos.Uned())
        menu3.separador()
        xopcion(menu3, "tol_uwe_easy", "%s (%s)" % (_("Uwe Auerswald"), _("Initial")), Iconos.Uwe())
        menu3.separador()
        xopcion(menu3, "tol_uwe", "%s (%s)" % (_("Uwe Auerswald"), _("Complete")), Iconos.Uwe())
        menu2.separador()
        menu3 = menu2.submenu(_("Calculation mode"), Iconos.Calculo())
        xopcion(menu3, "tol_uned_easy_calc", "%s (%s)" % (_("UNED chess school"), _("Initial")), Iconos.Uned())
        menu3.separador()
        xopcion(menu3, "tol_uned_calc", "%s (%s)" % (_("UNED chess school"), _("Complete")), Iconos.Uned())
        menu3.separador()
        xopcion(menu3, "tol_uwe_easy_calc", "%s (%s)" % (_("Uwe Auerswald"), _("Initial")), Iconos.Uwe())
        menu3.separador()
        xopcion(menu3, "tol_uwe_calc", "%s (%s)" % (_("Uwe Auerswald"), _("Complete")), Iconos.Uwe())
        # Washing
        menu2.separador()
        xopcion(menu2, "tol_oneline", _("In one line"), Iconos.TOLline())
        menu1.separador()
        xopcion(menu1, "washing_machine", _("The Washing Machine"), Iconos.WashingMachine())

        # Cebras ---------------------------------------------------------------------------------------------------
        menu.separador()
        # menu1 = menu.submenu(_("Resources for zebras"), Iconos.Cebra())
        menu2 = menu.submenu(_("Check your memory on a chessboard"), Iconos.Memoria())

        mem = Memoria.Memoria(self.procesador)
        categorias = CompetitionWithTutor.Categorias()

        for x in range(6):
            cat = categorias.number(x)
            txt = cat.name()

            nm = mem.nivel(x)
            if nm >= 0:
                txt += " %s %d" % (_("Level"), nm + 1)

            xopcion(menu2, -100 - x, txt, cat.icono(), is_disabled=not mem.is_active(x))

        menu.separador()

        menu2 = menu.submenu(_("Find all moves"), Iconos.FindAllMoves())
        xopcion(menu2, "find_all_moves_rival", _("Opponent"), Iconos.PuntoNaranja())
        xopcion(menu2, "find_all_moves_player", _("Player"), Iconos.PuntoAzul())

        menu.separador()
        self.horsesDef = hd = {
            1: ("N", "Alpha", _("Basic test")),
            2: ("p", "Fantasy", _("Four pawns test")),
            3: ("Q", "Pirat", _("Jonathan Levitt test")),
            4: ("n", "Spatial", _("Basic test") + ": a1"),
            5: ("N", "Cburnett", _("Basic test") + ": e4"),
        }
        menu2 = menu.submenu(_("Becoming a knight tamer"), Iconos.Knight())
        vicon = Code.todasPiezas.icono
        icl, icn, tit = hd[1]
        menu3 = menu2.submenu(tit, vicon(icl, icn))
        xopcion(menu3, "horses_1", tit, vicon(icl, icn))
        menu3.separador()
        icl, icn, tit = hd[4]
        xopcion(menu3, "horses_4", tit, vicon(icl, icn))
        menu3.separador()
        icl, icn, tit = hd[5]
        xopcion(menu3, "horses_5", tit, vicon(icl, icn))
        menu2.separador()
        icl, icn, tit = hd[2]
        xopcion(menu2, "horses_2", tit, vicon(icl, icn))
        menu2.separador()
        icl, icn, tit = hd[3]
        xopcion(menu2, "horses_3", tit, vicon(icl, icn))

        menu.separador()
        menu2 = menu.submenu(_("Moves between two positions"), Iconos.Puente())
        rp = QTVarios.rondoPuntos()
        for x in range(1, 11):
            xopcion(menu2, "puente_%d" % x, "%s %d" % (_("Level"), x), rp.otro())

        menu.separador()
        xopcion(menu, "potencia", _("Determine your calculating power"), Iconos.Potencia())

        menu.separador()
        menu2 = menu.submenu(_("Learn a game"), Iconos.School())
        xopcion(menu2, "learnPGN", _("Memorizing their moves"), Iconos.LearnGame())
        menu2.separador()
        xopcion(menu2, "playPGN", _("Playing against"), Iconos.Law())

        menu.separador()
        xopcion(menu, "visualiza", _("The board at a glance"), Iconos.Gafas())

        menu.separador()
        menu2 = menu.submenu(_("Coordinates"), Iconos.Coordinates())
        xopcion(menu2, "coordinates_basic", _("Basic"), Iconos.West())
        menu2.separador()
        xopcion(menu2, "coordinates_blocks", _("By blocks"), Iconos.Blocks())

        menu.separador()
        xopcion(menu, "anotar", _("Writing down moves of a game"), Iconos.Write())

        menu.separador()
        xopcion(menu, "captures", _("Captures and threats in a game"), Iconos.Captures())

        menu.separador()
        xopcion(menu, "counts", _("Count moves"), Iconos.Count())

        menu.separador()
        xopcion(menu, "15mate", _("Mate in 1½"), Iconos.Mate15())

        menu.separador()
        xopcion(menu, "endings_gtb", _("Endings with Gaviota Tablebases"), Iconos.Finales())

        return menu, dicMenu

    def comprueba(self):
        if self.menu is None:
            self.menu, self.dicMenu = self.creaMenu()

    def rehaz(self):
        self.menu, self.dicMenu = self.creaMenu()

    def lanza(self):
        self.comprueba()

        resp = self.menu.lanza()
        self.menu_run(resp)

    def menu_run(self, resp):
        if resp:
            if type(resp) == str:
                if resp == "gm":
                    self.entrenaGM()

                elif resp.startswith("mate"):
                    self.jugarMate(int(resp[-1]))

                elif resp == "bmt":
                    self.bmt()

                elif resp.startswith("resistance"):
                    self.resistance(resp[10:])

                elif resp in ["find_all_moves_rival", "find_all_moves_player"]:
                    self.find_all_moves(resp == "find_all_moves_player")

                elif resp == "dailytest":
                    self.dailyTest()

                elif resp == "potencia":
                    self.potencia()

                elif resp == "visualiza":
                    self.visualiza()

                elif resp == "anotar":
                    self.anotar()

                elif resp == "endings_gtb":
                    self.gaviota_endings()

                elif resp.startswith("tactica|"):
                    nada, tipo, name, carpeta, ini = resp.split("|")
                    self.tacticas(tipo, name, carpeta, ini)

                elif resp.startswith("remtactica|"):
                    nada, carpeta, name = resp.split("|")
                    self.tacticaRemove(carpeta, name)

                elif resp.startswith("puente_"):
                    self.puente(int(resp[7:]))

                elif resp.startswith("horses_"):
                    test = int(resp[7])
                    icl, icn, tit = self.horsesDef[test]
                    icon = Code.todasPiezas.icono(icl, icn)
                    self.horses(test, tit, icon)

                elif resp.startswith("ep_"):
                    um = self.procesador.unMomento()
                    entreno = os.path.realpath(resp[3:])
                    titentreno = os.path.relpath(entreno, Code.folder_root)
                    # if "/" in entreno:
                    #     dicTraining = TrListas.dicTraining()
                    #     titentreno = ""
                    #     for x in entreno[:-4].split("/")[1:]:
                    #         titentreno += dicTraining.get(x, x) + "/"
                    #     titentreno = titentreno[:-1]
                    with Util.OpenCodec(entreno) as f:
                        todo = f.read().strip()
                    liEntrenamientos = todo.split("\n")
                    nPosiciones = len(liEntrenamientos)
                    um.final()
                    if nPosiciones == 0:
                        return
                    elif nPosiciones == 1:
                        pos = 1
                        jump = False
                    else:
                        db = UtilSQL.DictSQL(self.configuracion.ficheroTrainings)
                        data = db[entreno]
                        jump = False
                        tipo = "s"
                        if data is None:
                            posUltimo = 1
                        elif type(data) == int:
                            posUltimo = data
                        else:
                            posUltimo = data["POSULTIMO"]
                            jump = data["SALTA"]
                            tipo = data["TIPO"]
                        resp = WCompetitionWithTutor.numPosicion(
                            self.procesador.main_window, titentreno, nPosiciones, posUltimo, jump, tipo
                        )
                        if resp is None:
                            db.close()
                            return
                        pos, tipo, jump = resp
                        db[entreno] = {"POSULTIMO": pos, "SALTA": jump, "TIPO": tipo}
                        db.close()
                        if tipo.startswith("r"):
                            if tipo == "rk":
                                random.seed(pos)
                            random.shuffle(liEntrenamientos)
                    self.procesador.entrenaPos(pos, nPosiciones, titentreno, liEntrenamientos, entreno, jump)

                elif resp == "learnPGN":
                    self.learnPGN()

                elif resp == "playPGN":
                    self.procesador.playPGN()

                elif resp.startswith("map_"):
                    nada, mapa = resp.split("_")
                    self.procesador.trainingMap(mapa)

                elif resp == "transsiberian":
                    self.procesador.showRoute()

                elif resp == "everest":
                    self.everest()

                elif resp.startswith("tol_"):
                    self.turn_on_lights(resp[4:])

                elif resp == "washing_machine":
                    self.washing_machine()

                elif resp == "captures":
                    self.captures()

                elif resp == "counts":
                    self.counts()

                elif resp == "15mate":
                    self.mate15()

                elif resp == "coordinates_blocks":
                    self.coordinates_blocks()

                elif resp == "coordinates_basic":
                    self.coordinates_basic()

            else:
                if resp <= -100:
                    self.menu = None  # ya que puede cambiar y la etiqueta es diferente
                    mem = Memoria.Memoria(self.procesador)
                    mem.lanza(abs(resp) - 100)

    def tacticas(self, tipo, name, carpeta, ini):
        um = self.procesador.unMomento()
        tacticas = Tactics.Tactics(tipo, name, carpeta, ini)
        liMenus = tacticas.listaMenus()
        if len(liMenus) == 0:
            um.final()
            return

        nico = QTVarios.rondoPuntos()
        if len(liMenus) > 1:
            menu = QTVarios.LCMenu(self.parent)
            menu.opcion(None, _SP(name), Iconos.Tacticas())
            menu.separador()

            dmenu = {}
            for valor, lista in liMenus:
                actmenu = menu
                if len(lista) > 1:
                    t = ""
                    for x in range(len(lista) - 1):
                        t += "|%s" % lista[x]
                        if not (t in dmenu):
                            dmenu[t] = actmenu.submenu(_SP(lista[x]), nico.otro())
                            actmenu.separador()
                        actmenu = dmenu[t]
                actmenu.opcion(valor, _SP(lista[-1]), nico.otro())
                actmenu.separador()
            um.final()
            resp = menu.lanza()

        else:
            resp = liMenus[0][0]

        if not resp:
            um.final()
            return

        tactica = tacticas.eligeTactica(resp, self.configuracion.carpeta_results)

        um.final()
        if tactica:
            self.entrenaTactica(tactica)

    def tacticaRemove(self, carpeta, name):
        if QTUtil2.pregunta(self.procesador.main_window, _X(_("Delete %1?"), name)):
            shutil.rmtree(carpeta)
            self.rehaz()

    def entrenaTactica(self, tactica):
        icono = Iconos.PuntoMagenta()
        resp = PantallaTacticas.consultaHistorico(self.procesador.main_window, tactica, icono)
        if resp:
            if resp != "seguir":
                if resp != "auto":
                    if resp.startswith("copia"):
                        ncopia = int(resp[5:])
                    else:
                        ncopia = None
                    if not PantallaTacticas.edita1tactica(self.procesador.main_window, tactica, ncopia):
                        return
                um = self.procesador.unMomento()
                tactica.genera()
                um.final()
            self.procesador.game_type = GT_TACTICS
            self.procesador.state = ST_PLAYING
            self.procesador.gestor = GestorTacticas.GestorTacticas(self.procesador)
            self.procesador.gestor.inicio(tactica)

    def entrenaGM(self):
        w = PantallaGM.WGM(self.procesador)
        if w.exec_():
            self.procesador.game_type = GT_AGAINST_GM
            self.procesador.state = ST_PLAYING
            self.procesador.gestor = GestorGM.GestorGM(self.procesador)
            self.procesador.gestor.inicio(w.record)

    def find_all_moves(self, siJugador):
        self.procesador.gestor = GestorFindAllMoves.GestorFindAllMoves(self.procesador)
        self.procesador.gestor.inicio(siJugador)

    def jugarMate(self, tipo):
        self.procesador.gestor = GestorMate.GestorMate(self.procesador)
        self.procesador.gestor.inicio(tipo)

    def dailyTest(self):
        PantallaDailyTest.dailyTest(self.procesador)

    def potencia(self):
        PantallaPotencia.pantallaPotencia(self.procesador)

    def visualiza(self):
        PantallaVisualiza.pantallaVisualiza(self.procesador)

    def anotar(self):
        self.procesador.show_anotar()

    def gaviota_endings(self):
        self.procesador.gaviota_endings()

    def puente(self, nivel):
        PantallaPuente.pantallaPuente(self.procesador, nivel)

    def horses(self, test, titulo, icono):
        PantallaHorses.pantallaHorses(self.procesador, test, titulo, icono)

    def bmt(self):
        PantallaBMT.pantallaBMT(self.procesador)

    def resistance(self, tipo):
        resistance = Resistance.Resistance(self.procesador, tipo)
        resp = PantallaResistance.pantallaResistance(self.procesador.main_window, resistance)
        if resp is not None:
            numEngine, key = resp
            self.procesador.gestor = GestorResistance.GestorResistance(self.procesador)
            self.procesador.gestor.inicio(resistance, numEngine, key)

    def learnPGN(self):
        w = PantallaLearnPGN.WLearnBase(self.procesador)
        w.exec_()

    def everest(self):
        PantallaEverest.everest(self.procesador)

    def turn_on_lights(self, name):
        one_line = False
        if name.startswith("uned_easy"):
            title = "%s (%s)" % (_("UNED chess school"), _("Initial"))
            folder = Code.path_resource("Trainings", "Tactics by UNED chess school")
            icono = Iconos.Uned()
            li_tam_blocks = (4, 6, 9, 12, 18, 36)
        elif name.startswith("uned"):
            title = _("UNED chess school")
            folder = Code.path_resource("Trainings", "Tactics by UNED chess school")
            icono = Iconos.Uned()
            li_tam_blocks = (6, 12, 20, 30, 60)
        elif name.startswith("uwe_easy"):
            title = "%s (%s)" % (_("Uwe Auerswald"), _("Initial"))
            TurnOnLights.compruebaUweEasy(self.configuracion, name)
            folder = self.configuracion.carpetaTemporal()
            icono = Iconos.Uwe()
            li_tam_blocks = (4, 6, 9, 12, 18, 36)
        elif name.startswith("uwe"):
            title = _("Uwe Auerswald")
            folder = Code.path_resource("Trainings", "Tactics by Uwe Auerswald")
            icono = Iconos.Uwe()
            li_tam_blocks = (5, 10, 20, 40, 80)
        elif name == "oneline":
            title = _("In one line")
            folder = None
            icono = Iconos.TOLline()
            li_tam_blocks = None
            one_line = True

        resp = PantallaTurnOnLights.pantallaTurnOnLigths(
            self.procesador, name, title, icono, folder, li_tam_blocks, one_line
        )
        if resp:
            num_theme, num_block, tol = resp
            self.procesador.game_type = GT_TURN_ON_LIGHTS
            self.procesador.state = ST_PLAYING
            self.procesador.gestor = GestorTurnOnLights.GestorTurnOnLights(self.procesador)
            self.procesador.gestor.inicio(num_theme, num_block, tol)

    def washing_machine(self):
        self.procesador.showWashing()

    def captures(self):
        w = WCountsCaptures.WCountsCaptures(self.procesador, True)
        w.exec_()

    def counts(self):
        w = WCountsCaptures.WCountsCaptures(self.procesador, False)
        w.exec_()

    def mate15(self):
        w = WMate15.WMate15(self.procesador)
        w.exec_()

    def coordinates_blocks(self):
        w = WCoordinatesBlocks.WCoordinatesBlocks(self.procesador)
        w.exec_()

    def coordinates_basic(self):
        w = WCoordinatesBasic.WCoordinatesBasic(self.procesador)
        w.exec_()


def selectOneFNS(owner, procesador):
    tpirat = Controles.TipoLetra("Chess Alpha 2", procesador.configuracion.x_menu_points + 4)

    def xopcion(menu, key, texto, icono, is_disabled=False):
        if "KP" in texto:
            k2 = texto.index("K", 2)
            texto = texto[:k2] + texto[k2:].lower()
            menu.opcion(key, texto, icono, is_disabled, tipoLetra=tpirat)
        else:
            menu.opcion(key, texto, icono, is_disabled)

    menu = QTVarios.LCMenu(owner)
    td = TrainingDir(Code.path_resource("Trainings"))
    td.addOtherFolder(procesador.configuracion.dirPersonalTraining)
    td.reduce()
    td.menu(menu, xopcion)
    resp = menu.lanza()
    return resp if resp is None else resp[3:]