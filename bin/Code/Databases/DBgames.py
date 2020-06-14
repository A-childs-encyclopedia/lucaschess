import atexit
import os
import sqlite3
import time
import random

import FasterCode
from Code.Constantes import STANDARD_TAGS, FEN_INITIAL

from Code import Game
from Code import Util
from Code.SQL import UtilSQL
import Code
from Code.Databases import DBgamesST

pos_a1 = FasterCode.pos_a1
a1_pos = FasterCode.a1_pos
pv_xpv = FasterCode.pv_xpv
xpv_pv = FasterCode.xpv_pv
xpv_pgn = FasterCode.xpv_pgn
PGNreader = FasterCode.PGNreader
set_fen = FasterCode.set_fen
make_move = FasterCode.make_move
get_fen = FasterCode.get_fen
get_exmoves = FasterCode.get_exmoves
fen_fenm2 = FasterCode.fen_fenm2
make_pv = FasterCode.make_pv
num_move = FasterCode.num_move
move_num = FasterCode.move_num

drots = {x.upper(): x for x in STANDARD_TAGS}

BODY_SAVE = b"BODY "


class DBgames:
    def __init__(self, nom_fichero):
        self.link_file = nom_fichero
        if nom_fichero.endswith(".lcdblink"):
            with open(nom_fichero, "rt") as f:
                nom_fichero = f.read().strip()
            self.external_folder = os.path.dirname(nom_fichero)
        else:
            self.external_folder = ""
        self.nom_fichero = Util.dirRelativo(nom_fichero)

        self.conexion = sqlite3.connect(self.nom_fichero)
        self.conexion.row_factory = sqlite3.Row
        self.order = None
        self.filter = None

        self.cache = {}
        self.mincache = 2024
        self.maxcache = 4048

        self.liCampos = self.lista_campos()

        self.allows_duplicates = self.recuperaConfig("ALLOWS_DUPLICATES", True)
        self.allows_positions = self.recuperaConfig("ALLOWS_POSITIONS", True)
        self.allows_complete_game = self.recuperaConfig("ALLOWS_COMPLETE_GAMES", True)
        self.allows_zero_moves = self.recuperaConfig("ALLOWS_ZERO_MOVES", True)

        self.liOrden = []

        summary_depth = self.recuperaConfig("SUMMARY_DEPTH", 0)
        self.with_db_stat = summary_depth > 0

        self.db_stat = DBgamesST.TreeSTAT(self.nom_fichero + ".st1", summary_depth)

        self.li_row_ids = []

        atexit.register(self.close)

        self.rowidReader = UtilSQL.RowidReader(self.nom_fichero, "Games")

    def remove_columns(self, lista):
        self.rowidReader.stopnow()

        cursor = self.conexion.execute("PRAGMA table_info('Games')")
        licreate = []
        lifields = []
        for row in cursor:
            num, key, tipo, nose1, nose2, nose3 = row
            if key not in lista:
                if key == "_DATA_":
                    licreate.append("_DATA_ BLOB")
                elif key == "PLYCOUNT":
                    licreate.append("PLYCOUNT INT")
                else:
                    licreate.append("'%s' VARCHAR" % key)
                lifields.append("'%s'" % key)
        sql_create = ",".join(licreate)
        sql_fields = ",".join(lifields)
        sql_select = ",".join(["Games_old.%s" % f for f in lifields])

        for sql in (
            "PRAGMA foreign_keys=off;",
            "BEGIN TRANSACTION;",
            "ALTER TABLE Games RENAME TO Games_old;",
            "CREATE TABLE Games (%s);" % sql_create,
            "INSERT INTO Games (%s) SELECT %s FROM Games_old;" % (sql_fields, sql_select),
            "DROP TABLE Games_old;",
            "CREATE INDEX XPV_INDEX ON Games (XPV);",
        ):
            self.conexion.execute(sql)
        self.conexion.commit()
        self.conexion.execute("VACUUM")

    def get_name(self):
        basename = os.path.basename(self.nom_fichero)
        p = basename.rindex(".")
        return basename[:p]

    @property
    def select(self):
        return ",".join('"%s"' % campo for campo in self.liCampos)

    def lista_campos(self):
        cursor = self.conexion.execute("pragma table_info(Games)")
        if not cursor.fetchall():
            for sql in (
                "CREATE TABLE Games(XPV VARCHAR,_DATA_ BLOB,PLYCOUNT INT);",
                "CREATE INDEX XPV_INDEX ON Games (XPV);",
                "PRAGMA page_size = 4096;",
                "PRAGMA synchronous = OFF;",
                "PRAGMA cache_size = 10000;",
                "PRAGMA journal_mode = MEMORY;",
            ):
                self.conexion.execute(sql)
            self.conexion.commit()
        cursor = self.conexion.execute("pragma table_info(Games);")
        return [row[1] for row in cursor.fetchall()]

    def reset_cache(self):
        self.cache = {}

    def guardaConfig(self, key, valor):
        with UtilSQL.DictRawSQL(self.nom_fichero, "Config") as dbconf:
            dbconf[key] = valor

    def recuperaConfig(self, key, default=None):
        with UtilSQL.DictRawSQL(self.nom_fichero, "Config") as dbconf:
            return dbconf.get(key, default)

    def addcache(self, rowid, reg):
        if len(self.cache) > self.maxcache:
            keys = self.cache.keys()
            rkeys = random.sample(keys, self.mincache)
            ncache = {}
            for k in rkeys:
                ncache[k] = self.cache[k]
            self.cache = ncache
        self.cache[rowid] = reg

    def intercambia(self, nfila, siUP):
        rowid = self.li_row_ids[nfila]
        if siUP:
            # buscamos el mayor, menor que rowid
            filOther = None
            rowidOther = -1
            for fil0, rowid0 in enumerate(self.li_row_ids):
                if rowid0 < rowid:
                    if rowid0 > rowidOther:
                        filOther = fil0
                        rowidOther = rowid0
            if filOther is None:
                return None
        else:
            # buscamos el menor, mayor que rowid
            filOther = None
            rowidOther = 999999999999
            for fil0, rowid0 in enumerate(self.li_row_ids):
                if rowid0 > rowid:
                    if rowid0 < rowidOther:
                        filOther = fil0
                        rowidOther = rowid0
            if filOther is None:
                return None
        # Hay que intercambiar rowid, con rowidOther
        selectAll = ",".join(self.liCampos)
        cursor = self.conexion.execute("SELECT %s FROM Games WHERE rowid =%d" % (selectAll, rowid))
        reg = cursor.fetchone()
        cursor = self.conexion.execute("SELECT %s FROM Games WHERE rowid =%d" % (selectAll, rowidOther))
        regOther = cursor.fetchone()

        # Problema con error por XPV unico cuando se intercambia, en RowidOther ponemos un xpv ficticio
        sql = "UPDATE Games SET XPV=? WHERE ROWID = %d" % rowidOther
        self.conexion.execute(sql, ("?????",))

        updateAll = ",".join(["%s=?" % campo for campo in self.liCampos])
        sql = "UPDATE Games SET %s" % updateAll + " WHERE ROWID = %d"

        self.conexion.execute(sql % rowid, regOther)
        self.conexion.execute(sql % rowidOther, reg)
        self.conexion.commit()

        self.addcache(rowid, regOther)
        self.addcache(rowidOther, reg)

        return filOther

    def getROWID(self, nfila):
        return self.li_row_ids[nfila]

    def field(self, nfila, name):
        rowid = self.li_row_ids[nfila]
        if not (rowid in self.cache):
            cursor = self.conexion.execute("SELECT %s FROM Games WHERE rowid =%d" % (self.select, rowid))
            reg = cursor.fetchone()
            self.addcache(rowid, reg)
        try:
            return self.cache[rowid][name]
        except:
            return ""

    def siFaltanRegistrosPorLeer(self):
        if not self.rowidReader:
            return False
        return not self.rowidReader.terminado()

    def filterPV(self, pv, condicionAdicional=None):
        condicion = ""
        if type(pv) == list:  # transpositions
            if pv:
                li = []
                for unpv in pv:
                    xpv = pv_xpv(unpv)
                    li.append('XPV GLOB "%s*"' % xpv)
                condicion = "(%s)" % (" OR ".join(li),)
        elif pv:
            xpv = pv_xpv(pv)
            condicion = 'XPV GLOB "%s*"' % xpv if xpv else ""
        if condicionAdicional:
            if condicion:
                condicion += " AND (%s)" % condicionAdicional
            else:
                condicion = condicionAdicional
        self.filter = condicion

        self.li_row_ids = []
        self.rowidReader.run(self.li_row_ids, condicion, self.order)

    def reccount(self):
        if not self.rowidReader:
            return 0
        n = self.rowidReader.reccount()
        # Si es cero y no ha terminado de leer, se le da vtime para que devuelva algo
        while n == 0 and not self.rowidReader.terminado():
            time.sleep(0.05)
            n = self.rowidReader.reccount()
        return n

    def all_reccount(self):
        self.li_row_ids = []
        self.rowidReader.run(self.li_row_ids, None, None)
        while not self.rowidReader.terminado():
            time.sleep(0.1)
        return self.reccount()

    def __len__(self):
        sql = "SELECT Count(*) FROM Games"
        cursor = self.conexion.execute(sql)
        return cursor.fetchone()[0]

    def close(self):
        if self.conexion:
            self.conexion.close()
            self.conexion = None
        if self.db_stat:
            self.db_stat.close()
            self.db_stat = None
        if self.rowidReader:
            self.rowidReader.stopnow()
            self.rowidReader = None

    def rotulo(self):
        return Util.path_rel(self.nom_fichero)

    def depthStat(self):
        return self.db_stat.depth if self.db_stat else 0

    def read_xpv(self, xpv):
        if xpv.startswith("|"):
            nada, fen, xpv = xpv.split("|")
        else:
            fen = ""
        pv = xpv_pv(xpv) if xpv else ""
        return fen, pv

    def damePV(self, fila):
        xpv = self.field(fila, "XPV")
        return self.read_xpv(xpv)

    def ponOrden(self, liOrden):
        li = []
        for campo, tipo in liOrden:
            li.append("%s %s" % (campo, tipo))
        self.order = ",".join(li)
        self.li_row_ids = []
        self.rowidReader.run(self.li_row_ids, self.filter, self.order)
        self.liOrden = liOrden

    def dameOrden(self):
        return self.liOrden

    def borrarLista(self, lista_recnos):
        cSQL = "DELETE FROM Games WHERE rowid = ?"
        lista_recnos.sort(reverse=True)
        for recno in lista_recnos:
            fen, pv = self.damePV(recno)
            result = self.field(recno, "RESULT")
            if not fen and self.with_db_stat:
                self.db_stat.append(pv, result, -1)
            self.conexion.execute(cSQL, (self.li_row_ids[recno],))
            del self.li_row_ids[recno]
        if self.with_db_stat:
            self.db_stat.commit()
        self.conexion.commit()

    def get_summary(self, pvBase, dicAnalisis, si_figurines_pgn, allmoves=True):
        return self.db_stat.get_summary(pvBase, dicAnalisis, si_figurines_pgn, allmoves)

    def rebuild_stat(self, dispatch, depth):
        self.guardaConfig("SUMMARY_DEPTH", depth)
        self.db_stat.depth = depth
        self.db_stat.reset()
        if self.filter:
            self.filterPV("")
        while self.siFaltanRegistrosPorLeer():
            time.sleep(0.1)
            dispatch(0, self.reccount())
        reccount = self.reccount()
        if reccount:
            cursor = self.conexion.execute("SELECT XPV, RESULT FROM Games")
            recno = 0
            self.db_stat.massive_append_set(True)
            while dispatch(recno, reccount):
                chunk = random.randint(60000, 100000)
                li = cursor.fetchmany(chunk)
                if li:
                    for pos, (XPV, RESULT) in enumerate(li):
                        pv = xpv_pv(XPV)
                        self.db_stat.append(pv, RESULT)
                        if (pos % (chunk // 20)) == 0:
                            if not dispatch(recno + pos, reccount):
                                break
                    nli = len(li)
                    if nli < chunk:
                        break
                    recno += nli
                    self.db_stat.commit()
                else:
                    break
            self.db_stat.massive_append_set(False)
            self.db_stat.commit()

    def leeAllRecno(self, recno):
        rowid = self.li_row_ids[recno]
        cursor = self.conexion.execute("SELECT %s FROM Games WHERE rowid =%d" % (self.select, rowid))
        return cursor.fetchone()

    def leeRegAllRecno(self, recno):
        raw = self.leeAllRecno(recno)
        alm = Util.Record()
        for campo in self.liCampos:
            setattr(alm, campo, raw[campo])
        return alm, raw

    def leeDicAllRecno(self, recno):
        raw = self.leeAllRecno(recno)
        dic = {}
        for campo in self.liCampos:
            dic[campo] = raw[campo]
        return dic

    def countData(self, filtro):
        sql = "SELECT COUNT(*) FROM Games"
        if self.filter:
            sql += " WHERE %s" % self.filter
            if filtro:
                sql += " AND %s" % filtro
        else:
            if filtro:
                sql += " WHERE %s" % filtro

        cursor = self.conexion.execute(sql)
        return cursor.fetchone()[0]

    def yieldData(self, liFields, filtro):
        select = ",".join(liFields)
        sql = "SELECT %s FROM Games" % (select,)
        if self.filter:
            sql += " WHERE %s" % self.filter
            if filtro:
                sql += " AND %s" % filtro
        else:
            if filtro:
                sql += " WHERE %s" % filtro

        cursor = self.conexion.execute(sql)
        while True:
            raw = cursor.fetchone()
            if raw:
                alm = Util.Record()
                for campo in liFields:
                    setattr(alm, campo, raw[campo])
                yield alm
            else:
                return

    def yield_polyglot(self):
        select = "XPV"
        si_result = "RESULT" in self.liCampos
        if si_result:
            select += ",RESULT"
        sql = "SELECT %s FROM Games" % (select,)

        if self.filter:
            sql += " WHERE %s" % self.filter

        cursor = self.conexion.execute(sql)
        while True:
            li_rows = cursor.fetchmany(10_000)
            if li_rows:
                for row in li_rows:
                    if si_result:
                        yield row
                    else:
                        yield row[0], "*"
            else:
                return

    def players(self):
        sql = "SELECT DISTINCT WHITE FROM Games"
        cursor = self.conexion.execute(sql)
        listaw = [raw[0] for raw in cursor.fetchall()]

        sql = "SELECT DISTINCT BLACK FROM Games"
        cursor = self.conexion.execute(sql)
        listab = [raw[0] for raw in cursor.fetchall()]

        listaw.extend(listab)

        lista = list(set(listaw))
        lista.sort()
        return lista

    def leePartidaRecno(self, recno):
        raw = self.leeAllRecno(recno)
        return self.leePartidaRaw(raw)

    def leePartidaRaw(self, raw):
        p = Game.Game()
        xpgn = raw["_DATA_"]
        ok = False
        if xpgn:
            if xpgn.startswith(BODY_SAVE):
                ok, p = Game.pgn_game(xpgn[len(BODY_SAVE):].strip())
            else:
                try:
                    p.restore(xpgn)
                    ok = True
                except:
                    ok = False

        if not ok:
            fen, pv = self.read_xpv(raw["XPV"])
            if fen:
                p.set_fen(fen)
            p.read_pv(pv)

        litags = []
        for field in self.liCampos:
            if not (field in ("XPV", "_DATA_", "PLYCOUNT")):
                v = raw[field]
                if v:
                    litags.append((drots.get(field, field), v if type(v) == str else str(v)))
        litags.append(("PlyCount", str(raw["PLYCOUNT"])))

        p.set_tags(litags)
        p.assign_opening()
        return p

    def leePGNRecno(self, recno, sp):
        raw = self.leeAllRecno(recno)
        litags = []
        result = "*"
        for field in self.liCampos:
            if not (field in ("XPV", "_DATA_", "PLYCOUNT")):
                v = raw[field]
                if v:
                    litags.append((drots.get(field, field), v if type(v) == str else str(v)))
                    if field == "RESULT":
                        result = v if type(v) == str else str(v)

        litags.append(("PlyCount", str(raw["PLYCOUNT"])))
        xpgn = raw["_DATA_"]
        if xpgn:
            if xpgn.startswith(BODY_SAVE):
                ok, p = Game.pgn_game(xpgn[len(BODY_SAVE):].strip())
            else:
                p = Game.Game()
                p.restore(xpgn)
            p.set_tags(litags)
            return p.pgn(), p.resultado()

        pgn = xpv_pgn(raw["XPV"])
        if sp == "\r\n":
            pgn = pgn.replace("\n", "\r\n")
        tags = []
        for t, v in litags:
            tags.append('[%s "%s"]' % (t, v))
        pgn = sp.join(tags) + sp + sp + pgn
        return pgn, result

    def blankPartida(self):
        hoy = Util.today()
        liTags = [["Date", "%d.%02d.%02d" % (hoy.year, hoy.month, hoy.day)]]
        return Game.Game(li_tags=liTags)

    def guardaPartidaRecno(self, recno, game):
        return self.inserta(game) if recno is None else self.modifica(recno, game)

    def fill(self, li_field_value):
        lset = ",".join(field + "=?" for field, value in li_field_value)
        sql = "UPDATE Games SET " + lset
        if self.filter:
            sql += " WHERE %s" % self.filter
        self.conexion.execute(sql, [value for field, value in li_field_value])
        self.conexion.commit()

    def pack(self):
        self.conexion.execute("VACUUM")
        if self.with_db_stat:
            self.db_stat._conexion.execute("VACUUM")

    def insert_lcsb(self, path_lcsb):
        dic = Util.restore_pickle(path_lcsb)
        game = Game.Game()
        game.restore(dic)
        return self.inserta(game)

    def li_tags(self):
        return [tag for tag in self.liCampos if not (tag in ("XPV", "_DATA_"))]

    def add_column(self, column: str):
        column = column.upper()
        sql = "ALTER TABLE Games ADD COLUMN '%s' VARCHAR;" % column
        self.conexion.execute(sql)
        self.conexion.commit()
        self.liCampos.append(column)

    def leerPGNs(self, ficheros, dlTmp):
        erroneos = duplicados = importados = 0

        allows_fen = self.allows_positions
        allows_complete_game = self.allows_complete_game
        allows_cero_moves = self.allows_zero_moves
        duplicate_check = not self.allows_duplicates

        t1 = time.time() - 0.7  # para que empiece enseguida

        if self.with_db_stat:
            self.db_stat.massive_append_set(True)

        def write_logs(fich, pgn):
            with open(fich, "at", encoding="utf-8", errors="ignore") as ferr:
                ferr.write(pgn)
                ferr.write("\n")

        si_cols_cambiados = False
        select = ",".join('"%s"' % campo for campo in self.liCampos)
        select_values = ("?," * len(self.liCampos))[:-1]
        sql = "INSERT INTO Games (%s) VALUES (%s);" % (select, select_values)

        st_xpv_bloque = set()

        li_regs = []
        n_regs = 0

        conexion = self.conexion

        dcabs = self.recuperaConfig("dcabs", drots.copy())

        obj_decode = Util.Decode()
        decode = obj_decode.decode

        for fichero in ficheros:
            nomfichero = os.path.basename(fichero)
            fich_erroneos = os.path.join(Code.configuracion.carpetaTemporal(), nomfichero[:-3] + "errors.pgn")
            fich_duplicados = os.path.join(Code.configuracion.carpetaTemporal(), nomfichero[:-3] + "duplicates.pgn")
            dlTmp.pon_titulo(nomfichero)
            next_n = random.randint(1000, 2000)

            obj_decode.read_file(fichero)

            with PGNreader(fichero, self.depthStat()) as fpgn:
                bsize = fpgn.size
                for n, (body, is_raw, pv, fens, bdCab, bdCablwr, btell) in enumerate(fpgn, 1):
                    if n == next_n:
                        if time.time() - t1 > 0.8:
                            if not dlTmp.actualiza(
                                erroneos + duplicados + importados,
                                erroneos,
                                duplicados,
                                importados,
                                btell * 100.0 / bsize,
                            ):
                                break
                            t1 = time.time()
                        next_n = n + random.randint(1000, 2000)

                    # Sin movimientos
                    if not pv and not allows_cero_moves:
                        erroneos += 1
                        write_logs(fich_erroneos, decode(fpgn.bpgn()))
                        continue

                    dCab = {decode(k): decode(v) for k, v in bdCab.items()}
                    dCablwr = {decode(k): decode(v) for k, v in bdCablwr.items()}
                    dcabs.update(dCablwr)

                    xpv = pv_xpv(pv)

                    fen = dCab.get("FEN", None)
                    if fen:
                        if fen == FEN_INITIAL:
                            del dCab["FEN"]
                            del dCablwr["fen"]
                            fen = None
                        else:
                            if not allows_fen:
                                erroneos += 1
                                write_logs(fich_erroneos, decode(fpgn.bpgn()))
                                continue
                            xpv = "|%s|%s" % (fen, xpv)

                    if not fen:
                        if not allows_complete_game:
                            erroneos += 1
                            write_logs(fich_erroneos, decode(fpgn.bpgn()))
                            continue
                        fen = None  # por si hay alguno vacio

                    if duplicate_check:
                        # Duplicados en el bloque actual
                        if xpv in st_xpv_bloque:
                            ok = False

                        # Duplicados respecto a las grabadas ya
                        else:
                            cursor = conexion.execute("SELECT COUNT(*) FROM games WHERE XPV = ?", (xpv,))
                            ok = cursor.fetchone()[0] == 0

                        if not ok:
                            duplicados += 1
                            write_logs(fich_duplicados, decode(fpgn.bpgn()))
                            continue

                    st_xpv_bloque.add(xpv)

                    for k in dCab:
                        if not (k in self.liCampos):

                            # Grabamos lo que hay
                            if li_regs:
                                n_regs = 0
                                conexion.executemany(sql, li_regs)
                                li_regs = []
                                st_xpv_bloque = set()
                                conexion.commit()
                                if self.with_db_stat:
                                    self.db_stat.massive_append_set(False)
                                    self.db_stat.commit()
                                    self.db_stat.massive_append_set(True)

                            self.add_column(k)
                            si_cols_cambiados = True
                            select_values = ("?," * len(self.liCampos))[:-1]
                            sql = "insert into Games (%s) values (%s);" % (self.select, select_values)

                    reg = []
                    result = "*"
                    for campo in self.liCampos:
                        if campo == "XPV":
                            reg.append(xpv)
                        elif campo == "_DATA_":
                            data = None
                            if not is_raw:
                                data = memoryview(BODY_SAVE + body)
                            reg.append(data)
                        elif campo == "PLYCOUNT":
                            reg.append(pv.count(" ") + 1)
                        else:
                            reg.append(dCab.get(campo))
                            if campo == "RESULT":
                                result = dCab.get(campo, "*")

                    if self.with_db_stat and fen is None and pv:
                        self.db_stat.append(pv, result)

                    li_regs.append(reg)
                    n_regs += 1
                    importados += 1
                    if n_regs == 20000:
                        n_regs = 0
                        conexion.executemany(sql, li_regs)
                        li_regs = []
                        st_xpv_bloque = set()
                        conexion.commit()
                        if self.with_db_stat:
                            self.db_stat.commit()

        dlTmp.actualiza(erroneos + duplicados + importados, erroneos, duplicados, importados, 100.00)
        dlTmp.ponSaving()

        if li_regs:
            conexion.executemany(sql, li_regs)
            conexion.commit()

        if self.with_db_stat:
            self.db_stat.massive_append_set(False)
            self.db_stat.commit()
        conexion.commit()
        dlTmp.ponContinuar()

        self.guardaConfig("dcabs", dcabs)

        return si_cols_cambiados

    def appendDB(self, db, liRecnos, dlTmp):
        erroneos = duplicados = importados = 0

        xtime = time.time()

        allows_fen = self.allows_positions
        allows_complete_game = self.allows_complete_game
        allows_cero_moves = self.allows_zero_moves
        duplicate_check = not self.allows_duplicates

        t1 = time.time() - 0.7  # para que empiece enseguida

        if self.with_db_stat:
            self.db_stat.massive_append_set(True)

        si_cols_cambiados = False
        for campo in db.liCampos:
            if campo not in self.liCampos:
                self.add_column(campo)
                si_cols_cambiados = True

        select = db.select
        select_values = ("?," * len(db.liCampos))[:-1]
        sql = "INSERT INTO Games (%s) VALUES (%s);" % (select, select_values)

        pos_result = db.liCampos.index("RESULT") if "RESULT" in db.liCampos else None

        st_xpv_bloque = set()

        liRegs = []
        nRegs = 0

        conexion = self.conexion

        next_n = random.randint(1000, 2000)

        bsize = len(liRecnos)
        for btell, recno in enumerate(liRecnos):
            if btell == next_n:
                if time.time() - t1 > 0.9:
                    if not dlTmp.actualiza(
                        erroneos + duplicados + importados, erroneos, duplicados, importados, btell * 100.0 / bsize
                    ):
                        break
                    t1 = time.time()
                next_n = btell + random.randint(1000, 2000)

            row = db.leeAllRecno(recno)

            xpv = row[0]

            si_fen = "|" in xpv
            if si_fen:
                if not allows_fen:
                    erroneos += 1
                    continue
                nada, fen, xpv = xpv.split("|")
            else:
                if not allows_complete_game:
                    erroneos += 1
                    continue

            if not xpv:
                if not allows_cero_moves:
                    erroneos += 1
                    continue

            if duplicate_check:
                if row[0] in st_xpv_bloque:
                    ok = False
                else:
                    cursor = conexion.execute(
                        "SELECT COUNT(*) FROM games WHERE XPV = ?", (row[0],)
                    )  # No vale la variable xpv, que se ha cambiado
                    ok = cursor.fetchone()[0] == 0
                if not ok:
                    duplicados += 1
                    continue
                st_xpv_bloque.add(row[0])

            if self.with_db_stat and not si_fen and xpv and pos_result is not None:
                pv = xpv_pv(xpv)
                result = row[pos_result]
                self.db_stat.append(pv, result)

            liRegs.append(row)
            nRegs += 1
            importados += 1
            if nRegs == 10000:
                nRegs = 0
                conexion.executemany(sql, liRegs)
                liRegs = []
                st_xpv_bloque = set()
                conexion.commit()
                if self.with_db_stat:
                    self.db_stat.commit()

        dlTmp.actualiza(erroneos + duplicados + importados, erroneos, duplicados, importados, 100.00)
        dlTmp.ponSaving()
        if liRegs:
            conexion.executemany(sql, liRegs)
        if self.with_db_stat:
            self.db_stat.massive_append_set(False)
            self.db_stat.commit()
        conexion.commit()
        dlTmp.ponContinuar()
        return si_cols_cambiados

    def check_partida(self, game):
        si_completa = game.siFenInicial()

        if not self.allows_positions:
            if not si_completa:
                return _("This database does not allow games that are not complete.")

        if not self.allows_complete_game:
            if si_completa:
                return _("This database only allows positions.")

        if not self.allows_zero_moves:
            if len(game) == 0:
                return _("This database does not allows games without moves.")

        return None

    def modifica(self, recno, partida_modificada):
        resp = Util.Record()
        resp.ok = True
        resp.changed = False
        resp.summary_changed = False
        resp.mens_error = None
        resp.inserted = False

        mens_error = self.check_partida(partida_modificada)
        if mens_error:
            resp.ok = False
            resp.mens_error = mens_error
            return resp

        partida_antigua = self.leePartidaRecno(recno)
        #
        # # La game antigua y la nueva son iguales ? no se hace nada.
        # if partida_antigua == partida_modificada:  # game.__eq__
        #     return resp

        # Test si hay nuevos tags
        for tag, valor in partida_modificada.li_tags:
            if not (tag.upper() in self.liCampos):
                self.add_column(tag)

        # Modificamos datos antiguos
        li_data = []
        for campo in self.liCampos:
            if campo == "XPV":
                dato = partida_modificada.xpv()
            elif campo == "_DATA_":
                dato = None if partida_modificada.only_has_moves() else partida_modificada.save(False)
            elif campo == "PLYCOUNT":
                dato = len(partida_modificada)
            else:
                dato = partida_modificada.get_tag(campo)
            li_data.append(dato)

        resp.changed = True

        fields = ",".join(["%s=?" % field for field in self.liCampos])
        rowid = self.li_row_ids[recno]
        sql = "UPDATE Games SET %s WHERE ROWID = %d" % (fields, rowid)
        self.conexion.execute(sql, li_data)
        self.conexion.commit()

        # Summary
        if self.with_db_stat:
            if partida_antigua.get_tag("FEN") is None:
                pv = partida_antigua.pv()
                if pv:
                    self.db_stat.append(pv, partida_antigua.resultado(), r=-1)
            if partida_modificada.get_tag("FEN") is None:
                pv = partida_modificada.pv()
                if pv:
                    self.db_stat.append(pv, partida_modificada.resultado(), r=+1)
            resp.summary_changed = True

        del self.cache[rowid]

        return resp

    def inserta(self, partida_nueva):
        resp = Util.Record()
        resp.ok = True
        resp.changed = False
        resp.summary_changed = False
        resp.inserted = True
        resp.mens_error = self.check_partida(partida_nueva)
        if resp.mens_error:
            resp.ok = False
            return resp

        # Test si hay nuevos tags
        for tag, valor in partida_nueva.li_tags:
            if not (tag.upper() in self.liCampos):
                self.add_column(tag)

        li_fields = []
        li_data = []

        data_nue = None if partida_nueva.only_has_moves() else partida_nueva.save()
        li_fields.append("_DATA_")
        li_data.append(data_nue)

        pv_nue = partida_nueva.pv()
        xpv_nue = pv_xpv(pv_nue)
        si_fen_nue = not partida_nueva.siFenInicial()
        if si_fen_nue:
            fen_nue = partida_nueva.first_position.fen()
            xpv_nue = "|%s|%s" % (fen_nue, xpv_nue)
        if not self.allows_duplicates:
            sql = "SELECT COUNT(*) FROM Games WHERE XPV = ?"
            cursor = self.conexion.execute(sql, (xpv_nue,))
            row = cursor.fetchone()
            if row[0] > 0:
                resp.ok = False
                resp.mens_error = _("This game is duplicated")
                return resp
        li_fields.append("XPV")
        li_data.append(xpv_nue)
        li_fields.append("PLYCOUNT")
        li_data.append(partida_nueva.num_moves())

        result_nue = "*"
        for tag, valor_nue in partida_nueva.li_tags:
            tag = tag.upper()
            if tag != "PLYCOUNT":
                li_fields.append(tag)
                li_data.append(valor_nue)
            if tag == "RESULT":
                result_nue = valor_nue

        fields = ",".join(li_fields)
        values = ",".join(["?"] * len(li_fields))
        sql = "INSERT INTO Games (%s) VALUES (%s)" % (fields, values)
        cursor = self.conexion.cursor()
        cursor.execute(sql, li_data)
        self.conexion.commit()
        self.li_row_ids.append(cursor.lastrowid)
        cursor.close()

        if self.with_db_stat and not si_fen_nue and pv_nue:
            self.db_stat.append(pv_nue, result_nue, +1)
            self.db_stat.commit()
            resp.summary_changed = True

        resp.changed = True

        return resp

    def has_positions(self):
        return "FEN" in self.liCampos


def get_random_game():
    db = DBgames(Code.path_resource("IntFiles", "last_games.lcdb"))
    recno = random.randint(0, db.all_reccount() - 1)
    game = db.leePartidaRecno(recno)
    db.close()
    return game
