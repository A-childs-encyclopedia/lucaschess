import os
import shutil

import Code
from Code.QT import Colocacion
from Code.QT import Columnas
from Code.QT import Delegados
from Code.QT import Grid
from Code.QT import Iconos
from Code.QT import QTUtil
from Code.QT import QTUtil2
from Code.QT import QTVarios
from Code import Usuarios
from Code.QT import FormLayout


class WUsuarios(QTVarios.WDialogo):
    def __init__(self, procesador):

        self.configuracion = procesador.configuracion

        self.leeUsuarios()

        titulo = _("Usuarios")
        icono = Iconos.Usuarios()
        extparam = "users"
        QTVarios.WDialogo.__init__(self, procesador.main_window, titulo, icono, extparam)

        # Toolbar
        li_acciones = (
            (_("Accept"), Iconos.Aceptar(), self.aceptar),
            None,
            (_("Cancel"), Iconos.Cancelar(), self.cancelar),
            None,
            (_("New"), Iconos.Nuevo(), self.nuevo),
            None,
            (_("Remove"), Iconos.Borrar(), self.borrar),
            None,
        )
        tb = QTVarios.LCTB(self, li_acciones)

        # Lista
        o_columns = Columnas.ListaColumnas()
        o_columns.nueva("NUMERO", _("N."), 40, centered=True)
        o_columns.nueva("USUARIO", _("User"), 140, edicion=Delegados.LineaTextoUTF8())
        # o_columns.nueva("PASSWORD", _("Password"), 100, edicion=Delegados.LineaTextoUTF8(siPassword=True))

        self.grid = Grid.Grid(self, o_columns, siEditable=True)

        # Layout
        layout = Colocacion.V().control(tb).control(self.grid).margen(3)
        self.setLayout(layout)

        self.grid.gotop()
        self.grid.setFocus()

        self.siPlay = False

        self.register_grid(self.grid)

        if not self.restore_video():
            self.resize(310, 400)

    def leeUsuarios(self):
        self.liUsuarios = Usuarios.Usuarios().list_users
        if not self.liUsuarios:
            usuario = Usuarios.User()
            usuario.number = 0
            usuario.password = ""
            self.liUsuarios = [usuario]

        main = self.liUsuarios[0]
        main.name = self.configuracion.x_player
        # Para que al pedir la password siempre en el idioma del main en principio solo hace falta el password pero por si acaso se cambia de opinion
        main.trlucas = Code.lucas_chess
        main.trusuario = _("User")
        main.trpassword = _("Password")
        main.traceptar = _("Accept")
        main.trcancelar = _("Cancel")

    def cancelar(self):
        self.save_video()
        self.reject()

    def nuevo(self):

        li = []
        for usuario in self.liUsuarios:
            li.append(usuario.number)

        # plantilla = self.configuracion.carpetaUsers + "/%d"
        number = 1
        while number in li:  # or os.path.isdir(plantilla % number):
            number += 1

        usuario = Usuarios.User()
        usuario.name = _X(_("User %1"), str(number))
        usuario.number = number
        usuario.password = ""

        self.liUsuarios.append(usuario)
        self.grid.refresh()
        self.grid.goto(len(self.liUsuarios) - 1, 1)
        self.grid.setFocus()

    def aceptar(self):
        self.grid.goto(len(self.liUsuarios) - 1, 1)
        self.grid.setFocus()
        self.save_video()
        Usuarios.Usuarios().save_list(self.liUsuarios)
        self.accept()

    def borrar(self):
        fila = self.grid.recno()
        if fila > 0:
            usuario = self.liUsuarios[fila]
            carpeta = "%s/users/%d/" % (self.configuracion.carpeta, usuario.number)
            if os.path.isdir(carpeta):
                if QTUtil2.pregunta(self, _("Do you want to remove all data of this user?")):
                    shutil.rmtree(carpeta)
            del self.liUsuarios[fila]
            self.grid.refresh()
            self.grid.setFocus()

    def grid_num_datos(self, grid):
        return len(self.liUsuarios)

    def grid_setvalue(self, grid, fila, columna, valor):
        campo = columna.clave
        valor = valor.strip()
        usuario = self.liUsuarios[fila]
        if campo == "USUARIO":
            if valor:
                usuario.name = valor
            else:
                QTUtil.beep()
        # else:
        #     usuario.password = valor

    def grid_dato(self, grid, fila, oColumna):
        key = oColumna.clave
        usuario = self.liUsuarios[fila]
        if key == "NUMERO":
            return str(usuario.number) if usuario.number else "-"
        elif key == "USUARIO":
            return usuario.name
        # if key == "PASSWORD":
        #     return "x" * len(usuario.password)


def editaUsuarios(procesador):
    w = WUsuarios(procesador)
    if w.exec_():
        pass


def setPassword(procesador):
    configuracion = procesador.configuracion

    npos = 0
    user = configuracion.user
    liUsuarios = Usuarios.Usuarios().list_users
    if user:
        number = int(user)
        for n, usu in enumerate(liUsuarios):
            if usu.number == number:
                npos = n
                break
        if npos == 0:
            return
    else:
        if not liUsuarios:
            usuario = Usuarios.User()
            usuario.number = 0
            usuario.password = ""
            usuario.name = configuracion.x_player
            liUsuarios = [usuario]

    usuario = liUsuarios[npos]

    while True:
        liGen = [FormLayout.separador]

        config = FormLayout.Editbox(_("Current"), ancho=120, siPassword=True)
        liGen.append((config, ""))

        config = FormLayout.Editbox(_("New"), ancho=120, siPassword=True)
        liGen.append((config, ""))

        config = FormLayout.Editbox(_("Repeat"), ancho=120, siPassword=True)
        liGen.append((config, ""))

        resultado = FormLayout.fedit(
            liGen, title=_("Set password"), parent=procesador.main_window, icon=Iconos.Password()
        )

        if resultado:
            previa, nueva, repite = resultado[1]

            error = ""
            if previa != usuario.password:
                error = _("Current password is not correct")
            else:
                if nueva != repite:
                    error = _("New password and repetition are not the same")

            if error:
                QTUtil2.message_error(procesador.main_window, error)

            else:
                usuario.password = nueva
                Usuarios.Usuarios().save_list(liUsuarios)
                return
