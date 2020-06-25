import copy

import Code.SQL.Base as SQLBase


class BMT(SQLBase.DBBase):
    def __init__(self, nom_fichero):
        SQLBase.DBBase.__init__(self, nom_fichero)

        self.tabla = "DATOS"

        if not self.existeTabla(self.tabla):
            cursor = self.conexion.cursor()
            for sql in (
                "CREATE TABLE %s( ESTADO VARCHAR(1),ORDEN INTEGER,NOMBRE TEXT,EXTRA TEXT,TOTAL INTEGER,HECHOS INTEGER,"
                "PUNTOS INTEGER,MAXPUNTOS INTEGER,FINICIAL VARCHAR(8),FFINAL VARCHAR(8),SEGUNDOS INTEGER,REPE INTEGER,"
                "BMT_LISTA BLOB,HISTORIAL BLOB);",
                "CREATE INDEX [NOMBRE] ON '%s'(ORDEN DESC,NOMBRE);",
            ):
                cursor.execute(sql % self.tabla)
                self.conexion.commit()
            cursor.close()
        self.db = None

    def read_dbf(self, si_terminadas):
        select = "ESTADO,ORDEN,NOMBRE,EXTRA,TOTAL,HECHOS,PUNTOS,MAXPUNTOS,FFINAL,SEGUNDOS,REPE"
        condicion = "HECHOS=TOTAL" if si_terminadas else "HECHOS<TOTAL"
        orden = "ORDEN DESC,NOMBRE"
        dbf = self.dbf(self.tabla, select, condicion, orden)
        dbf.leer()
        self.db = dbf
        return dbf

    def cerrar(self):
        if self.db:
            self.db.cerrar()
            self.db = None
        if self.conexion:
            self.conexion.close()
            self.conexion = None


class BMTUno:
    def __init__(self, fen, mrm, max_puntos, cl_game):
        self.fen = fen
        self.mrm = mrm
        self.put_color()

        self.puntos = max_puntos
        self.max_puntos = max_puntos
        self.segundos = 0
        self.state = 0
        self.finished = False
        self.cl_game = cl_game

    def put_color(self):
        is_white = "w" in self.fen
        self.mrm.is_white = is_white
        for rm in self.mrm.li_rm:
            rm.is_white = is_white

    def condiciones(self):
        try:
            return "%s - %d %s" % (self.mrm.name, self.mrm.vtime / 1000, _("Second(s)")) if self.mrm.name else ""
        except:
            return ""

    def update_state(self):
        self.state = 0
        if self.finished:
            if self.max_puntos:
                self.state = int(7.0 * self.puntos / self.max_puntos) + 1

    def reiniciar(self):
        for rm in self.mrm.li_rm:
            rm.siElegirPartida = False
        self.puntos = self.max_puntos
        self.segundos = 0
        self.state = 0
        self.finished = False


class BMTLista:
    def __init__(self):
        self.li_bmt_uno = []
        self.dic_games = {}

    def check_color(self):
        for uno in self.li_bmt_uno:
            uno.put_color()

    def nuevo(self, bmt_uno):
        self.li_bmt_uno.append(bmt_uno)

    def __len__(self):
        return len(self.li_bmt_uno)

    def state(self, num):
        return self.li_bmt_uno[num].state

    def finished(self, num):
        return self.li_bmt_uno[num].finished

    def is_finished(self):
        for bmt in self.li_bmt_uno:
            if not bmt.finished:
                return False
        return True

    def check_game(self, cl_game, txt_game):
        if not (cl_game in self.dic_games):
            self.dic_games[cl_game] = txt_game

    def dame_uno(self, num):
        return self.li_bmt_uno[num]

    def max_puntos(self):
        mx = 0
        for bmt in self.li_bmt_uno:
            mx += bmt.max_puntos
        return mx

    def reiniciar(self):
        for bmt in self.li_bmt_uno:
            bmt.reiniciar()

    def calc_thpse(self):
        hechos = 0
        t_estado = 0
        t_segundos = 0
        total = len(self.li_bmt_uno)
        t_puntos = 0
        for uno in self.li_bmt_uno:
            if uno.finished:
                hechos += 1
                t_estado += uno.state
                t_puntos += uno.puntos
            t_segundos += uno.segundos
        return total, hechos, t_puntos, t_segundos, t_estado

    def extrae(self, from_sq, to_sq):
        nv = BMTLista()
        for x in range(from_sq, to_sq):
            uno = copy.deepcopy(self.li_bmt_uno[x])
            if uno.cl_game:
                nv.dic_games[uno.cl_game] = self.dic_games[uno.cl_game]
            uno.reiniciar()
            nv.nuevo(uno)
        return nv

    def extrae_lista(self, lni):
        nv = BMTLista()
        for num, bmt in enumerate(self.li_bmt_uno):
            if lni.siEsta(num + 1):
                uno = copy.deepcopy(bmt)
                if uno.cl_game:
                    nv.dic_games[uno.cl_game] = self.dic_games[uno.cl_game]
                uno.reiniciar()
                nv.nuevo(uno)
        return nv