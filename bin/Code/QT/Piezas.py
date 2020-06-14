import collections
import os
import shutil

from PySide2 import QtCore, QtGui, QtSvg

from Code.QT import Colocacion
from Code.QT import Controles
from Code.QT import FormLayout
from Code.QT import Iconos
from Code.QT import QTVarios
from Code import TrListas
import Code
from Code.Constantes import *


class ConjuntoPiezas:
    def __init__(self, name):
        self.name = name
        self.dicPiezas = self.leePiezas(name)

    def leePiezas(self, name):
        try:
            dic = {}
            for pieza in "rnbqkpRNBQKP":
                fich = Code.path_resource("Pieces", name, "%s%s.svg" % ("w" if pieza.isupper() else "b", pieza.lower()))
                with open(fich, "rb") as f:
                    qb = QtCore.QByteArray(f.read())
                dic[pieza] = qb
            return dic
        except:
            return self.leePiezas("Cburnett")

    def render(self, pieza):
        return QtSvg.QSvgRenderer(self.dicPiezas[pieza])

    def widget(self, pieza):
        w = QtSvg.QSvgWidget()
        w.load(self.dicPiezas[pieza])
        return w

    def pixmap(self, pieza, tam=24):
        pm = QtGui.QPixmap(tam, tam)
        pm.fill(QtCore.Qt.transparent)
        render = self.render(pieza)
        painter = QtGui.QPainter()
        painter.begin(pm)
        render.render(painter)
        painter.end()
        return pm

    def label(self, owner, pieza, tam):
        pm = self.pixmap(pieza, tam)
        lb = Controles.LB(owner)
        lb.ponImagen(pm)
        lb.pieza = pieza
        lb.tam_pieza = tam
        return lb

    def change_label(self, lb, tam):
        if lb.tam_pieza != tam:
            pm = self.pixmap(lb.pieza, tam)
            lb.ponImagen(pm)

    def icono(self, pieza):
        icon = QtGui.QIcon(self.pixmap(pieza, 32))
        return icon

    def cursor(self, pieza):
        return QtGui.QCursor(self.pixmap(pieza))


class TodasPiezas:
    def __init__(self):
        self.dicConjuntos = {}

    def selecciona(self, name):
        if name in self.dicConjuntos:
            return self.dicConjuntos[name]
        else:
            return self.nuevo(name)

    def nuevo(self, name):
        self.dicConjuntos[name] = ConjuntoPiezas(name)
        return self.dicConjuntos[name]

    def icono(self, pieza, name):
        fich = Code.path_resource("Pieces", name, "%s%s.svg" % ("w" if pieza.isupper() else "b", pieza.lower()))
        with open(fich, "rb") as f:
            qb = QtCore.QByteArray(f.read())
        pm = QtGui.QPixmap(32, 32)
        pm.fill(QtCore.Qt.transparent)
        render = QtSvg.QSvgRenderer(qb)
        painter = QtGui.QPainter()
        painter.begin(pm)
        render.render(painter)
        painter.end()
        icon = QtGui.QIcon(pm)
        return icon

    def iconoDefecto(self, pieza):
        return self.icono(pieza, "Cburnett")

    def saveAllPNG(self, name, px):
        for pieza in "pnbrqk":
            for color in "wb":
                fich = Code.path_resource("Pieces", name, "%s%s.svg" % (color, pieza))
                with open(fich, "rb") as f:
                    qb = QtCore.QByteArray(f.read())
                pm = QtGui.QPixmap(px, px)
                pm.fill(QtCore.Qt.transparent)
                render = QtSvg.QSvgRenderer(qb)
                painter = QtGui.QPainter()
                painter.begin(pm)
                render.render(painter)
                painter.end()
                pm.save(Code.path_resource("IntFiles", "Figs", "%s%s.png" % (color, pieza)), "PNG")


HIDE, GREY, CHECKER, SHOW = range(4)


class BlindfoldConfig:
    def __init__(self, nomPiezasOri, dicPiezas=None):
        self.nomPiezasOri = nomPiezasOri
        if dicPiezas is None:
            self.restore()
        else:
            self.dicPiezas = dicPiezas

    def ficheroBase(self, pz, siWhite):
        pz = pz.lower()
        if siWhite:
            pzT = pz.upper()
        else:
            pzT = pz
        tipo = self.dicPiezas[pzT]
        if tipo == SHOW:
            pz = ("w" if siWhite else "b") + pz
            return Code.path_resource("Pieces", self.nomPiezasOri, pz + ".svg")
        if tipo == HIDE:
            fich = "h"
        elif tipo == GREY:
            fich = "g"
        elif tipo == CHECKER:
            fich = "w" if siWhite else "b"
        return Code.path_resource("IntFiles/Svg", "blind_%s.svg" % fich)

    def restore(self):
        self.dicPiezas = Code.configuracion.leeVariables("BLINDFOLD")
        if not self.dicPiezas:
            for pieza in "rnbqkpRNBQKP":
                self.dicPiezas[pieza] = HIDE

    def save(self):
        Code.configuracion.escVariables("BLINDFOLD", self.dicPiezas)


class Blindfold(ConjuntoPiezas):
    def __init__(self, nomPiezasOri, tipo=BLINDFOLD_CONFIG):
        self.name = "BlindFold"
        self.carpetaBF = os.path.join(Code.configuracion.carpeta, "BlindFoldPieces")
        self.carpetaPZ = Code.path_resource("IntFiles")
        self.tipo = tipo
        self.reset(nomPiezasOri)

    def leePiezas(self, name=None):  # name usado por compatibilidad
        dic = {}
        for pieza in "rnbqkpRNBQKP":
            fich = os.path.join(self.carpetaBF, "%s%s.svg" % ("w" if pieza.isupper() else "b", pieza.lower()))
            with open(fich, "rb") as f:
                qb = QtCore.QByteArray(f.read())
            dic[pieza] = qb
        return dic

    def reset(self, nomPiezasOri):
        if self.tipo == BLINDFOLD_CONFIG:
            dicTPiezas = None
        else:
            w = b = HIDE
            if self.tipo == BLINDFOLD_WHITE:
                b = SHOW
            elif self.tipo == BLINDFOLD_BLACK:
                w = SHOW
            dicTPiezas = {}
            for pieza in "rnbqkp":
                dicTPiezas[pieza] = b
                dicTPiezas[pieza.upper()] = w
        self.configBF = BlindfoldConfig(nomPiezasOri, dicPiezas=dicTPiezas)
        if not os.path.isdir(self.carpetaBF):
            os.mkdir(self.carpetaBF)

        for siWhite in (True, False):
            for pieza in "rnbqkp":
                ori = self.configBF.ficheroBase(pieza, siWhite)
                bs = "w" if siWhite else "b"
                dest = os.path.join(self.carpetaBF, "%s%s.svg" % (bs, pieza))
                shutil.copy(ori, dest)

        self.dicPiezas = self.leePiezas()


class WBlindfold(QTVarios.WDialogo):
    def __init__(self, owner, nomPiezasOri):

        titulo = _("Blindfold") + " - " + _("Configuration")
        icono = Iconos.Ojo()
        extparam = "wblindfold"
        QTVarios.WDialogo.__init__(self, owner, titulo, icono, extparam)

        self.config = BlindfoldConfig(nomPiezasOri)
        self.nomPiezasOri = nomPiezasOri

        lbWhite = Controles.LB(self, _("White")).ponTipoLetra(peso=75, puntos=10)
        lbBlack = Controles.LB(self, _("Black")).ponTipoLetra(peso=75, puntos=10)

        self.dicWidgets = collections.OrderedDict()
        self.dicImgs = {}

        li_options = ((_("Hide"), HIDE), (_("Green"), GREY), (_("Checker"), CHECKER), (_("Show"), SHOW))
        dicNomPiezas = TrListas.dicNomPiezas()

        def haz(pz):
            tpW = self.config.dicPiezas[pz.upper()]
            tpB = self.config.dicPiezas[pz]
            lbPZw = Controles.LB(self)
            cbPZw = Controles.CB(self, li_options, tpW).capturaCambiado(self.reset)
            lbPZ = Controles.LB(self, dicNomPiezas[pz.upper()]).ponTipoLetra(peso=75, puntos=10)
            lbPZb = Controles.LB(self)
            cbPZb = Controles.CB(self, li_options, tpB).capturaCambiado(self.reset)
            self.dicWidgets[pz] = [lbPZw, cbPZw, lbPZ, lbPZb, cbPZb, None, None]

        for pz in "kqrbnp":
            haz(pz)

        btAllW = Controles.PB(self, _("All White"), self.allWhite, plano=False)
        self.cbAll = Controles.CB(self, li_options, HIDE)
        btAllB = Controles.PB(self, _("All Black"), self.allBlack, plano=False)

        btSwap = Controles.PB(self, _("Swap"), self.swap, plano=False)

        li_acciones = (
            (_("Save"), Iconos.Grabar(), "grabar"),
            None,
            (_("Cancel"), Iconos.Cancelar(), "cancelar"),
            None,
            (_("Configurations"), Iconos.Opciones(), "configurations"),
            None,
        )
        tb = Controles.TB(self, li_acciones)

        ly = Colocacion.G()
        ly.controlc(lbWhite, 0, 1).controlc(lbBlack, 0, 3)
        fila = 1
        for pz in "kqrbnp":
            lbPZw, cbPZw, lbPZ, lbPZb, cbPZb, tipoW, tipoB = self.dicWidgets[pz]
            ly.control(cbPZw, fila, 0)
            ly.controlc(lbPZw, fila, 1)
            ly.controlc(lbPZ, fila, 2)
            ly.controlc(lbPZb, fila, 3)
            ly.control(cbPZb, fila, 4)
            fila += 1

        ly.filaVacia(fila, 20)
        fila += 1

        ly.controld(btAllW, fila, 0, 1, 2)
        ly.control(self.cbAll, fila, 2)
        ly.control(btAllB, fila, 3, 1, 2)
        ly.controlc(btSwap, fila + 1, 0, 1, 5)
        ly.margen(20)

        layout = Colocacion.V().control(tb).otro(ly)

        self.setLayout(layout)

        self.reset()

    def process_toolbar(self):
        getattr(self, self.sender().clave)()

    def closeEvent(self):
        self.save_video()

    def grabar(self):
        self.save_video()
        self.config.save()
        self.accept()

    def cancelar(self):
        self.save_video()
        self.reject()

    def configurations(self):
        dic = Code.configuracion.leeVariables("BLINDFOLD")
        dicConf = collections.OrderedDict()
        for k in dic:
            if k.startswith("_"):
                cl = k[1:]
                dicConf[cl] = dic[k]

        menu = QTVarios.LCMenu(self)
        for k in dicConf:
            menu.opcion((True, k), k, Iconos.PuntoAzul())
        menu.separador()
        menu.opcion((True, None), _("Save current configuration"), Iconos.PuntoVerde())
        if dicConf:
            menu.separador()
            menudel = menu.submenu(_("Remove"), Iconos.Delete())
            for k in dicConf:
                menudel.opcion((False, k), k, Iconos.PuntoNegro())

        resp = menu.lanza()
        if resp is None:
            return

        si, cual = resp

        if si:
            if cual:
                dpz = dic["_" + cual]
                for pz in "kqrbnp":
                    lbPZw, cbPZw, lbPZ, lbPZb, cbPZb, tipoW, tipoB = self.dicWidgets[pz]
                    cbPZw.ponValor(dpz[pz.upper()])
                    cbPZb.ponValor(dpz[pz])
                self.reset()
            else:
                liGen = [(None, None)]
                liGen.append((_("Name") + ":", ""))

                resultado = FormLayout.fedit(
                    liGen,
                    title=_("Save current configuration"),
                    parent=self,
                    min_width=460,
                    icon=Iconos.TutorialesCrear(),
                )
                if resultado is None:
                    return None

                accion, liResp = resultado
                name = liResp[0].strip()
                if not name:
                    return None
                dic["_%s" % name] = self.config.dicPiezas
                Code.configuracion.escVariables("BLINDFOLD", dic)
        else:
            del dic["_%s" % cual]
            Code.configuracion.escVariables("BLINDFOLD", dic)

    def allWhite(self):
        tp = self.cbAll.valor()
        for pzB in "rnbqkp":
            lbPZw, cbPZw, lbPZ, lbPZb, cbPZb, tipoW, tipoB = self.dicWidgets[pzB]
            cbPZw.ponValor(tp)
        self.reset()

    def allBlack(self):
        tp = self.cbAll.valor()
        for pzB in "rnbqkp":
            lbPZw, cbPZw, lbPZ, lbPZb, cbPZb, tipoW, tipoB = self.dicWidgets[pzB]
            cbPZb.ponValor(tp)
        self.reset()

    def swap(self):
        for pzB in "rnbqkp":
            lbPZw, cbPZw, lbPZ, lbPZb, cbPZb, tipoW, tipoB = self.dicWidgets[pzB]
            tpB = cbPZb.valor()
            tpW = cbPZw.valor()
            cbPZb.ponValor(tpW)
            cbPZw.ponValor(tpB)
        self.reset()

    def reset(self):
        for pzB in "kqrbnp":
            lbPZw, cbPZw, lbPZ, lbPZb, cbPZb, tipoW, tipoB = self.dicWidgets[pzB]
            tipoNv = cbPZw.valor()
            if tipoW != tipoNv:
                pzW = pzB.upper()
                self.config.dicPiezas[pzW] = tipoNv
                self.dicWidgets[pzB][5] = tipoNv  # tiene que ser pzB que esta en misnusculas
                fich = self.config.ficheroBase(pzB, True)
                if fich in self.dicImgs:
                    pm = self.dicImgs[fich]
                else:
                    pm = QTVarios.fsvg2pm(fich, 32)
                    self.dicImgs[fich] = pm
                lbPZw.ponImagen(pm)
            tipoNv = cbPZb.valor()
            if tipoB != tipoNv:
                self.config.dicPiezas[pzB] = tipoNv
                self.dicWidgets[pzB][6] = tipoNv
                fich = self.config.ficheroBase(pzB, False)
                if fich in self.dicImgs:
                    pm = self.dicImgs[fich]
                else:
                    pm = QTVarios.fsvg2pm(fich, 32)
                    self.dicImgs[fich] = pm
                lbPZb.ponImagen(pm)
