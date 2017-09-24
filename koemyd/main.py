# vi:ts=4:sw=4:syn=python

import optparse

import koemyd.const

def main(argv):
    parser = optparse.OptionParser(
                description="%s, %s" % (koemyd.const.PROGRAM_NAME, koemyd.const.PROGRAM_DESC),
                    version="%s v%s" % (koemyd.const.PROGRAM_NAME, koemyd.const.VERSION),
                       prog=koemyd.const.PROGRAM_NAME, epilog="-- koaeH (118E 7E44)",
             )
    parser.set_defaults(mode="advanced")
    parser.parse_args(argv)

    from koemyd.daemon import Server
    daemon = koemyd.daemon.Server()
    daemon.start()
