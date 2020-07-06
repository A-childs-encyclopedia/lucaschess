import os

import Code

from Code.Engines import Engines


def read_engines(folder_engines):
    dic_engines = {}

    def mas(clave, autor, version, url, exe, elo):
        path_exe = os.path.join(folder_engines, clave, exe)
        engine = Engines.Engine(clave, autor, version, url, path_exe)
        engine.elo = elo
        dic_engines[clave] = engine
        return engine

    mas("andscacs", "Daniel José Queraltó", "0.9532n", "http://www.andscacs.com/", "andscacs", 3240)

    mas("cheng", "Martin Sedlák", "4 ver 0.39", "http://www.vlasak.biz/cheng", "cheng4_linux_x64", 2750)

    mas("cinnamon", "Giuseppe Cannella", "1.2b", "http://cinnamonchess.altervista.org/", "cinnamon_1.2b-generic", 1930)

    cm = mas("critter", "Richard Vida", "1.6a", "http://www.vlasak.biz/critter/", "critter-16a-64bit", 3091)
    cm.ordenUCI("Threads", "1")
    cm.ponMultiPV(20, 100)

    cm = mas("clarabit", "Salvador Pallares Bejarano", "1.00", "http://sapabe.googlepages.com", "clarabit_100_x64_linux", 2058)
    cm.ordenUCI("OwnBook", "false")
    cm.ordenUCI("Ponder", "false")

    cm = mas("komodo", "Don Dailey, Larry Kaufman", "11.01", "http://komodochess.com/", "Linux/komodo-11.01-linux", 3240)
    cm.ordenUCI("Ponder", "false")
    cm.ordenUCI("Hash", "32")
    cm.ponMultiPV(20, 218)

    cm = mas("stockfish", "Tord Romstad, Marco Costalba, Joona Kiiski", "11", "http://stockfishchess.org/", "Linux/stockfish_20011801_x64", 3300)
    cm.ordenUCI("Ponder", "false")
    cm.ordenUCI("Hash", "64")
    cm.ordenUCI("Threads", "1")
    cm.ponMultiPV(20, 500)

    mas("greko", "Vladimir Medvedev", "10.2", "http://sourceforge.net/projects/greko", "Linux/GreKo-102-64-ja", 2480)

    cm = mas("fruit", "Fabien Letouzey", "2.3.1", "http://www.fruitchess.com/", "Fruit-2-3-1-Linux", 2784)
    cm.ordenUCI("Hash", "32")
    cm.ponMultiPV(20, 256)

    mas("discocheck", "Lucas Braesch", "5.2.1", "https://github.com/lucasart/", "discocheck_5.2.1_x86-64", 2700)

    cm = mas("gaviota", "Miguel A. Ballicora", "1.0", "https://sites.google.com/site/gaviotachessengine", "gaviota-1.0-linux64", 2548)
    cm.ordenUCI("Log", "false")

    cm = mas("godel", "Juan Manuel Vazquez", "4.4.5", "https://sites.google.com/site/godelchessengine", "Godel64", 2814)
    cm.ordenUCI("Ponder", "false")
    cm.name = "Gödel 4.4.5"

    cm = mas("daydreamer", "Aaron Becker", "1.75 JA", "http://github.com/AaronBecker/daydreamer/downloads", "daydreamer-175-32-ja", 2670)

    cm = mas("glaurung", "Tord RomsTad", "2.2 JA", "http://www.glaurungchess.com/", "glaurung-64", 2765)
    cm.ordenUCI("Ponder", "false")
    cm.ponMultiPV(20, 500)

    cm = mas("gnuchess", "Chua Kong Sian,Stuart Cracraft,Lukas Geyer,Simon Waters,Michael Van den Bergh", "5.50", "http://www.gnu.org/software/chess/", "gnuchess-5.50-32", 2700)
    cm.ordenUCI("Ponder", "false")

    cm = mas("pawny", "Mincho Georgiev", "1.2", "http://pawny.netii.net/", "linux/pawny_1.2.x64", 2550)

    cm = mas("rocinante", "Antonio Torrecillas", "2.0", "http://sites.google.com/site/barajandotrebejos/", "rocinante-64", 1800)

    cm = mas("simplex", "Antonio Torrecillas", "0.98", "http://sites.google.com/site/barajandotrebejos/", "simplex-098-32-ja", 2396)

    cm = mas("texel", "Peter Österlund", "1.06", "http://web.comhem.se/petero2home/javachess/index.html#texel", "texel64", 2900)

    cm = mas("irina", "Lucas Monge", "0.15", "https://github.com/lukasmonk/irina", "irina", 1200)

    cm = mas("rodentII", "Pawel Koziol", "0.9.64", "http://www.pkoziol.cal24.pl/rodent/rodent.htm", "rodentII", 2912)
    cm.ordenUCI("Hash", "64")

    cm = mas("honey", "Michael Byrne", f"XI-r3 64bit", "https://github.com/MichaelB7/Stockfish/tree/honey", f"Honey-XI-r3", 3300)
    cm.ordenUCI("Hash", "64")
    cm.ponMultiPV(20, 256)

    cm = mas("zappa", "Anthony Cozzie", "1.1", "http://www.acoz.net/zappa/", "zappa.exe", 2614)

    return dic_engines


def dict_engines_fixed_elo(folder_engines):
    d = read_engines(folder_engines)
    dic = {}
    for nm, desde, hasta in (
        ("rodent", 600, 2600),
        ("amyan", 1000, 2400),
        ("honey", 1000, 2900),
        ("rhetoric", 1300, 2600),
        ("cheng", 800, 2500),
        ("greko", 1600, 2400),
        ("hamsters", 1000, 2000),
        ("rybka", 1200, 2400),
        ("ufim", 700, 2000),
        ("delfi", 1000, 1000),
        ("spike", 1100, 2500),
    ):
        for elo in range(desde, hasta + 100, 100):
            cm = d[nm].clona()
            if elo not in dic:
                dic[elo] = []
            cm.ordenUCI("UCI_Elo", str(elo))
            cm.ordenUCI("UCI_LimitStrength", "true")
            cm.name += " (%d)" % elo
            cm.clave += " (%d)" % elo
            dic[elo].append(cm)
    return dic
