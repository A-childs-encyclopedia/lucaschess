import copy

from PySide2 import QtCore

VTEXTO = 0
VENTERO = 1
VDECIMAL = 2


class Variable:
    def __init__(self, name, tipo, inicial):
        self.id = None
        self.name = name
        self.tipo = tipo
        self.inicial = inicial
        self.valor = inicial
        self.id = None


class Tarea:
    def enlaza(self, cpu):
        self.cpu = cpu
        self.id = cpu.nuevaID()
        self.junks = cpu.junks
        self.padre = 0


class TareaDuerme(Tarea):
    def __init__(self, seconds):
        self.seconds = seconds

    def enlaza(self, cpu):
        Tarea.enlaza(self, cpu)
        self.totalPasos = int(self.seconds * self.junks)

        self.pasoActual = 0

    def unPaso(self):
        self.pasoActual += 1
        return self.pasoActual >= self.totalPasos  # si es ultimo

    def __str__(self):
        return "DUERME %0.2f" % self.seconds


class TareaToolTip(Tarea):
    def __init__(self, texto):
        self.texto = texto

    def unPaso(self):
        self.cpu.board.setToolTip(self.texto)
        return True

    def __str__(self):
        return "TOOLTIP %s" % self.texto


class TareaPonPosicion(Tarea):
    def __init__(self, position):
        self.position = position

    def unPaso(self):
        self.cpu.board.set_position(self.position)
        return True

    def __str__(self):
        return self.position.fen()


class TareaCambiaPieza(Tarea):
    def __init__(self, a1h8, pieza):
        self.a1h8 = a1h8
        self.pieza = pieza

    def unPaso(self):
        self.cpu.board.cambiaPieza(self.a1h8, self.pieza)
        return True

    def __str__(self):
        return _X(_("Change piece in %1 to %2"), self.a1h8, self.pieza)

    def directo(self, board):
        return board.cambiaPieza(self.a1h8, self.pieza)


class TareaBorraPieza(Tarea):
    def __init__(self, a1h8, tipo=None):
        self.a1h8 = a1h8
        self.tipo = tipo

    def unPaso(self):
        if self.tipo:
            self.cpu.board.borraPiezaTipo(self.a1h8, self.tipo)
        else:
            self.cpu.board.borraPieza(self.a1h8)
        return True

    def __str__(self):
        return _X(_("Remove piece on %1"), self.a1h8)

    def directo(self, board):
        board.borraPieza(self.a1h8)


class TareaMuevePieza(Tarea):
    def __init__(self, from_a1h8, to_a1h8, seconds=0.0):
        self.pieza = None
        self.from_a1h8 = from_a1h8
        self.to_a1h8 = to_a1h8
        self.seconds = seconds

    def enlaza(self, cpu):
        Tarea.enlaza(self, cpu)

        self.board = self.cpu.board

        dx, dy = self.a1h8_xy(self.from_a1h8)
        hx, hy = self.a1h8_xy(self.to_a1h8)

        linea = QtCore.QLineF(dx, dy, hx, hy)

        pasos = int(self.seconds * self.junks)
        self.liPuntos = []
        for x in range(1, pasos + 1):
            self.liPuntos.append(linea.pointAt(float(x) / pasos))
        self.nPaso = 0
        self.totalPasos = len(self.liPuntos)

    def a1h8_xy(self, a1h8):
        row = int(a1h8[1])
        column = ord(a1h8[0]) - 96
        x = self.board.columna2punto(column)
        y = self.board.fila2punto(row)
        return x, y

    def unPaso(self):
        if self.pieza is None:
            self.pieza = self.board.damePiezaEn(self.from_a1h8)
            if self.pieza is None:
                return True
        npuntos = len(self.liPuntos)
        if npuntos == 0:
            return True
        if self.nPaso >= npuntos:
            self.nPaso = npuntos - 1
        p = self.liPuntos[self.nPaso]
        bp = self.pieza.bloquePieza
        bp.physical_pos.x = p.x()
        bp.physical_pos.y = p.y()
        self.pieza.rehazPosicion()
        self.nPaso += 1
        siUltimo = self.nPaso >= self.totalPasos
        if siUltimo:
            # Para que este al final en la physical_pos correcta
            self.board.colocaPieza(bp, self.to_a1h8)
        return siUltimo

    def __str__(self):
        return _X(_("Move piece from %1 to %2 on %3 second (s)"), self.from_a1h8, self.to_a1h8, "%0.2f" % self.seconds)

    def directo(self, board):
        board.muevePieza(self.from_a1h8, self.to_a1h8)


class TareaMuevePiezaV(TareaMuevePieza):
    def __init__(self, from_a1h8, to_a1h8, vsegundos):
        TareaMuevePieza.__init__(self, from_a1h8, to_a1h8, 0.0)
        self.vsegundos = vsegundos

    def enlaza(self, cpu):
        self.seconds = self.vsegundos.valor
        TareaMuevePieza.enlaza(self, cpu)

    def __str__(self):
        return _X(
            _("Move piece from %1 to %2 on %3 second (s)"),
            self.from_a1h8,
            self.to_a1h8,
            "%0.2f (%s)" % (self.vsegundos.valor, self.vsegundos.name),
        )

    def directo(self, board):
        board.muevePieza(self.from_a1h8, self.to_a1h8)


class TareaMuevePiezaLI(Tarea):
    def __init__(self, lista, seconds):
        self.lista = lista
        self.seconds = seconds

    def enlaza(self, cpu):
        Tarea.enlaza(self, cpu)
        self.board = self.cpu.board
        self.pieza = None
        self.from_a1h8 = self.lista[0][0]
        self.to_a1h8 = self.lista[-1][1]
        self.liPuntos = []
        pasos1 = int(self.seconds * self.junks / len(self.lista))

        for from_a1h8, to_a1h8 in self.lista:
            dx, dy = self.a1h8_xy(from_a1h8)
            hx, hy = self.a1h8_xy(to_a1h8)

            linea = QtCore.QLineF(dx, dy, hx, hy)

            for x in range(1, pasos1 + 1):
                self.liPuntos.append(linea.pointAt(float(x) / pasos1))
        self.nPaso = 0
        self.totalPasos = len(self.liPuntos)

    def a1h8_xy(self, a1h8):
        row = int(a1h8[1])
        column = ord(a1h8[0]) - 96
        x = self.board.columna2punto(column)
        y = self.board.fila2punto(row)
        return x, y

    def unPaso(self):
        if self.pieza is None:
            self.pieza = self.board.damePiezaEn(self.from_a1h8)
        p = self.liPuntos[self.nPaso]
        bp = self.pieza.bloquePieza
        bp.physical_pos.x = p.x()
        bp.physical_pos.y = p.y()
        self.pieza.rehazPosicion()
        self.nPaso += 1
        siUltimo = self.nPaso >= self.totalPasos
        if siUltimo:
            # Para que este al final en la position correcta
            self.board.colocaPieza(bp, self.to_a1h8)
        return siUltimo


class TareaCreaFlecha(Tarea):
    def __init__(self, tutorial, from_sq, to_sq, idFlecha):
        self.tutorial = tutorial
        self.idFlecha = idFlecha
        self.from_sq = from_sq
        self.to_sq = to_sq
        self.scFlecha = None

    def unPaso(self):
        regFlecha = copy.deepcopy(self.tutorial.dameFlecha(self.idFlecha))
        regFlecha.siMovible = True
        regFlecha.a1h8 = self.from_sq + self.to_sq
        self.scFlecha = self.cpu.board.creaFlecha(regFlecha)
        return True

    def __str__(self):
        vFlecha = self.tutorial.dameFlecha(self.idFlecha)
        return _("Arrow") + " " + vFlecha.name + " " + self.from_sq + self.to_sq

    def directo(self, board):
        regFlecha = copy.deepcopy(self.tutorial.dameFlecha(self.idFlecha))
        regFlecha.siMovible = True
        regFlecha.a1h8 = self.from_sq + self.to_sq
        self.scFlecha = board.creaFlecha(regFlecha)
        return True


class TareaCreaMarco(Tarea):
    def __init__(self, tutorial, from_sq, to_sq, idMarco):
        self.tutorial = tutorial
        self.idMarco = idMarco
        self.from_sq = from_sq
        self.to_sq = to_sq

    def unPaso(self):
        regMarco = copy.deepcopy(self.tutorial.dameMarco(self.idMarco))
        regMarco.siMovible = True
        regMarco.a1h8 = self.from_sq + self.to_sq
        self.scMarco = self.cpu.board.creaMarco(regMarco)
        return True

    def __str__(self):
        vMarco = self.tutorial.dameMarco(self.idMarco)
        return _("Box") + " " + vMarco.name + " " + self.from_sq + self.to_sq

    def directo(self, board):
        regMarco = copy.deepcopy(self.tutorial.dameMarco(self.idMarco))
        regMarco.siMovible = True
        regMarco.a1h8 = self.from_sq + self.to_sq
        self.scMarco = board.creaMarco(regMarco)
        return True


class TareaCreaSVG(Tarea):
    def __init__(self, tutorial, from_sq, to_sq, idSVG):
        self.tutorial = tutorial
        self.idSVG = idSVG
        self.from_sq = from_sq
        self.to_sq = to_sq

    def unPaso(self):
        regSVG = copy.deepcopy(self.tutorial.dameSVG(self.idSVG))
        regSVG.siMovible = True
        regSVG.a1h8 = self.from_sq + self.to_sq
        self.scSVG = self.cpu.board.creaSVG(regSVG)
        return True

    def __str__(self):
        vSVG = self.tutorial.dameSVG(self.idSVG)
        return _("Image") + " " + vSVG.name + " " + self.from_sq + self.to_sq

    def directo(self, board):
        regSVG = copy.deepcopy(self.tutorial.dameSVG(self.idSVG))
        regSVG.siMovible = True
        regSVG.a1h8 = self.from_sq + self.to_sq
        self.scSVG = board.creaSVG(regSVG)
        return True
