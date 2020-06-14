import os, time

from PIL import Image
from PySide2 import QtCore, QtGui, QtWidgets

from Code import Position
from Code import Move
from Code import Game
from Code import Util
import Code
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Controles
from Code.QT import Delegados
from Code.QT import FormLayout
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code.QT import Tablero
from Code.QT import Scanner

MODO_POSICION, MODO_PARTIDA = range(2)


def hamming_distance(string, other_string):
    # Adaptation from https://github.com/bunchesofdonald/photohash, MIT license
    """ Computes the hamming distance between two strings. """
    return sum(map(lambda x: 0 if x[0] == x[1] else 1, zip(string, other_string)))


def average_hash(img, hash_size=8):
    # Adaptation from https://github.com/bunchesofdonald/photohash, MIT license
    """ Computes the average hash of the given image. """
    # Open the image, resize it and convert it to black & white.
    image = img.resize((hash_size, hash_size), Image.ANTIALIAS).convert("L")
    pixels = list(image.getdata())

    avg = sum(pixels) // len(pixels)

    # Compute the hash based on each pixels value compared to the average.
    bits = "".join(map(lambda pixel: "1" if pixel > avg else "0", pixels))
    hashformat = "0{hashlength}x".format(hashlength=hash_size ** 2 // 4)
    return int(bits, 2).__format__(hashformat)


class WPosicion(QtWidgets.QWidget):
    def __init__(self, wparent, is_game, game):
        self.game = game
        self.position = game.first_position
        self.configuracion = configuracion = Code.configuracion

        self.is_game = is_game

        self.wparent = wparent

        QtWidgets.QWidget.__init__(self, wparent)

        li_acciones = (
            (_("Save"), Iconos.GrabarComo(), self.save),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.cancelar),
            None,
            (_("Start position"), Iconos.Inicio(), self.inicial),
            None,
            (_("Clear board"), Iconos.Borrar(), self.limpiaTablero),
            (_("Paste FEN position"), Iconos.Pegar16(), self.pegar),
            (_("Copy FEN position"), Iconos.Copiar(), self.copiar),
            (_("Scanner"), Iconos.Scanner(), self.scanner),
        )

        self.tb = Controles.TBrutina(self, li_acciones, siTexto=False, tamIcon=20)

        config_board = configuracion.config_board("VOYAGERPOS", 24)
        self.tablero = Tablero.PosTablero(self, config_board)
        self.tablero.crea()
        self.tablero.set_dispatcher(self.mueve)
        self.tablero.mensBorrar = self.borraCasilla
        self.tablero.mensCrear = self.creaCasilla
        self.tablero.mensRepetir = self.repitePieza
        self.tablero.ponDispatchDrop(self.dispatchDrop)
        self.tablero.baseCasillasSC.setAcceptDrops(True)

        dragDropWB = QTVarios.ListaPiezas(self, "P,N,B,R,Q,K", self.tablero, margen=0)
        dragDropBA = QTVarios.ListaPiezas(self, "k,q,r,b,n,p", self.tablero, margen=0)

        self.rbWhite = Controles.RB(self, _("White"), rutina=self.cambiaColor)
        self.rbBlack = Controles.RB(self, _("Black"), rutina=self.cambiaColor)

        self.cbWoo = Controles.CHB(self, _("White") + " O-O", True)
        self.cbWooo = Controles.CHB(self, _("White") + " O-O-O", True)
        self.cbBoo = Controles.CHB(self, _("Black") + " O-O", True)
        self.cbBooo = Controles.CHB(self, _("Black") + " O-O-O", True)

        lbEnPassant = Controles.LB(self, _("En passant") + ":")
        self.edEnPassant = Controles.ED(self).controlrx("(-|[a-h][36])").anchoFijo(30)

        self.edMovesPawn, lbMovesPawn = QTUtil2.spinBoxLB(self, 0, 0, 999, etiqueta=_("Halfmove clock"), maxTam=50)

        self.edFullMoves, lbFullMoves = QTUtil2.spinBoxLB(self, 1, 1, 999, etiqueta=_("Fullmove number"), maxTam=50)

        self.vars_scanner = Scanner.Scanner_vars(self.configuracion.carpetaScanners)

        self.lb_scanner = Controles.LB(self)

        pb_scanner_deduce = Controles.PB(self, _("Deduce"), self.scanner_deduce, plano=False)
        self.chb_scanner_flip = Controles.CHB(self, _("Flip the board"), False).capturaCambiado(self, self.scanner_flip)
        self.pb_scanner_learn = Controles.PB(self, _("Learn"), self.scanner_learn, plano=False)
        self.pb_scanner_learn_quit = Controles.PB(self, "", self.scanner_learn_quit).ponIcono(
            Iconos.Menos(), tamIcon=24
        )
        self.pb_scanner_learn_quit.ponToolTip(_("Remove last learned")).anchoFijo(24)

        self.sb_scanner_tolerance, lb_scanner_tolerance = QTUtil2.spinBoxLB(
            self, self.vars_scanner.tolerance, 3, 20, etiqueta=_("Deduction tolerance"), maxTam=50
        )
        self.sb_scanner_tolerance_learns, lb_scanner_tolerance_learns = QTUtil2.spinBoxLB(
            self, self.vars_scanner.tolerance_learns, 1, 6, etiqueta=_("Learning tolerance"), maxTam=50
        )

        self.chb_rem_ghost_deductions = Controles.CHB(self, _("Remove ghost deductions"), self.vars_scanner.rem_ghost)

        self.cb_scanner_select, lb_scanner_select = QTUtil2.comboBoxLB(self, [], None, _("OPR"))
        self.cb_scanner_select.capturaCambiado(self.scanner_change)
        pb_scanner_more = Controles.PB(self, "", self.scanner_more).ponIcono(Iconos.Mas())

        self.chb_scanner_ask = Controles.CHB(self, _("Ask before new capture"), self.vars_scanner.ask)

        self.li_scan_pch = []
        self.is_scan_init = False

        # LAYOUT -------------------------------------------------------------------------------------------
        hbox = Colocacion.H().control(self.rbWhite).espacio(15).control(self.rbBlack)
        gbColor = Controles.GB(self, _("Side to play"), hbox)

        ly = Colocacion.G().control(self.cbWoo, 0, 0).control(self.cbBoo, 0, 1)
        ly.control(self.cbWooo, 1, 0).control(self.cbBooo, 1, 1)
        gbEnroques = Controles.GB(self, _("Castling moves possible"), ly)

        ly = Colocacion.G()
        ly.controld(lbMovesPawn, 0, 0, 1, 3).control(self.edMovesPawn, 0, 3)
        ly.controld(lbEnPassant, 1, 0).control(self.edEnPassant, 1, 1)
        ly.controld(lbFullMoves, 1, 2).control(self.edFullMoves, 1, 3)
        gbOtros = Controles.GB(self, "", ly)

        lyT = (
            Colocacion.H()
            .relleno()
            .control(lb_scanner_tolerance)
            .espacio(5)
            .control(self.sb_scanner_tolerance)
            .relleno()
        )
        lyTL = (
            Colocacion.H()
            .relleno()
            .control(lb_scanner_tolerance_learns)
            .espacio(5)
            .control(self.sb_scanner_tolerance_learns)
            .relleno()
        )
        lyL = Colocacion.H().control(self.pb_scanner_learn).control(self.pb_scanner_learn_quit)
        lyS = Colocacion.H().control(lb_scanner_select).control(self.cb_scanner_select).control(pb_scanner_more)
        ly = Colocacion.V().control(self.chb_scanner_flip).control(pb_scanner_deduce).otro(lyL).otro(lyT).otro(lyTL)
        ly.control(self.chb_rem_ghost_deductions).otro(lyS)
        ly.control(self.chb_scanner_ask)
        self.gb_scanner = Controles.GB(self, _("Scanner"), ly)

        lyG = Colocacion.G()
        lyG.controlc(dragDropBA, 0, 0)
        lyG.control(self.tablero, 1, 0).control(self.lb_scanner, 1, 1)
        lyG.controlc(dragDropWB, 2, 0).controlc(self.gb_scanner, 2, 1, numFilas=4)
        lyG.controlc(gbColor, 3, 0)
        lyG.controlc(gbEnroques, 4, 0)
        lyG.controlc(gbOtros, 5, 0)

        layout = Colocacion.V()
        layout.controlc(self.tb)
        layout.otro(lyG)
        layout.margen(1)
        self.setLayout(layout)

        self.ultimaPieza = "P"
        self.piezas = self.tablero.piezas
        self.resetPosicion()
        self.ponCursor()

        self.lb_scanner.hide()
        self.pb_scanner_learn_quit.hide()
        self.gb_scanner.hide()

    def closeEvent(self, QCloseEvent):
        self.scanner_write()

    def cambiaColor(self):
        self.tablero.ponIndicador(self.rbWhite.isChecked())

    def save(self):
        self.actPosicion()
        siK = False
        sik = False
        for p in self.squares.values():
            if p == "K":
                siK = True
            elif p == "k":
                sik = True
        if siK and sik:
            self.wparent.setPosicion(self.position)
            self.scanner_write()
            if self.is_game:
                self.wparent.ponModo(MODO_PARTIDA)
            else:
                self.wparent.save()
        else:
            if not siK:
                QTUtil2.message_error(self, _("King") + "-" + _("White") + "???")
                return
            if not sik:
                QTUtil2.message_error(self, _("King") + "-" + _("Black") + "???")
                return

    def cancelar(self):
        self.scanner_write()
        if self.is_game:
            self.wparent.ponModo(MODO_PARTIDA)
        else:
            self.wparent.cancelar()

    def ponCursor(self):
        cursor = self.piezas.cursor(self.ultimaPieza)
        for item in self.tablero.escena.items():
            item.setCursor(cursor)
        self.tablero.setCursor(cursor)

    def cambiaPiezaSegun(self, pieza):
        ant = self.ultimaPieza
        if ant.upper() == pieza:
            if ant == pieza:
                pieza = pieza.lower()
        self.ultimaPieza = pieza
        self.ponCursor()

    def mueve(self, from_sq, to_sq):
        if from_sq == to_sq:
            return
        if self.squares.get(to_sq):
            self.tablero.borraPieza(to_sq)
        self.squares[to_sq] = self.squares.get(from_sq)
        self.squares.pop(from_sq, None)
        self.tablero.muevePieza(from_sq, to_sq)

        self.ponCursor()

    def dispatchDrop(self, from_sq, qbpieza):
        pieza = qbpieza[0]
        if self.squares.get(from_sq):
            self.borraCasilla(from_sq)
        self.ponPieza(from_sq, pieza)

    def borraCasilla(self, from_sq):
        self.squares[from_sq] = None
        self.tablero.borraPieza(from_sq)

    def creaCasilla(self, from_sq):
        menu = QtWidgets.QMenu(self)

        siK = False
        sik = False
        for p in self.squares.values():
            if p == "K":
                siK = True
            elif p == "k":
                sik = True

        li_options = []
        if not siK:
            li_options.append((_("King"), "K"))
        li_options.extend(
            [(_("Queen"), "Q"), (_("Rook"), "R"), (_("Bishop"), "B"), (_("Knight"), "N"), (_("Pawn"), "P")]
        )
        if not sik:
            li_options.append((_("King"), "k"))
        li_options.extend(
            [(_("Queen"), "q"), (_("Rook"), "r"), (_("Bishop"), "b"), (_("Knight"), "n"), (_("Pawn"), "p")]
        )

        for txt, pieza in li_options:
            icono = self.tablero.piezas.icono(pieza)

            accion = QtWidgets.QAction(icono, txt, menu)
            accion.key = pieza
            menu.addAction(accion)

        resp = menu.exec_(QtGui.QCursor.pos())
        if resp:
            pieza = resp.key
            self.ponPieza(from_sq, pieza)

    def ponPieza(self, from_sq, pieza):
        antultimo = self.ultimaPieza
        self.ultimaPieza = pieza
        self.repitePieza(from_sq)
        if pieza == "K":
            self.ultimaPieza = antultimo
        if pieza == "k":
            self.ultimaPieza = antultimo

        self.ponCursor()

    def repitePieza(self, from_sq):
        pieza = self.ultimaPieza
        if pieza in "kK":
            for pos, pz in self.squares.items():
                if pz == pieza:
                    self.borraCasilla(pos)
                    break
        if QtWidgets.QApplication.keyboardModifiers() == QtCore.Qt.ShiftModifier:
            if pieza.islower():
                pieza = pieza.upper()
            else:
                pieza = pieza.lower()
        self.squares[from_sq] = pieza
        pieza = self.tablero.creaPieza(pieza, from_sq)
        pieza.activa(True)

        self.ponCursor()

    def leeDatos(self):
        is_white = self.rbWhite.isChecked()
        en_passant = self.edEnPassant.texto().strip()
        if not en_passant:
            en_passant = "-"
        num_moves = self.edFullMoves.value()
        mov_pawn_capt = self.edMovesPawn.value()

        castles = ""
        for cont, pieza in ((self.cbWoo, "K"), (self.cbWooo, "Q"), (self.cbBoo, "k"), (self.cbBooo, "q")):
            if cont.isChecked():
                castles += pieza
        if not castles:
            castles = "-"
        return is_white, en_passant, num_moves, mov_pawn_capt, castles

    def actPosicion(self):
        self.position.is_white, self.position.en_passant, self.position.num_moves, self.position.mov_pawn_capt, self.position.castles = (
            self.leeDatos()
        )

    def setPosicion(self, position):
        self.position = position.copia()
        self.resetPosicion()

    def pegar(self):
        cb = QtWidgets.QApplication.clipboard()
        fen = cb.text()
        if fen:
            try:
                self.position.read_fen(str(fen))
                self.resetPosicion()
            except:
                pass

    def copiar(self):
        cb = QtWidgets.QApplication.clipboard()
        self.actPosicion()
        cb.setText(self.position.fen())

    def limpiaTablero(self):
        self.position.read_fen("8/8/8/8/8/8/8/8 w - - 0 1")
        self.resetPosicion()

    def inicial(self):
        self.position.set_pos_initial()
        self.resetPosicion()

    def resetPosicion(self):
        self.tablero.ponPosicion(self.position)
        self.squares = self.position.squares
        self.tablero.squares = self.squares
        self.tablero.activaTodas()

        if self.position.is_white:
            self.rbWhite.activa(True)
        else:
            self.rbBlack.activa(True)

        # Enroques permitidos
        castles = self.position.castles
        self.cbWoo.setChecked("K" in castles)
        self.cbWooo.setChecked("Q" in castles)
        self.cbBoo.setChecked("k" in castles)
        self.cbBooo.setChecked("q" in castles)

        # Otros
        self.edEnPassant.ponTexto(self.position.en_passant)
        self.edFullMoves.setValue(self.position.num_moves)
        self.edMovesPawn.setValue(self.position.mov_pawn_capt)

    def scanner(self):
        pos = QTUtil.escondeWindow(self.wparent)
        seguir = True
        if self.chb_scanner_ask.valor() and not QTUtil2.pregunta(
            None, _("Bring the window to scan to front"), label_yes=_("Accept"), label_no=_("Cancel"), si_top=True
        ):
            seguir = False
        if seguir:
            fich_png = self.configuracion.ficheroTemporal("png")
            if not self.is_scan_init:
                self.scanner_init()
                self.is_scan_init = True

            sc = Scanner.Scanner(self.configuracion.carpetaScanners, fich_png)
            sc.exec_()

            self.vars_scanner.read()
            self.vars_scanner.tolerance = self.sb_scanner_tolerance.valor()  # releemos la variable
            self.vars_scanner.tolerance_learns = min(
                self.sb_scanner_tolerance_learns.valor(), self.vars_scanner.tolerance
            )

            if os.path.isfile(fich_png) and Util.filesize(fich_png):
                self.scanner_read_png(fich_png)
                self.pixmap = QtGui.QPixmap(fich_png)
                tc = self.tablero.anchoCasilla * 8
                pm = self.pixmap.scaled(tc, tc)
                self.lb_scanner.ponImagen(pm)
                self.lb_scanner.show()
                self.gb_scanner.show()
                self.scanner_deduce()

        self.wparent.move(pos)
        self.setFocus()

    def scanner_read_png(self, fdb):
        self.im_scanner = Image.open(fdb)
        self.scanner_process()

    def scanner_process(self):
        im = self.im_scanner
        flipped = self.chb_scanner_flip.isChecked()
        w, h = im.size
        tam = w // 8
        dic = {}
        dic_color = {}
        for f in range(8):
            for c in range(8):
                if flipped:
                    fil = chr(49 + f)
                    col = chr(97 + 7 - c)
                else:
                    fil = chr(49 + 7 - f)
                    col = chr(97 + c)
                x = c * tam + 2
                y = f * tam + 2
                x1 = x + tam - 4
                y1 = y + tam - 4
                im_t = im.crop((x, y, x1, y1))
                pos = "%s%s" % (col, fil)
                dic[pos] = average_hash(im_t, hash_size=8)
                dic_color[pos] = (f + c) % 2 == 0
        self.dicscan_pos_hash = dic
        self.dic_pos_color = dic_color
        is_white_bottom = self.tablero.is_white_bottom
        if (is_white_bottom and flipped) or ((not is_white_bottom) and (not flipped)):
            self.tablero.rotaTablero()

    def scanner_flip(self):
        self.scanner_process()
        self.scanner_deduce()

    def scanner_deduce_base(self, extended):
        tolerance = self.sb_scanner_tolerance.valor()
        dic = {}
        for pos, hs in self.dicscan_pos_hash.items():
            pz = None
            dt = 99999999
            reg = None
            cl = self.dic_pos_color[pos]
            for piece, color, hsp in self.li_scan_pch:
                if cl == color:
                    dtp = hamming_distance(hs, hsp)
                    if dtp <= dt:
                        pz = piece
                        dt = dtp
                        reg = piece, color, hsp
            if pz and dt <= tolerance:
                if extended:
                    dic[pos] = pz, reg, dt
                else:
                    dic[pos] = pz
        return dic

    def scanner_deduce(self):
        self.actPosicion()
        fen = "8/8/8/8/8/8/8/8 w KQkq - 0 1"
        if not self.position.is_white:
            fen = fen.replace("w", "b")
        self.position.read_fen(fen)
        self.actPosicion()
        self.resetPosicion()
        dic = self.scanner_deduce_base(False)
        for pos, pz in dic.items():
            self.ponPieza(pos, pz)

    def scanner_learn(self):
        cp = Position.Position()
        cp.read_fen(self.tablero.fen_active())
        tolerance = self.sb_scanner_tolerance.valor()
        tolerance_learn = min(self.sb_scanner_tolerance_learns.valor(), tolerance)

        self.n_scan_last_added = len(self.li_scan_pch)
        dic_deduced_extended = self.scanner_deduce_base(True)

        for pos, pz_real in cp.squares.items():
            if pz_real:
                resp = dic_deduced_extended.get(pos)
                if resp is None:
                    pz_deduced = None
                    dt = 99
                else:
                    pz_deduced, reg_scan, dt = resp
                if (not pz_deduced) or (pz_real != pz_deduced) or dt > tolerance_learn:
                    color_celda = self.dic_pos_color[pos]
                    hs = self.dicscan_pos_hash[pos]
                    key = (pz_real, color_celda, hs)
                    self.li_scan_pch.append(key)

        if self.chb_rem_ghost_deductions.valor():
            for pos_a1h8, (pz_deduced, reg_scan, dt) in dic_deduced_extended.items():
                if cp.get_pz(pos_a1h8) is None:  # ghost
                    pz, color, hs = reg_scan
                    for pos_li, (xpz, xcolor, xhs) in enumerate(self.li_scan_pch):
                        if pz == xpz and color == xcolor and hs == xhs:
                            del self.li_scan_pch[pos_li]
                            break

        self.scanner_show_learned()

    def scanner_learn_quit(self):
        self.li_scan_pch = self.li_scan_pch[: self.n_scan_last_added]
        self.scanner_show_learned()

    def scanner_more(self):
        name = ""
        while True:
            liGen = []

            config = FormLayout.Editbox(_("Name"), ancho=120)
            liGen.append((config, name))

            resultado = FormLayout.fedit(
                liGen, title=_("New scanner"), parent=self, anchoMinimo=200, icon=Iconos.Scanner()
            )
            if resultado:
                accion, liGen = resultado
                name = liGen[0].strip()
                if name:
                    fich = os.path.join(self.configuracion.carpetaScanners, "%s.scn" % name)
                    if Util.exist_file(fich):
                        QTUtil2.message_error(self, _("This scanner already exists."))
                        continue
                    try:
                        with open(fich, "w") as f:
                            f.write("")
                        self.scanner_reread(name)
                        return
                    except:
                        QTUtil2.message_error(self, _("This name is not valid to create a scanner file."))
                        continue
            return

    def scanner_init(self):
        scanner = self.vars_scanner.scanner
        self.scanner_reread(scanner)

    def scanner_change(self):
        fich_scanner = self.cb_scanner_select.valor()
        self.vars_scanner.scanner = os.path.basename(fich_scanner)[:-4]
        self.scanner_read()

    def scanner_reread(self, label_default):
        dsc = self.configuracion.carpetaScanners
        lista = [fich for fich in os.listdir(dsc) if fich.endswith(".scn")]
        li = [(fich[:-4], os.path.join(dsc, fich)) for fich in lista]
        fich_default = None
        if not label_default:
            if li:
                label_default, fich_default = li[0]

        for label, fich in li:
            if label == label_default:
                fich_default = fich

        self.cb_scanner_select.rehacer(li, fich_default)
        self.cb_scanner_select.show()
        self.scanner_read()

    def scanner_read(self):
        self.li_scan_pch = []
        self.n_scan_last_save = 0
        self.n_scan_last_added = 0
        fich = self.cb_scanner_select.valor()
        if not fich:
            return
        if Util.filesize(fich):
            with open(fich) as f:
                for linea in f:
                    self.li_scan_pch.append(eval(linea.strip()))
        self.n_scan_last_save = len(self.li_scan_pch)
        self.n_scan_last_added = self.n_scan_last_save

        self.scanner_show_learned()

    def scanner_show_learned(self):
        self.pb_scanner_learn.ponTexto("%s (%d)" % (_("Learn"), len(self.li_scan_pch)))
        self.pb_scanner_learn_quit.setVisible(self.n_scan_last_added < len(self.li_scan_pch))

    def scanner_write(self):
        fich_scanner = self.cb_scanner_select.valor()
        if not fich_scanner:
            return

        tam = len(self.li_scan_pch)
        if tam > self.n_scan_last_save:
            with open(fich_scanner, "a") as q:
                for x in range(self.n_scan_last_save, tam):
                    q.write(str(self.li_scan_pch[x]).replace(" ", ""))
                    q.write("\n")
            self.n_scan_last_save = tam
            self.n_scan_last_added = tam

        self.vars_scanner.scanner = os.path.basename(fich_scanner)[:-4]
        self.vars_scanner.tolerance = self.sb_scanner_tolerance.valor()
        self.vars_scanner.tolerance_learns = self.sb_scanner_tolerance_learns.valor()
        self.vars_scanner.ask = self.chb_scanner_ask.valor()
        self.vars_scanner.rem_ghost = self.chb_rem_ghost_deductions.valor()
        self.vars_scanner.write()

    def keyPressEvent(self, event):
        k = event.key()

        if k == QtCore.Qt.Key_W:
            self.actPosicion()
            fen = self.position.fen()
            fich = "scanner.fns"
            with open(fich, "ab") as q:
                q.write(fen + "\n")
                QTUtil2.mensajeTemporal(self.parent(), _("Saved in %s") % fich, 0.3)

        elif k == QtCore.Qt.Key_D:
            self.scanner_deduce()

        event.ignore()


class WPGN(QtWidgets.QWidget):
    def __init__(self, wparent, game):
        self.game = game

        self.wparent = wparent
        self.configuracion = configuracion = Code.configuracion
        QtWidgets.QWidget.__init__(self, wparent)

        li_acciones = (
            (_("Save"), Iconos.Grabar(), self.save),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.wparent.cancelar),
            None,
            (_("Start position"), Iconos.Datos(), self.inicial),
            None,
            (_("Clear"), Iconos.Borrar(), self.limpia),
            None,
            (_("Take back"), Iconos.Atras(), self.atras),
            None,
        )

        self.tb = Controles.TBrutina(self, li_acciones, siTexto=False, tamIcon=20)

        config_board = configuracion.config_board("VOYAGERPGN", 24)
        self.tablero = Tablero.Tablero(self, config_board)
        self.tablero.crea()
        self.tablero.set_dispatcher(self.mueve_humano)
        Delegados.generaPM(self.tablero.piezas)

        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUMERO", _("N."), 35, centered=True)
        self.si_figurines_pgn = configuracion.x_pgn_withfigurines
        nAnchoColor = (self.tablero.ancho - 35 - 20) // 2
        o_columns.nueva(
            "BLANCAS", _("White"), nAnchoColor, edicion=Delegados.EtiquetaPGN(True if self.si_figurines_pgn else None)
        )
        o_columns.nueva(
            "NEGRAS", _("Black"), nAnchoColor, edicion=Delegados.EtiquetaPGN(False if self.si_figurines_pgn else None)
        )
        self.pgn = Grid.Grid(self, o_columns, siCabeceraMovible=False, siSelecFilas=True)
        self.pgn.setMinimumWidth(self.tablero.ancho)

        ly = Colocacion.V().control(self.tb).control(self.tablero)
        ly.control(self.pgn)
        ly.margen(1)
        self.setLayout(ly)

        self.tablero.ponPosicion(self.game.last_position)
        self.siguiente_jugada()

    def save(self):
        self.wparent.save()

    def limpia(self):
        self.game.li_moves = []
        self.tablero.ponPosicion(self.game.first_position)
        self.siguiente_jugada()

    def atras(self):
        n = len(self.game)
        if n:
            self.game.li_moves = self.game.li_moves[:-1]
            move = self.game.move(n - 2)
            if move:
                self.tablero.ponPosicion(move.position)
                self.tablero.ponFlechaSC(move.from_sq, move.to_sq)
            else:
                self.tablero.ponPosicion(self.game.first_position)
            self.siguiente_jugada()

    def inicial(self):
        self.wparent.ponModo(MODO_POSICION)

    def siguiente_jugada(self):
        self.tb.setAccionVisible(self.inicial, len(self.game) == 0)
        if self.game.is_finished():
            self.tablero.disable_all()
            return
        self.pgn.refresh()
        self.pgn.gobottom()
        self.tablero.activaColor(self.game.last_position.is_white)

    def mueve_humano(self, from_sq, to_sq, promotion=None):
        if not promotion and self.game.last_position.siPeonCoronando(from_sq, to_sq):
            promotion = self.tablero.peonCoronando(self.game.last_position.is_white)
            if promotion is None:
                return False

        siBien, mens, move = Move.dameJugada(self.game, self.game.last_position, from_sq, to_sq, promotion)

        if siBien:
            self.game.add_move(move)
            self.tablero.ponPosicion(move.position)
            self.tablero.ponFlechaSC(move.from_sq, move.to_sq)

            self.siguiente_jugada()
            return True
        else:
            return False

    def grid_num_datos(self, grid):
        n = len(self.game)
        if not n:
            return 0
        if self.game.siEmpiezaConNegras:
            n += 1
        if n % 2:
            n += 1
        return n // 2

    def grid_dato(self, grid, fila, oColumna):
        col = oColumna.clave
        if col == "NUMERO":
            return str(self.game.first_position.num_moves + fila)

        siIniBlack = self.game.siEmpiezaConNegras
        nJug = len(self.game)
        if fila == 0:
            w = None if siIniBlack else 0
            b = 0 if siIniBlack else 1
        else:
            n = fila * 2
            w = n - 1 if siIniBlack else n
            b = w + 1
        if b >= nJug:
            b = None

        def xjug(n):
            if n is None:
                return ""
            move = self.game.move(n)
            if self.si_figurines_pgn:
                return move.pgnFigurinesSP()
            else:
                return move.pgn_translated()

        if col == "BLANCAS":
            return xjug(w)
        else:
            return xjug(b)


class Voyager(QTVarios.WDialogo):
    def __init__(self, owner, is_game, game):

        titulo = _("Voyager 2") if is_game else _("Start position")
        icono = Iconos.Voyager() if is_game else Iconos.Datos()
        QTVarios.WDialogo.__init__(self, owner, titulo, icono, "voyager")
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.Window | QtCore.Qt.WindowStaysOnTopHint)

        self.is_game = is_game
        self.game = game
        self.resultado = None

        self.wPos = WPosicion(self, is_game, game)
        self.wPGN = WPGN(self, game)

        ly = Colocacion.V().control(self.wPos).control(self.wPGN).margen(0)
        self.setLayout(ly)

        self.ponModo(MODO_PARTIDA if self.is_game else MODO_POSICION)

        self.restore_video(siTam=False)

    def ponModo(self, modo):
        self.modo = modo
        if modo == MODO_POSICION:
            self.wPos.setPosicion(self.game.first_position)
            self.wPGN.setVisible(False)
            self.wPos.setVisible(True)
        else:
            self.wPos.setVisible(False)
            self.wPGN.setVisible(True)

    def setPosicion(self, position):
        self.game.first_position = position
        self.wPGN.limpia()

    def save(self):
        self.resultado = self.game.save() if self.is_game else self.game.first_position
        self.save_video()
        self.accept()

    def cancelar(self):
        self.save_video()
        self.reject()


def voyager_position(wowner, position, si_esconde: bool = True, wownerowner=None):
    pos_ownerowner = None
    pos = None
    if si_esconde:
        pos = QTUtil.escondeWindow(wowner)
        if wownerowner:
            pos_ownerowner = QTUtil.escondeWindow(wownerowner)
    game = Game.Game(ini_posicion=position)
    dlg = Voyager(wowner, False, game)
    resp = dlg.resultado if dlg.exec_() else None
    if si_esconde:
        if wownerowner:
            wownerowner.show()
            wownerowner.move(pos_ownerowner)
            QTUtil.refresh_gui()
            time.sleep(0.01)

        wowner.show()
        wowner.move(pos)
        QTUtil.refresh_gui()
        time.sleep(0.01)
    return resp


def voyagerPartida(wowner, game):
    pos = QTUtil.escondeWindow(wowner)
    dlg = Voyager(wowner, True, game)
    resp = dlg.resultado if dlg.exec_() else None
    wowner.move(pos)
    wowner.show()
    return resp
