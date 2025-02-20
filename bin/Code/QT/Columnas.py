from PySide2 import QtCore, QtGui

from Code.QT import Delegados


class Columna:
    """
    Definicion de cada column del grid.
    """

    def __init__(
        self,
        key,
        head,
        ancho=100,
        centered=False,
        siDerecha=False,
        rgbTexto=None,
        rgbFondo=None,
        siOrden=True,
        estadoOrden=0,
        edicion=None,
        siEditable=None,
        must_show=True,
        siChecked=False,
    ):
        """

        @param key: referencia de la column.
        @param head: texto mostrado en el grid como head.
        @param ancho: anchura en pixels.
        @param centered: alineacion
        @param siDerecha: alineacion, se ha diferenciado la alineacion, para que al definir
            columnas sea mas facilmente visible el tipo de alineacion, cuando no es a la izquierda.
        @param rgbTexto: color del texto como un entero.
        @param rgbFondo: color de fondo.
        @param siOrden: si se puede ordenar por este campo
        @param estadoOrden: indica cual es el orden inicial de la column  -1 Desc, 0 No, 1 Asc
        @param edicion: objeto delegate usado para la edicion de los campos de esta column
        @param siEditable: este parametro se usa cuando aunque la column tiene un delegate asociado para mostrarla, sin embargo no es editable.
        @param must_show: si se muestra o no.
        @param siChecked: si es un campo de chequeo.
        """

        self.key = key
        self.cabeceraDef = self.head = head
        self.anchoDef = self.ancho = ancho

        alineacion = "i"
        if centered:
            alineacion = "c"
        if siDerecha:
            alineacion = "d"
        self.alineacionDef = self.alineacion = alineacion

        self.rgbTextoDef = self.rgbTexto = rgbTexto or -1
        self.rgbFondoDef = self.rgbFondo = rgbFondo or -1

        self.position = 0

        self.siOrden = siOrden
        self.stateOrden = estadoOrden  # -1 Desc, 0 No, 1 Asc

        self.edicion = edicion
        self.siEditable = False
        if self.edicion:
            self.siEditable = True
            if siEditable is not None:
                self.siEditable = siEditable

        self.siMostrarDef = self.must_show = must_show
        self.siChecked = siChecked

        if siChecked:
            self.edicion = Delegados.PmIconosCheck()
            self.siEditable = True

        self.ponQT()

    def ponQT(self):
        self.qtAlineacion = self.QTalineacion(self.alineacion)
        self.qtColorTexto = self.QTcolorTexto(self.rgbTexto)
        self.qtColorFondo = self.QTcolorFondo(self.rgbFondo)

    def porDefecto(self):
        self.head = self.cabeceraDef
        self.alineacion = self.alineacionDef
        self.rgbTexto = self.rgbTextoDef
        self.rgbFondo = self.rgbFondoDef
        self.must_show = self.siMostrarDef

    def copia_defecto(self, col):
        self.cabeceraDef = col.cabeceraDef
        self.alineacionDef = col.alineacionDef
        self.rgbTextoDef = col.rgbTextoDef
        self.rgbFondoDef = col.rgbFondoDef
        self.siMostrarDef = col.siMostrarDef

    def QTalineacion(self, alin):
        if alin == "c":
            qtalin = QtCore.Qt.AlignCenter
        elif alin == "d":
            qtalin = int(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        else:
            qtalin = QtCore.Qt.AlignVCenter

        return qtalin

    def QTcolorTexto(self, rgb):
        """
        Convierte un parametro de color del texto para que sea usable por QT
        """
        if rgb == -1:
            return None
        else:
            return QtGui.QColor(rgb)

    def QTcolorFondo(self, rgb):
        """
        Convierte un parametro de color del fondo para que sea usable por QT
        """
        if rgb == -1:
            return None
        else:
            return QtGui.QBrush(QtGui.QColor(rgb))

    def guardarConf(self, dic, grid):
        """
        Guarda los valores actuales de configuration de la column.

        @param dic: diccionario con los datos del modulo al que pertenece la column.
        """

        xid = grid.id if grid else None

        def x(c, v):
            if xid is None:
                k = "%s.%s" % (self.key, c)
            else:
                k = "%s.%s.%s" % (self.key, c, xid)

            dic[k] = v

        x("CABECERA", self.head)  # Traduccion
        x("ANCHO", str(self.ancho))
        x("ALINEACION", self.alineacion)
        x("RGBTEXTO", str(self.rgbTexto))
        x("RGBFONDO", str(self.rgbFondo))
        x("POSICION", str(self.position))
        x("SIMOSTRAR", "S" if self.must_show else "N")

    def recuperarConf(self, dic, grid, with_cabeceras=False):
        """
        Recupera los valores de configuration de la column.

        @param dic: diccionario con los datos del modulo al que pertenece la column.
        """
        xid = grid.id if grid else None

        def x(varTxt, varInt, tipo):
            key = "%s.%s" % (self.key, varTxt)
            if xid:
                key += ".%s" % xid
            if key in dic:
                v = dic[key]
                if tipo == "n":
                    v = int(v)
                elif tipo == "l":
                    v = v == "S"
                setattr(self, varInt, v)

        if with_cabeceras:
            x("CABECERA", "head", "t")  # Traduccion, se pierde si no
        x("ANCHO", "ancho", "n")
        x("ALINEACION", "alineacion", "t")
        x("RGBTEXTO", "rgbTexto", "n")
        x("RGBFONDO", "rgbFondo", "n")
        x("POSICION", "position", "n")
        x("SIMOSTRAR", "must_show", "l")

        self.ponQT()

        return self


class ListaColumnas:
    """
    Recorda la configuration de columnas como un bloque.
    """

    def __init__(self):
        self.li_columns = []
        self.posCreacion = 0

    def nueva(
        self,
        key,
        head="",
        ancho=100,
        centered=False,
        siDerecha=False,
        rgbTexto=None,
        rgbFondo=None,
        siOrden=True,
        estadoOrden=0,
        edicion=None,
        siEditable=None,
        must_show=True,
        siChecked=False,
    ):
        """
        Contiene los mismos parametros que la Columna.

        @param key: referencia de la column.
        @param head: texto mostrado en el grid como head.
        @param ancho: anchura en pixels.
        @param centered: alineacion
        @param siDerecha: alineacion, se ha diferenciado la alineacion, para que al definir
            columnas sea mas facilmente visible el tipo de alineacion, cuando no es a la izquierda.
        @param rgbTexto: color del texto como un entero.
        @param rgbFondo: color de fondo.
        @param siOrden: si se puede ordenar por este campo
        @param estadoOrden: indica cual es el orden inicial de la column  -1 Desc, 0 No, 1 Asc
        @param edicion: objeto delegate usado para la edicion de los campos de esta column
        @param siEditable: este parametro se usa cuando aunque la column tiene un delegate asociado para mostrarla, sin embargo no es editable.
        @param must_show: si se muestra o no.
        @param siChecked: si es un campo de chequeo.

        @return: la column creada.
        """
        column = Columna(
            key, head, ancho, centered, siDerecha, rgbTexto, rgbFondo, siOrden, estadoOrden, edicion, siEditable, must_show, siChecked
        )
        self.li_columns.append(column)
        self.posCreacion += 1
        column.posCreacion = self.posCreacion
        return column

    def column(self, numCol):
        return self.li_columns[numCol]

    def borrarColumna(self, numCol):
        del self.li_columns[numCol]

    def numColumnas(self):
        return len(self.li_columns)

    def resetEstadoOrden(self):
        for x in self.li_columns:
            x.stateOrden = 0

    def porDefecto(self):
        for x in self.li_columns:
            x.porDefecto()

    def columnasMostrables(self):
        """
        Crea un nuevo objeto con solo las columnas mostrables.
        """
        for col in self.li_columns:
            col.ponQT()
        cols = [column for column in self.li_columns if column.must_show]
        cols.sort(key=lambda x: x.position)
        oColumnasR = ListaColumnas()
        oColumnasR.li_columns = cols
        return oColumnasR

    def buscaColumna(self, key):
        for col in self.li_columns:
            if col.key == key:
                return col
        return None

    def clone(self):
        oColumnasCopy = ListaColumnas()
        for col in self.li_columns:
            col_nueva = oColumnasCopy.nueva(
                col.key,
                head=col.head,
                ancho=col.ancho,
                centered=col.alineacion == "c",
                siDerecha=col.alineacion == "d",
                rgbTexto=col.rgbTexto,
                rgbFondo=col.rgbFondo,
                siOrden=col.siOrden,
                estadoOrden=col.stateOrden,
                edicion=col.edicion,
                siEditable=col.siEditable,
                must_show=col.must_show,
                siChecked=col.siChecked,
            )
            col_nueva.copia_defecto(col)
        return oColumnasCopy

    def save_dic(self, grid):
        dic_conf = {}
        for col in self.li_columns:
            col.guardarConf(dic_conf, grid)
        return dic_conf

    def restore_dic(self, dic_conf, grid):
        for col in self.li_columns:
            col.recuperarConf(dic_conf, grid)
