from Code.Base import Game
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.Config import TrListas
from Code import Util
from Code.SQL import UtilSQL
from Code.Databases import WindowDatabase


class DBPlayGame(UtilSQL.DictSQL):
    def __init__(self, file):
        UtilSQL.DictSQL.__init__(self, file)
        self.regKeys = self.keys(True, True)

    def leeRegistro(self, num):
        return self.__getitem__(self.regKeys[num])

    def append(self, valor):
        k = str(Util.today())
        self.__setitem__(k, valor)
        self.regKeys = self.keys(True, True)

    def appendHash(self, xhash, valor):
        """Usado from_sq databases-games, el hash = hash del xpv"""
        k = str(Util.today()) + "|" + str(xhash)
        self.__setitem__(k, valor)
        self.regKeys = self.keys(True, True)

    def recnoHash(self, xhash):
        """Usado from_sq databases-games"""
        for recno, key in enumerate(self.regKeys):
            if "|" in key:
                h = int(key.split("|")[1])
                if xhash == h:
                    return recno
        return None

    def cambiaRegistro(self, num, valor):
        self.__setitem__(self.regKeys[num], valor)

    def borraRegistro(self, num):
        self.__delitem__(self.regKeys[num])
        self.regKeys = self.keys(True, True)

    def borraLista(self, li):
        li.sort()
        li.reverse()
        for x in li:
            self.__delitem__(self.regKeys[x])
        self.pack()
        self.regKeys = self.keys(True, True)

    def label(self, num):
        r = self.leeRegistro(num)
        game = Game.Game()
        game.restore(r["GAME"])

        def x(k):
            return game.get_tag(k)

        date = x("DATE").replace(".?", "").replace("?", "")
        return "%s-%s : %s %s %s" % (x("WHITE"), x("BLACK"), date, x("EVENT"), x("SITE"))


class WPlayGameBase(QTVarios.WDialogo):
    def __init__(self, procesador):

        titulo = _("Play against a game")
        QTVarios.WDialogo.__init__(self, procesador.main_window, titulo, Iconos.Law(), "playgame")

        self.procesador = procesador
        self.configuration = procesador.configuration
        self.recno = None

        self.db = DBPlayGame(self.configuration.file_play_game())

        # Historico
        o_columns = Columnas.ListaColumnas()

        def creaCol(key, label, centered=True):
            o_columns.nueva(key, label, 80, centered=centered)

        # # Claves segun orden estandar
        self.li_keys = liBasic = ("EVENT", "SITE", "DATE", "ROUND", "WHITE", "BLACK", "RESULT", "ECO", "FEN", "WHITEELO", "BLACKELO")
        for key in liBasic:
            label = TrListas.pgnLabel(key)
            creaCol(key, label, key != "EVENT")
        self.grid = Grid.Grid(self, o_columns, siSelecFilas=True, siSeleccionMultiple=True)
        self.grid.setMinimumWidth(self.grid.anchoColumnas() + 20)

        # Tool bar
        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.terminar),
            None,
            (_("Play"), Iconos.Empezar(), self.play),
            (_("New"), Iconos.Nuevo(), self.new),
            None,
            (_("Remove"), Iconos.Borrar(), self.remove),
            None,
        )
        self.tb = QTVarios.LCTB(self, li_acciones)

        # Colocamos
        lyTB = Colocacion.H().control(self.tb).margen(0)
        ly = Colocacion.V().otro(lyTB).control(self.grid).margen(3)

        self.setLayout(ly)

        self.register_grid(self.grid)
        self.restore_video(siTam=False)

        self.grid.gotop()

    def grid_doble_click(self, grid, row, column):
        self.play()

    def grid_num_datos(self, grid):
        return len(self.db)

    def grid_dato(self, grid, row, o_column):
        col = o_column.key
        reg = self.db.leeRegistro(row)
        if "CACHE" in reg:
            dic_tags = reg["CACHE"]
        else:
            game = Game.Game()
            game.restore(reg["GAME"])
            reg["CACHE"] = {k: game.get_tag(k) for k in self.li_keys}
            self.db.cambiaRegistro(row, reg)
        return reg["CACHE"].get(col, "")

    def terminar(self):
        self.save_video()
        self.db.close()
        self.accept()

    def closeEvent(self, QCloseEvent):
        self.save_video()
        self.db.close()

    def new(self):
        menu = QTVarios.LCMenu(self)
        if not QTVarios.lista_db(self.configuration, True).is_empty():
            menu.opcion("db", _("Game in a database"), Iconos.Database())
            menu.separador()
        menu.opcion("pgn", _("Game in a pgn"), Iconos.Filtrar())
        menu.separador()
        resp = menu.lanza()
        game = None
        if resp == "pgn":
            game = self.procesador.select_1_pgn(self)
        elif resp == "db":
            db = QTVarios.select_db(self, self.configuration, True, False)
            if db:
                w = WindowDatabase.WBDatabase(self, self.procesador, db, False, True)
                resp = w.exec_()
                if resp:
                    game = w.game
        if game and len(game) > 0:
            reg = {"GAME": game.save()}
            self.db.append(reg)
            self.grid.refresh()
            self.grid.gotop()

    def remove(self):
        li = self.grid.recnosSeleccionados()
        if len(li) > 0:
            if QTUtil2.pregunta(self, _("Do you want to delete all selected records?")):
                self.db.borraLista(li)
        self.grid.gotop()
        self.grid.refresh()

    def play(self):
        li = self.grid.recnosSeleccionados()
        if len(li) > 0:
            recno = li[0]
            w = WPlay1(self, self.configuration, self.db, recno)
            if w.exec_():
                self.recno = recno
                self.is_white = w.is_white
                self.accept()


class WPlay1(QTVarios.WDialogo):
    def __init__(self, owner, configuration, db, recno):

        QTVarios.WDialogo.__init__(self, owner, _("Play against a game"), Iconos.PlayGame(), "play1game")

        self.owner = owner
        self.db = db
        self.configuration = configuration
        self.recno = recno
        self.registro = self.db.leeRegistro(recno)

        self.game = Game.Game()
        self.game.restore(self.registro["GAME"])

        self.lbRotulo = Controles.LB(self, self.db.label(recno)).ponTipoLetra(puntos=12).set_foreground_backgound("#076C9F", "#EFEFEF")

        self.liIntentos = self.registro.get("LIINTENTOS", [])

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("DATE", _("Date"), 80, centered=True)
        o_columns.nueva("COLOR", _("Play with"), 80, centered=True)
        o_columns.nueva("POINTS", _("Score"), 80, centered=True)
        o_columns.nueva("TIME", _("Time"), 80, centered=True)
        self.grid = Grid.Grid(self, o_columns, siSelecFilas=True, siSeleccionMultiple=True)
        self.grid.setMinimumWidth(self.grid.anchoColumnas() + 20)

        # Tool bar
        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.terminar),
            None,
            (_("Train"), Iconos.Entrenar(), self.empezar),
            None,
            (_("Remove"), Iconos.Borrar(), self.borrar),
            None,
        )
        self.tb = QTVarios.LCTB(self, li_acciones)

        # Colocamos
        lyTB = Colocacion.H().control(self.tb).margen(0)
        ly = Colocacion.V().otro(lyTB).control(self.grid).control(self.lbRotulo).margen(3)

        self.setLayout(ly)

        self.register_grid(self.grid)
        self.restore_video(siTam=False)

        self.grid.gotop()

    def grid_num_datos(self, grid):
        return len(self.liIntentos)

    def grid_dato(self, grid, row, o_column):
        col = o_column.key
        reg = self.liIntentos[row]

        if col == "DATE":
            f = reg["DATE"]
            return "%02d/%02d/%d-%02d:%02d" % (f.day, f.month, f.year, f.hour, f.minute)
        if col == "COLOR":
            c = reg["COLOR"]
            if c == "b":
                return _("Black")
            elif c == "w":
                return _("White")
        if col == "POINTS":
            return "%d (%d)" % (reg["POINTS"], reg["POINTSMAX"])
        if col == "TIME":
            s = int(reg["TIME"])
            m = int(s / 60)
            s -= m * 60
            return "%d' %d\"" % (m, s)

    def guardar(self, dic):
        self.liIntentos.insert(0, dic)
        self.grid.refresh()
        self.grid.gotop()
        self.registro["LIINTENTOS"] = self.liIntentos
        self.db.cambiaRegistro(self.numRegistro, self.registro)

    def terminar(self, siAccept=False):
        self.save_video()
        if siAccept:
            self.accept()
        else:
            self.reject()

    def borrar(self):
        li = self.grid.recnosSeleccionados()
        if len(li) > 0:
            if QTUtil2.pregunta(self, _("Do you want to delete all selected records?")):
                li.sort()
                li.reverse()
                for x in li:
                    del self.liIntentos[x]
        self.grid.gotop()
        self.grid.refresh()

    def empezar(self):
        self.is_white = QTVarios.blancasNegras(self)
        self.terminar(True)
