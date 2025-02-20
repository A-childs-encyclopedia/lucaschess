from Code.Base import Game

from Code.SQL import UtilSQL
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import QTUtil2
from Code.QT import QTVarios


class WAnotar(QTVarios.WDialogo):
    def __init__(self, procesador):

        self.procesador = procesador
        self.configuration = procesador.configuration
        self.resultado = None
        self.db = UtilSQL.DictSQL(self.configuration.ficheroAnotar)
        self.lista = self.db.keys(True, True)
        self.resultado = None

        QTVarios.WDialogo.__init__(self, procesador.main_window, _("Writing down moves of a game"), Iconos.Write(), "annotateagame")

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("DATE", _("Date"), 110)
        o_columns.nueva("COLOR", _("Color"), 80, centered=True)
        o_columns.nueva("GAME", _("Game"), 280)
        o_columns.nueva("MOVES", _("Moves"), 80, centered=True)
        o_columns.nueva("TIME", _("Avg time"), 80, centered=True)
        o_columns.nueva("ERRORS", _("Errors"), 80, centered=True)
        o_columns.nueva("HINTS", _("Hints"), 80, centered=True)
        self.glista = Grid.Grid(self, o_columns, siSelecFilas=True, siSeleccionMultiple=True)

        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.terminar),
            None,
            (_("New"), Iconos.Nuevo(), self.new),
            None,
            (_("Repeat"), Iconos.Copiar(), self.repetir),
            None,
            (_("Remove"), Iconos.Borrar(), self.borrar),
            None,
        )
        tb = Controles.TBrutina(self, li_acciones)

        ly = Colocacion.V().control(tb).control(self.glista).margen(4)

        self.setLayout(ly)

        self.register_grid(self.glista)
        self.restore_video(anchoDefecto=self.glista.anchoColumnas() + 20)
        self.glista.gotop()

    def grid_doble_click(self, grid, row, o_column):
        self.repetir()

    def repetir(self):
        recno = self.glista.recno()
        if recno >= 0:
            registro = self.db[self.lista[recno]]
            self.haz(registro["PC"])

    def new(self):
        self.haz(None)

    def haz(self, game_saved):
        if game_saved:
            game = Game.Game()
            game.restore(game_saved)
        else:
            game = None
        siblancasabajo = QTVarios.blancasNegras(self)
        if siblancasabajo is None:
            return
        self.resultado = game, siblancasabajo
        self.save_video()
        self.db.close()
        self.accept()

    def borrar(self):
        li = self.glista.recnosSeleccionados()
        if len(li) > 0:
            mens = _("Do you want to delete all selected records?")
            if QTUtil2.pregunta(self, mens):
                for row in li:
                    del self.db[self.lista[row]]
                recno = self.glista.recno()
                self.glista.refresh()
                self.lista = self.db.keys(True, True)
                if recno >= len(self.lista):
                    self.glista.gobottom()

    def grid_num_datos(self, grid):
        return len(self.lista)

    def game(self, reg):
        if isinstance(reg["PC"], Game.Game):
            game = reg["PC"]
        else:
            game = Game.Game()
            game.restore(reg["PC"])
        return game

    def grid_dato(self, grid, row, o_column):
        col = o_column.key
        reg = self.db[self.lista[row]]
        if not reg:
            return ""
        if col == "DATE":
            return self.lista[row]
        elif col == "GAME":
            return self.game(reg).titulo("DATE", "EVENT", "WHITE", "BLACK", "RESULT")
        elif col == "MOVES":
            total = reg.get("TOTAL_MOVES", len(self.game(reg)))
            moves = reg["MOVES"]
            if total == moves:
                return str(total)
            else:
                return "%d/%d" % (moves, total)
        elif col == "TIME":
            return '%0.2f"' % reg["TIME"]
        elif col == "HINTS":
            return str(reg["HINTS"])
        elif col == "ERRORS":
            return str(reg["ERRORS"])
        elif col == "COLOR":
            return _("White") if reg["COLOR"] else _("Black")

    def closeEvent(self, event):  # Cierre con X
        self.db.close()
        self.save_video()

    def terminar(self):
        self.db.close()
        self.save_video()
        self.reject()
