import os
import sys
import Code
from Code import Util
from Code import Procesador
from Code.Sound import Sound
from Code.QT import Gui

from Code.Constantes import *

if Code.DEBUG:
    prlk("DEBUG " * 20 + "\n")


def init():
    if not Code.DEBUG:
        sys.stderr = Util.Log("bug.log")

    main_procesador = Procesador.Procesador()
    main_procesador.set_version(Code.VERSION)
    run_sound = Sound.RunSound()
    resp = Gui.run_gui(main_procesador)
    run_sound.close()
    # Added by GON
    main_procesador.desactivarDGT()
    # ------------
    main_procesador.pararMotores()
    main_procesador.kibitzers_manager.close()

    if resp == OUT_REINIT:
        if sys.argv[0].endswith(".py"):
            exe = os.path.abspath(sys.argv[0])
        else:
            exe = "LucasR.exe" if Code.isWindows else "LucasR"
        Code.startfile(exe)
