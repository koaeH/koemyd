# vi:ts=4:sw=4:syn=python

import re
import errno

class KConfigParser(dict):
    K_RE_C = re.compile(r"^\s*(#.*)?$")
    K_RE_S = re.compile(r"^\s*\[([^\]]*)\]")
    K_RE_O = re.compile(r"^\s*(?P<k>[^=]+)(=(?P<v>.*))?")

    VI_M_L = "# vi:ts=2:sw=2:fenc=ascii:syn=kconf:backup"

    def __init__(self, kconf_file_path):
        self.kconf_file_path = kconf_file_path
        self.__parser = self.__cr_parser()
        self.__parser.next()

        try:
            with open(kconf_file_path) as f:
                for l_n, l_s in enumerate(f.readlines()):
                    self.__parser.send((l_n + 1, l_s))
        except EnvironmentError as e:
            if e.errno not in [errno.ENOENT]:
                raise

    def __cr_parser(self):
        while 1:
            l_n, l_s = (yield)
            if not self.K_RE_C.match(l_s):
                m_s = self.K_RE_S.match(l_s)
                if m_s:
                    s = m_s.group(1)
                    if l_s[m_s.end():].strip():
                        raise KConfigParserError("%d:%s:syntax error" % (l_n, s))

                    if not s in self: self[s] = KConfigSection(s)

                    continue # as s is not k, v

                m_o = self.K_RE_O.match(l_s)
                if m_o:
                    k = m_o.group('k').rstrip()
                    v = m_o.group('v')
                    if v:
                        v = v.lstrip()
                        while v.endswith(('\\', '\\+', '\\&')):
                            _, l_s = (yield) # no k if EOF is reached on multi
                            if v[-1] == '&': l_s = re.sub(r"^\s+", str(), l_s)
                            if v[-1] == '+': l_s = re.sub(r"^\s+",   " ", l_s)
                            v = re.sub(r"\\[+&]?$", "", v) + l_s.rstrip()

                    try: self[s][k] = v
                    except NameError:
                        raise KConfigParserError("%d:%s:option before a section" % (l_n, k))

    def __getitem__(self, k):
        try: return super(KConfigParser, self).__getitem__(k)
        except KeyError:
            raise MissingSectionError("%s:no section" % k)

    def save(self):
        with open(self.kconf_file_path, 'w') as f:
            f.write("%s\n" % self.VI_M_L)
            for s in sorted(self.keys()):
                f.write("\n[%s]\n" % s)
                for k, v in sorted(self[s].items()):
                    if v:
                        f.write("%s = %s\n" % (k,v))
                    else:
                        f.write("%s\n" % k)

class KConfigParserError(Exception): pass

class MissingSectionError(KConfigParserError): pass

class KConfigSection(dict):
    def __init__(self, name): self.__name = name
    def __getitem__(self, k):
        try: return super(KConfigSection, self).__getitem__(k)
        except KeyError:
            raise MissingOptionError(
                "%s:%s:no such option" % (self.__name, k)
            )

class MissingOptionError(KConfigParserError): pass
