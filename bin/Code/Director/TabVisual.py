import copy
import time

from Code.Board import BoardTypes
from Code.Config import TrListas
from Code import Util
from Code.SQL import UtilSQL
import Code


class PFlecha(BoardTypes.Flecha):
    def __init__(self):
        BoardTypes.Flecha.__init__(self)
        self.name = ""
        self.id = None


class PMarco(BoardTypes.Marco):
    def __init__(self):
        BoardTypes.Marco.__init__(self)
        self.name = ""
        self.id = None


class PSVG(BoardTypes.SVG):
    def __init__(self):
        BoardTypes.SVG.__init__(self)
        self.name = ""
        self.id = None


class PMarker(BoardTypes.Marker):
    def __init__(self):
        BoardTypes.Marker.__init__(self)
        self.name = ""
        self.id = None


TP_FLECHA, TP_MARCO, TP_TEXTO, TP_SVG, TP_MARKER, TP_PIEZACREA, TP_PIEZAMUEVE, TP_PIEZABORRA, TP_ACTION, TP_CONFIGURATION = (
    "F",
    "M",
    "T",
    "S",
    "X",
    "PC",
    "PM",
    "PB",
    "A",
    "C",
)


class GTarea:
    def __init__(self, guion, tp):
        self.guion = guion
        self._id = Util.str_id()
        self._tp = tp
        self._marcado = False
        self._orden = 0
        self._nombre = None
        self._registro = None
        self.xmarcadoOwner = False

    def id(self):
        return self._id

    def tp(self):
        return self._tp

    def marcado(self, si=None):
        if si is not None:
            self._marcado = bool(si)
        return self._marcado

    def marcadoOwner(self, si=None):
        if si is not None:
            self.xmarcadoOwner = bool(si)
        return self.xmarcadoOwner

    def name(self, name=None):
        if name is not None:
            self._nombre = name
        return self._nombre if self._nombre else ""

    def registro(self, valores=None):
        if valores:
            self._registro = valores
        return self._registro

    def guarda(self):
        reg = {}
        for atr in dir(self):
            if atr.startswith("_") and not atr.startswith("__"):
                if atr == "_itemSC":
                    reg["_bloqueDatos"] = self._itemSC.bloqueDatos
                else:
                    valor = getattr(self, atr)
                    reg[atr] = valor
        return reg

    def recupera(self, reg):
        for atr in reg:
            if atr.startswith("_") and not atr.startswith("__") and atr != "_id":
                valor = reg[atr]
                setattr(self, atr, valor)


class GT_Item(GTarea):
    def __init__(self, guion, tp):
        GTarea.__init__(self, guion, tp)
        self._itemSC = None
        self._bloqueDatos = None
        self.xitemSCOwner = None

    def itemSC(self, sc=None):
        if sc is not None:
            self._itemSC = sc
        return self._itemSC

    def borraItemSCOwner(self):
        self.xitemSCOwner = None
        self.marcadoOwner(False)

    def itemSCOwner(self, sc=None):
        if sc is not None:
            self.xitemSCOwner = sc
        return self.xitemSCOwner

    def a1h8(self):
        bd = self._itemSC.bloqueDatos
        return bd.a1h8

    def bloqueDatos(self):
        return self._itemSC.bloqueDatos

    def name(self, name=None):
        if name is not None:
            self._nombre = name
        if self._nombre:
            return self._nombre
        return self._nombre if self._nombre else getattr(self._itemSC.bloqueDatos, "name", "")

    def coordina(self):
        if self.xitemSCOwner:
            if self.tp() == "S":
                self.xitemSCOwner.coordinaPosicionOtro(self._itemSC)
                self.xitemSCOwner.update()
            else:
                bf = copy.deepcopy(self._itemSC.bloqueDatos)
                bf.width_square = self.xitemSCOwner.bloqueDatos.width_square
                self.xitemSCOwner.bloqueDatos = bf
                self.xitemSCOwner.reset()
            self.xitemSCOwner.escena.update()


class GT_Texto(GTarea):
    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_TEXTO)
        self._texto = None
        self._continuar = None

    def texto(self, txt=None):
        if txt is not None:
            self._texto = txt
        return self._texto

    def continuar(self, ok=None):
        if ok is not None:
            self._continuar = ok
        return self._continuar

    def info(self):
        mas_texto = "? " if self._continuar else ""
        if not self._texto:
            return mas_texto
        if "</head>" in self._texto:
            li = self._texto.split("</head>")[1].split("<")
            for n in range(len(li)):
                li1 = li[n].split(">")
                if len(li1) == 2:
                    li[n] = li1[1]
            return mas_texto + "".join(li)
        else:
            return mas_texto + self._texto

    def txt_tipo(self):
        return _("Text")

    def run(self):
        self.guion.writePizarra(self)


class GT_Flecha(GT_Item):
    def __init__(self, guion):
        GT_Item.__init__(self, guion, TP_FLECHA)

    def txt_tipo(self):
        return _("Arrow")

    def info(self):
        bd = self._itemSC.bloqueDatos
        return bd.a1h8

    def run(self):
        sc = self.guion.board.creaFlecha(self._bloqueDatos)
        sc.ponRutinaPulsada(None, self.id())
        self.itemSC(sc)
        self.marcado(True)
        if self._itemSC:
            self._itemSC.show()


class GT_Marco(GT_Item):
    def __init__(self, guion):
        GT_Item.__init__(self, guion, TP_MARCO)

    def txt_tipo(self):
        return _("Box")

    def info(self):
        bd = self._itemSC.bloqueDatos
        return bd.a1h8

    def run(self):
        if self._itemSC:
            self._itemSC.show()

        sc = self.guion.board.creaMarco(self._bloqueDatos)
        sc.ponRutinaPulsada(None, self.id())
        self.itemSC(sc)
        self.marcado(True)


class GT_SVG(GT_Item):
    def __init__(self, guion):
        GT_Item.__init__(self, guion, TP_SVG)

    def txt_tipo(self):
        return _("Image")

    def info(self):
        return "(%.02f,%.02f)-(%.02f,%.02f)" % self.get_datos()

    def get_datos(self):
        bd = self._itemSC.bloqueDatos
        p = bd.physical_pos

        def f(n):
            return float(n * 1.0 / bd.width_square)

        return (f(p.x), f(p.y), f(p.ancho), f(p.alto))

    def set_datos(self, col, fil, ancho, alto):
        bd = self._itemSC.bloqueDatos
        p = bd.physical_pos

        def f(n):
            return float(n * bd.width_square)

        p.x = f(col)
        p.y = f(fil)
        p.ancho = f(ancho)
        p.alto = f(alto)

    def run(self):
        if self._itemSC:
            self._itemSC.show()

        siEditando = self.guion.siEditando()

        sc = self.guion.board.creaSVG(self._bloqueDatos, siEditando=siEditando)
        sc.ponRutinaPulsada(None, self.id())
        sc.bloqueDatos = self._bloqueDatos  # necesario para svg con physical_pos no ajustado a squares
        sc.update()
        self.itemSC(sc)
        self.marcado(True)


class GT_Marker(GT_Item):
    def __init__(self, guion):
        GT_Item.__init__(self, guion, TP_MARKER)

    def txt_tipo(self):
        return _("Marker")

    def info(self):
        bd = self._itemSC.bloqueDatos
        return bd.a1h8

    def run(self):
        if self._itemSC:
            self._itemSC.show()

        siEditando = self.guion.siEditando()
        sc = self.guion.board.creaMarker(self._bloqueDatos, siEditando=siEditando)
        self.itemSC(sc)
        self.marcado(True)


class GT_Action(GTarea):
    def __init__(self, guion):
        self.GTA_INICIO, self.GTA_MAINARROW_REMOVE, self.GTA_PIECES_REMOVEALL, self.GTA_GRAPHICS_REMOVEALL, self.GTA_PIZARRA_REMOVE = (
            "I",
            "MAR",
            "PRA",
            "GRA",
            "PR",
        )
        self.dicTxt = {
            self.GTA_INICIO: _("Initial physical pos"),
            self.GTA_MAINARROW_REMOVE: _("Remove main arrow"),
            self.GTA_PIECES_REMOVEALL: _("Remove all pieces"),
            self.GTA_GRAPHICS_REMOVEALL: _("Remove all graphics"),
            self.GTA_PIZARRA_REMOVE: _("Remove text"),
        }

        GTarea.__init__(self, guion, TP_ACTION)
        self._action = None

    def action(self, action=None):
        if action:
            self._action = action
        return self._action

    def txt_tipo(self):
        return _("Action")

    def info(self):
        return self.dicTxt[self._action] if self._action else "?"

    def run(self):
        guion = self.guion
        board = guion.board
        if self._action == self.GTA_INICIO:
            guion.restoreBoard()
        elif self._action == self.GTA_MAINARROW_REMOVE:
            if board.flechaSC:
                board.flechaSC.hide()
        elif self._action == self.GTA_PIECES_REMOVEALL:
            board.removePieces()
        elif self._action == self.GTA_GRAPHICS_REMOVEALL:
            board.borraMovibles()
        elif self._action == self.GTA_PIZARRA_REMOVE:
            guion.cierraPizarra()


class GT_Configuration(GTarea):
    GTC_TRANSITION, GTC_NEXT_TRANSITION = "T", "NT"
    dicTxt = {GTC_TRANSITION: "General transition time", GTC_NEXT_TRANSITION: "Next transition time"}

    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_CONFIGURATION)
        self._configuration = None
        self._value = 0

    def configuration(self, configuration=None):
        if configuration:
            self._configuration = configuration
        return self._configuration

    def value(self, value=None):
        if type(value) == int:
            self._value = value
        return self._value

    def txt_tipo(self):
        return _("Configuration")

    def info(self):
        return "%d=%s" % (self._value, self.dicTxt[self._configuration] if self._configuration else "?")

    def run(self):
        guion = self.guion
        if self._configuration == self.GTC_TRANSITION:
            guion.transition = self._value
        elif self._configuration == self.GTC_NEXT_TRANSITION:
            guion.nextTransition = self._value


class GT_PiezaMueve(GTarea):
    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_PIEZAMUEVE)
        self._desde = None
        self._hasta = None
        self._borra = None

    def setPosicion(self, physical_pos):
        self._posicion = physical_pos

    def physical_pos(self):
        return self._posicion

    def desdeHastaBorra(self, from_sq=None, to_sq=None, pieza_borra=None):
        if from_sq is not None:
            self._desde = from_sq
            self._hasta = to_sq
            self._borra = pieza_borra
        return self._desde, self._hasta, self._borra

    def txt_tipo(self):
        return _("Move piece")

    def info(self):
        return self._desde + " -> " + self._hasta


class GT_PiezaCrea(GTarea):
    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_PIEZACREA)
        self._pieza = None
        self._desde = None
        self._borra = None

    def from_sq(self, from_sq=None, borra=None):
        if from_sq is not None:
            self._desde = from_sq
            self._borra = borra
        return self._desde, self._borra

    def pieza(self, pz=None):
        if pz is not None:
            self._pieza = pz
        return self._pieza

    def txt_tipo(self):
        return _("Create piece")

    def info(self):
        pz = TrListas.letterPiece(self._pieza)
        return (pz if pz.isupper() else pz.lower()) + " -> " + self._desde


class GT_PiezaBorra(GTarea):
    def __init__(self, guion):
        GTarea.__init__(self, guion, TP_PIEZABORRA)
        self._pieza = None
        self._desde = None

    def from_sq(self, from_sq=None):
        if from_sq is not None:
            self._desde = from_sq
        return self._desde

    def pieza(self, pz=None):
        if pz is not None:
            self._pieza = pz
        return self._pieza

    def txt_tipo(self):
        return _("Delete piece")

    def info(self):
        pz = TrListas.letterPiece(self._pieza)
        return (pz if pz.isupper() else pz.lower()) + " -> " + self._desde


class Guion:
    def __init__(self, board, winDirector=None):
        self.liGTareas = []
        self.pizarra = None
        self.anchoPizarra = 250
        self.posPizarra = "R"
        self.board = board
        self.winDirector = winDirector
        self.saveBoard()
        self.cerrado = False

    def siEditando(self):
        return self.winDirector is not None

    def saveBoard(self):
        self.board_last_position = self.board.last_position
        self.board_is_white_bottom = self.board.is_white_bottom
        if self.board.flechaSC and self.board.flechaSC.isVisible():
            a1h8 = self.board.flechaSC.bloqueDatos.a1h8
            self.board_flechaSC = a1h8[:2], a1h8[2:]
        else:
            self.board_flechaSC = None

        if self.winDirector:
            if not hasattr(self, "board_mensajero") or self.board_mensajero != self.winDirector.muevePieza:
                self.board_mensajero = self.board.mensajero
                self.board.mensajero = self.winDirector.muevePieza

        self.board_activasPiezas = self.board.pieces_are_active, self.board.side_pieces_active

    def restoreBoard(self):
        self.board.dirvisual = None
        self.board.set_position(self.board_last_position, siBorraMoviblesAhora=False)
        if self.board_flechaSC:
            from_sq, to_sq = self.board_flechaSC
            self.board.put_arrow_sc(from_sq, to_sq)
        if self.winDirector:
            self.board.mensajero = self.board_mensajero
        if self.board_activasPiezas[0]:
            self.board.activate_side(self.board_activasPiezas[1])
        self.board.siDirector = True
        self.cierraPizarra()

    def nuevaTarea(self, tarea, row=-1):
        if row == -1:
            self.liGTareas.append(tarea)
            row = len(self.liGTareas) - 1
        else:
            self.liGTareas.insert(row, tarea)
        return row

    def savedPizarra(self):
        self.winDirector.refresh_guion()
        self.winDirector.ponSiGrabar()

    def writePizarra(self, tarea):
        if self.pizarra is None:
            self.pizarra = BoardTypes.Pizarra(
                self, self.board, self.anchoPizarra, edit_mode=self.winDirector is not None, with_continue=tarea.continuar()
            )
            self.pizarra.mensaje.setFocus()
        self.pizarra.write(tarea)
        self.pizarra.show()

    def cierraPizarra(self):
        if self.pizarra:
            self.pizarra.close()
            self.pizarra = None

    def borrarPizarraActiva(self):
        if self.winDirector:
            self.winDirector.borrarPizarraActiva()
        else:
            self.cierraPizarra()

    def nuevaCopia(self, ntarea):
        tarea = copy.copy(self.tarea(ntarea))
        tarea._id = Util.str_id()
        return self.nuevaTarea(tarea, ntarea + 1)

    def borra(self, nTarea):
        del self.liGTareas[nTarea]

    def cambiaMarcaTarea(self, nTarea, valor):
        tarea = self.liGTareas[nTarea]
        tarea.marcado(valor)
        return tarea

    def cambiaMarcaTareaOwner(self, nTarea, valor):
        tarea = self.liGTareas[nTarea]
        tarea.marcadoOwner(valor)
        return tarea

    def tareaItem(self, item):
        for n, tarea in enumerate(self.liGTareas):
            if isinstance(tarea, GT_Item) and tarea.itemSC() == item:
                return tarea, n
        return None, -1

    def tareasPosicion(self, pos):
        li = []
        for n, tarea in enumerate(self.liGTareas):
            if isinstance(tarea, GT_Item) and tarea.itemSC().contain(pos):
                li.append((n, tarea))
        return li

    def itemTarea(self, nTarea):
        tarea = self.liGTareas[nTarea]
        return tarea.itemSC() if isinstance(tarea, GT_Item) else None

    def itemTareaOwner(self, nTarea):
        tarea = self.liGTareas[nTarea]
        return tarea.itemSCOwner() if isinstance(tarea, GT_Item) else None

    def borraItemTareaOwner(self, nTarea):
        tarea = self.liGTareas[nTarea]
        if isinstance(tarea, GT_Item):
            tarea.borraItemSCOwner()

    def marcado(self, nTarea):
        return self.liGTareas[nTarea].marcado()

    def marcadoOwner(self, nTarea):
        return self.liGTareas[nTarea].marcadoOwner()

    def desmarcaItem(self, item):
        for tarea in self.liGTareas:
            if isinstance(tarea, GT_Item) and tarea._itemSC == item:
                tarea.marcado(False)
                return

    def id(self, nTarea):
        return self.liGTareas[nTarea].id()

    def tarea(self, nTarea):
        nlig_tareas = len(self.liGTareas)
        if nlig_tareas == 0:
            return None
        if nTarea < 0:
            return self.liGTareas[nTarea] if nlig_tareas >= abs(nTarea) else None
        else:
            return self.liGTareas[nTarea] if nTarea < nlig_tareas else None

    def borraRepeticionUltima(self):
        len_li = len(self.liGTareas)
        if len_li > 1:
            ult_tarea = self.liGTareas[-1]
            if hasattr(ult_tarea, "_itemSC"):
                ult_bd = ult_tarea.bloqueDatos()
                ult_tp, ult_xid = ult_bd.tpid
                ult_a1h8 = ult_bd.a1h8
                for pos in range(len_li - 1):
                    tarea = self.liGTareas[pos]
                    if hasattr(tarea, "_itemSC"):
                        bd = tarea.itemSC().bloqueDatos
                        t_tp, t_xid = bd.tpid
                        t_a1h8 = bd.a1h8
                        t_h8a1 = t_a1h8[2:] + t_a1h8[:2]
                        if ult_tp == t_tp and ult_xid == t_xid and ult_a1h8 in (t_a1h8, t_h8a1):
                            return [pos, len_li - 1]
        return False

    def arriba(self, nTarea):
        if nTarea > 0:
            self.liGTareas[nTarea], self.liGTareas[nTarea - 1] = self.liGTareas[nTarea - 1], self.liGTareas[nTarea]
            return True
        else:
            return False

    def abajo(self, nTarea):
        if nTarea < (len(self.liGTareas) - 1):
            self.liGTareas[nTarea], self.liGTareas[nTarea + 1] = self.liGTareas[nTarea + 1], self.liGTareas[nTarea]
            return True
        else:
            return False

    def __len__(self):
        return len(self.liGTareas)

    def txt_tipo(self, row):
        tarea = self.liGTareas[row]
        return tarea.txt_tipo()

    def name(self, row):
        tarea = self.liGTareas[row]
        return tarea.name()

    def info(self, row):
        tarea = self.liGTareas[row]
        return tarea.info()

    def guarda(self):
        lista = []
        for tarea in self.liGTareas:
            lista.append(tarea.guarda())
        return lista

    def recuperaReg(self, reg):
        dic = {
            TP_FLECHA: GT_Flecha,
            TP_MARCO: GT_Marco,
            TP_SVG: GT_SVG,
            TP_MARKER: GT_Marker,
            TP_TEXTO: GT_Texto,
            TP_PIEZACREA: GT_PiezaCrea,
            TP_PIEZAMUEVE: GT_PiezaMueve,
            TP_PIEZABORRA: GT_PiezaBorra,
            TP_ACTION: GT_Action,
            TP_CONFIGURATION: GT_Configuration,
        }
        tarea = dic[reg["_tp"]](self)
        tarea.recupera(reg)
        self.nuevaTarea(tarea, -1)
        return tarea

    def recuperaMoviblesBoard(self):
        stPrevios = set()
        if self.board.dicMovibles:
            for k, item in self.board.dicMovibles.items():
                bd = item.bloqueDatos
                if hasattr(bd, "tpid"):
                    tp, xid = bd.tpid
                    if tp == TP_FLECHA:
                        tarea = GT_Flecha(self)

                    elif tp == TP_MARCO:
                        tarea = GT_Marco(self)

                    elif tp == TP_SVG:
                        tarea = GT_SVG(self)

                    elif tp == TP_MARKER:
                        tarea = GT_Marker(self)
                    tarea.itemSC(item)
                    self.nuevaTarea(tarea)
                    stPrevios.add((tp, xid, bd.a1h8))
        return stPrevios

    def recupera(self):
        fenm2 = self.board.last_position.fenm2()
        lista = self.board.dbVisual_lista(fenm2)
        self.liGTareas = []
        stPrevios = self.recuperaMoviblesBoard()
        if lista is not None:
            for reg in lista:
                if "_bloqueDatos" in reg:
                    bd = reg["_bloqueDatos"]
                    buscar = (bd.tpid[0], bd.tpid[1], bd.a1h8)
                    if not (buscar in stPrevios):
                        self.recuperaReg(reg)

        if self.winDirector:
            for tarea in self.liGTareas:
                if not (tarea.tp() in (TP_ACTION, TP_CONFIGURATION, TP_TEXTO)):
                    if not tarea.itemSC():
                        tarea.run()
                    tarea.marcado(True)
                else:
                    tarea.marcado(False)

    def play(self):
        self.cerrado = False
        for tarea in self.liGTareas:
            if not tarea.itemSC():
                tarea.run()
            if tarea.tp() == TP_TEXTO and tarea.continuar():
                while self.pizarra is not None and self.pizarra.is_blocked():
                    time.sleep(0.05)
            if self.cerrado:
                return


class DBManagerVisual:
    def __init__(self, file, showAllways=False, saveAllways=False):
        self._dbFEN = self._dbConfig = self._dbFlechas = self._dbMarcos = self._dbSVGs = self._dbMarkers = None
        self._showAllways = showAllways
        self._saveAllways = saveAllways
        self.setFichero(file)

    def saveMoviblesBoard(self, board):
        fenm2 = board.lastFenM2
        if not fenm2:
            return
        dicMovibles = board.dicMovibles
        n = 0
        for k, v in dicMovibles.items():
            if hasattr(v, "bloqueDatos") and hasattr(v.bloqueDatos, "tpid"):
                n += 1
        if n == 0:
            if fenm2 in self.dbFEN:
                del self.dbFEN[fenm2]
            return
        guion = Guion(board)
        guion.recuperaMoviblesBoard()
        self.dbFEN[fenm2] = guion.guarda()

    def saveAllways(self, yesno=None):
        if yesno is not None:
            self._saveAllways = yesno
        return self._saveAllways

    def showAllways(self, yesno=None):
        if yesno is not None:
            self._showAllways = yesno
        return self._showAllways

    def getConfig(self, key, default=None):
        return self.dbConfig.get(key, default)

    def setConfig(self, key, value):
        self.dbConfig[key] = value

    def setFichero(self, file):
        self.close()
        self._fichero = file if file is not None else Code.configuration.ficheroRecursos
        if not Util.exist_file(self._fichero):
            Util.file_copy(Code.path_resource("IntFiles", "recursos.dbl"), self._fichero)

        # li = self.dbConfig[b"SELECTBANDA"]
        # if li is None:
        #     dbr = DBManagerVisual("Code..resources/IntFiles/recursos.dbl", False)
        #     li = dbr.dbConfig["SELECTBANDA"]
        #     self.dbConfig["SELECTBANDA"] = li
        #     for xid, pos in li:
        #         key = xid[3:]
        #         if xid.startswith("_F"):
        #             self.dbFlechas[key] = dbr.dbFlechas[key]
        #         elif xid.startswith("_M"):
        #             self.dbMarcos[key] = dbr.dbMarcos[key]
        #         elif xid.startswith("_S"):
        #             self.dbSVGs[key] = dbr.dbSVGs[key]
        #         elif xid.startswith("_X"):
        #             self.dbMarkers[key] = dbr.dbMarkers[key]
        #     dbr.close()

    @property
    def file(self):
        return self._fichero

    @property
    def dbFEN(self):
        if self._dbFEN is None:
            self._dbFEN = UtilSQL.DictSQL(self._fichero, tabla="FEN")
        return self._dbFEN

    @property
    def dbConfig(self):
        if self._dbConfig is None:
            self._dbConfig = UtilSQL.DictSQL(self._fichero, tabla="Config")
            li = self.dbConfig["SELECTBANDA"]
        return self._dbConfig

    @property
    def dbFlechas(self):
        if self._dbFlechas is None:
            self._dbFlechas = UtilSQL.DictSQL(self._fichero, tabla="Flechas")
        return self._dbFlechas

    @property
    def dbMarcos(self):
        if self._dbMarcos is None:
            self._dbMarcos = UtilSQL.DictSQL(self._fichero, tabla="Marcos")
        return self._dbMarcos

    @property
    def dbSVGs(self):
        if self._dbSVGs is None:
            self._dbSVGs = UtilSQL.DictSQL(self._fichero, tabla="SVGs")
        return self._dbSVGs

    @property
    def dbMarkers(self):
        if self._dbMarkers is None:
            self._dbMarkers = UtilSQL.DictSQL(self._fichero, tabla="Markers")
        return self._dbMarkers

    def close(self):
        for db in (self._dbFEN, self._dbConfig, self._dbFlechas, self._dbMarcos, self._dbSVGs, self._dbMarkers):
            if db is not None:
                db.close()
        self._dbFEN = self._dbConfig = self._dbFlechas = self._dbMarcos = self._dbSVGs = self._dbMarkers = None


# def readGraphLive(configuration):
#     db = DBManagerVisual(configuration.ficheroRecursos, False)
#     rel = {0: "MR", 1: "ALTMR", 2: "SHIFTMR", 6: "MR1", 7: "ALTMR1", 8: "SHIFTMR1" }
#     dic = {}
#     li = db.dbConfig["SELECTBANDA"]
#     for xid, pos in li:
#         if xid.startswith("_F"):
#             xdb = db.dbFlechas
#             tp = TP_FLECHA
#         elif xid.startswith("_M"):
#             xdb = db.dbMarcos
#             tp = TP_MARCO
#         elif xid.startswith("_S"):
#             xdb = db.dbSVGs
#             tp = TP_SVG
#         elif xid.startswith("_X"):
#             xdb = db.dbMarkers
#             tp = TP_MARKER
#         else:
#             continue
#         if pos in rel:
#             valor = xdb[xid[3:]]
#             valor.TP = tp
#             dic[rel[pos]] = valor

#     db.close()
#     return dic

# def leeGraficos(configuration):
#     dicResp = {}

#     fdb = configuration.ficheroRecursos
#     dbConfig = UtilSQL.DictSQL(fdb, tabla="Config")
#     li = dbConfig["SELECTBANDA"]
#     dbConfig.close()
#     dbFlechas = dbMarcos = dbSVGs = dbMarkers = None
#     for xid, pos in li:
#         if xid.startswith("_F"):
#             if not dbFlechas:
#                 dbFlechas = UtilSQL.DictSQL(fdb, tabla="Flechas")
#             dicResp[pos] = dbFlechas[xid[3:]]
#             dicResp[pos].xtipo = TP_FLECHA
#         elif xid.startswith("_M"):
#             if not dbMarcos:
#                 dbMarcos = UtilSQL.DictSQL(fdb, tabla="Marcos")
#             dicResp[pos] = dbMarcos[xid[3:]]
#             dicResp[pos].xtipo = TP_MARCO
#         elif xid.startswith("_S"):
#             if not dbSVGs:
#                 dbSVGs = UtilSQL.DictSQL(fdb, tabla="SVGs")
#             dicResp[pos] = dbSVGs[xid[3:]]
#             dicResp[pos].xtipo = TP_SVG
#         elif xid.startswith("_X"):
#             if not dbMarkers:
#                 dbMarkers = UtilSQL.DictSQL(fdb, tabla="Markers")
#             dicResp[pos] = dbMarkers[xid[3:]]
#             dicResp[pos].xtipo = TP_MARKER
#     for db in (dbFlechas, dbMarcos, dbSVGs, dbMarkers):
#         if db:
#             db.close()

#     return dicResp
