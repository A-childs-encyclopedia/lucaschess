import Code
from Code import Util
from Code.Databases import DBgames, PantallaDatabase
from Code.QT import Colocacion, Columnas, Controles, Grid, Iconos, QTUtil2, QTVarios

from Code.CountsCaptures import CountsCaptures, WRunCaptures, WRunCounts


class WCountsCaptures(QTVarios.WDialogo):
    def __init__(self, procesador, is_captures):
        configuracion = procesador.configuracion
        self.is_captures = is_captures
        if is_captures:
            path = configuracion.file_captures()
            title = _("Captures and threats in a game")
            icon = Iconos.Captures()
            extconfig = "captures"
        else:
            path = configuracion.file_counts()
            title = _("Count moves")
            icon = Iconos.Count()
            extconfig = "counts"

        self.db = CountsCaptures.DBCountCapture(path)

        QTVarios.WDialogo.__init__(self, procesador.main_window, title, icon, extconfig)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("DATE", _("Date"), 120, centered=True)
        o_columns.nueva("GAME", _("Game"), 520, centered=True)
        o_columns.nueva("CURRENT_MOVE", _("Current move"), 96, centered=True)
        o_columns.nueva("%", _("Success"), 90, centered=True)
        self.glista = Grid.Grid(self, o_columns, siSelecFilas=True, siSeleccionMultiple=True)
        f = Controles.TipoLetra(puntos=configuracion.x_menu_points)
        self.glista.ponFuente(f)

        li_acciones = (
            (_("Close"), Iconos.MainMenu(), self.terminar),
            None,
            (_("Play"), Iconos.Play(), self.play),
            None,
            (_("New"), Iconos.Nuevo(), self.new),
            None,
            (_("Repeat"), Iconos.Copiar(), self.repetir),
            None,
            (_("Remove"), Iconos.Borrar(), self.borrar),
            None,
        )
        tb = QTVarios.LCTB(self, li_acciones)

        ly = Colocacion.V().control(tb).control(self.glista).margen(4)

        self.setLayout(ly)

        self.register_grid(self.glista)
        self.restore_video(anchoDefecto=self.glista.anchoColumnas() + 20)
        self.glista.gotop()

    def grid_doble_click(self, grid, fila, oColumna):
        self.play()

    def repetir(self):
        recno = self.glista.recno()
        if recno >= 0:
            capture = self.db.count_capture(recno)
            self.db.new_count_capture(capture.copy())
            self.glista.refresh()

    def new(self):
        menu = QTVarios.LCMenu(self)
        menu.opcion("random", _("Random"), Iconos.SQL_RAW())
        menu.separador()
        if not QTVarios.lista_db(Code.configuracion, True).is_empty():
            menu.opcion("db", _("Game in a database"), Iconos.Database())
            menu.separador()
        menu.opcion("pgn", _("Game in a pgn"), Iconos.Filtrar())
        menu.separador()
        resp = menu.lanza()
        game = None
        if resp == "random":
            game = DBgames.get_random_game()
        elif resp == "pgn":
            game = Code.procesador.select_1_pgn(self)
        elif resp == "db":
            db = QTVarios.select_db(self, Code.configuracion, True, False)
            if db:
                w = PantallaDatabase.WBDatabase(self, Code.procesador, db, False, True)
                resp = w.exec_()
                if resp:
                    game = w.game
        if game is None:
            return
        capture = CountsCaptures.CountCapture()
        capture.game = game
        self.db.new_count_capture(capture)
        self.glista.refresh()

    def borrar(self):
        li = self.glista.recnosSeleccionados()
        if len(li) > 0:
            mens = _("Do you want to delete all selected records?")
            if QTUtil2.pregunta(self, mens):
                self.db.remove_count_captures(li)
                recno = self.glista.recno()
                self.glista.refresh()
                if recno >= self.grid_num_datos(None):
                    self.glista.gobottom()

    def grid_num_datos(self, grid):
        return len(self.db)

    def grid_dato(self, grid, fila, oColumna):
        count_capture = self.db.count_capture(fila)
        col = oColumna.clave
        if col == "DATE":
            return Util.dtostr_hm(count_capture.date)
        elif col == "GAME":
            return count_capture.game.titulo("DATE", "EVENT", "WHITE", "BLACK", "RESULT")
        elif col == "CURRENT_MOVE":
            if count_capture.is_finished():
                return "%s/%d" % (_("Ended"), len(count_capture.game))
            return "%d/%d" % (count_capture.current_posmove+1, len(count_capture.game))
        elif col == "%":
            return "%.01f%%" % (count_capture.success() * 100.0,)
        else:
            return col

    def closeEvent(self, event):  # Cierre con X
        self.save_video()

    def terminar(self):
        self.save_video()
        self.accept()

    def play(self):
        recno = self.glista.recno()
        if recno >= 0:
            count_capture = self.db.count_capture(recno)
            if not count_capture.is_finished():
                if self.is_captures:
                    w = WRunCaptures.WRunCaptures(self, self.db, count_capture)
                else:
                    w = WRunCounts.WRunCounts(self, self.db, count_capture)
                w.exec_()