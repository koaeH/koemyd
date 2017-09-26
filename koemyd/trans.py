# vi:ts=4:sw=4:syn=python

import koemyd.util
import koemyd.const
import koemyd.struct

class Coder(object):
    def __init__(self, k_f=False): self.keep_feeding = k_f

    def feed(self, data): raise NotImplementedError

class CoderException(Exception): pass

class CoderError(Exception): pass

class ChunkCoder(Coder):
    def __init__(self):
        super(ChunkCoder, self).__init__(k_f=True)

        self._chunk = koemyd.struct.HTTPChunk()
        self._chunk_queue = list()
        self._chunks = list()

        self.cache = str()

    @property
    def body(self): return str().join([c.data for c in self._chunks])

    def flush(self):
        chunks = self._chunk_queue
        self._chunk_queue = []
        return chunks

class ChunksCodedException(Exception): pass

class ChunkDecoder(ChunkCoder):
    def __init__(self):
        super(ChunkDecoder, self).__init__()

        self.__decoder = self.__cr_decoder()

        self.__decoder.next()

    def __cr_decoder(self):
        self.cache = (yield)

        while self.keep_feeding or self.cache:
            while koemyd.const.HTTP_CRLF not in self.cache: self.cache += (yield)

            s_i = self.cache.index(koemyd.const.HTTP_CRLF)
            s_s = self.cache[:s_i]

            self.cache = self.cache[s_i + 2:] # HTTP_CRLF

            try:
                self._chunk.size = long(s_s, 16)
            except ValueError:
                raise ChunkDecoderError("chunk-size:could not parse")

            if 0 == self._chunk.size: # i.e., last-chunk
                self._chunk_queue.append(self._chunk)

                return

            while len(self.cache) < (self._chunk.size + 2): self.cache += (yield)

            self._chunk.data = self.cache[:self._chunk.size]
            self.cache = self.cache[self._chunk.size + 2:]
            self._chunk_queue.append(self._chunk) # next

            self._chunk = koemyd.struct.HTTPChunk()

    def feed(self, c_data=str()):
        try: self.__decoder.send(c_data)
        except StopIteration:
            self.keep_feeding = False

        if self._chunk_queue:
            raise ChunksDecodedException

class ChunksDecodedException(ChunksCodedException): pass

class ChunkDecoderError(CoderError): pass

class ChunkEncoder(ChunkCoder):
    def __init__(self):
        super(ChunkEncoder, self).__init__()

    def __encode(self, d):
        if d:
            self._chunk.size = len(d)
            self._chunk.data = str(d)

        self._chunk_queue.append(self._chunk)

        if d: self._chunk = koemyd.struct.HTTPChunk()
        else:
            self.keep_feeding = False

    def feed(self, r_data=str()):
        if self.keep_feeding:
            self.__encode(r_data)

            if self._chunk_queue:
                raise ChunkEncodedException

class ChunkEncodedException(ChunksCodedException): pass

class ChunkEncoderError(CoderError): pass
