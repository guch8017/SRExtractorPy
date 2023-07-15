import os
from typing import List, Optional
from logger import get_logger
from binary_reader import BinaryReader
from utils import bytes_to_hex_string, get_stable_hash

logger = get_logger('DesignIndexLoader')


class DesignConfigEntry:
    def __init__(self, hash_: int, size: int, offset: int, parent: Optional["FileEntry"] = None):
        self.hash = hash_
        self.size = size
        self.offset = offset
        self.parent = parent

    @classmethod
    def from_reader(cls, reader: BinaryReader, parent: "FileEntry") -> "DesignConfigEntry":
        hash_ = reader.read_b_int()
        size = reader.read_b_ulong()
        offset = reader.read_b_ulong()
        return cls(hash_, size, offset, parent)

    def __repr__(self):
        return f'[DesignConfigEntry {self.parent.filename}+0x{self.offset:x} Length: 0x{self.size:x}]'


class FileEntry:
    def __init__(self, hash_: int, filename: str, size: int, count: int):
        self.hash = hash_
        self.filename = filename
        self.size = size
        self.count = count
        self.chunks: List[DesignConfigEntry] = []

    @classmethod
    def from_reader(cls, reader: BinaryReader) -> "FileEntry":
        hash_ = reader.read_b_int()
        name = bytes_to_hex_string(reader.read_bytes(16)) + '.bytes'
        size = reader.read_b_ulong()
        count = reader.read_b_uint()
        ret = cls(hash_, name, size, count)
        for _ in range(count):
            ret.chunks.append(DesignConfigEntry.from_reader(reader, ret))
        reader.skip(1)
        return ret


class DesignIndexLoader:
    def __init__(self, path: str):
        path = os.path.abspath(path)
        self.file_entries: List[FileEntry] = []
        self.hash_map = {}
        self.dir_path = None
        if os.path.isdir(path):
            self.dir_path = path
            for f in os.listdir(path):
                if f.startswith('DesignV_'):
                    self._load(os.path.join(path, f))
                    break
            else:
                logger.error('DesignV_* file not found. '
                             'Please make sure the path is point to the DesignData folder. '
                             'You can also try to specific a file instead.')
                raise FileNotFoundError('DesignV_* file not found')
        elif os.path.isfile(path):
            if not os.path.basename(path).startswith('DesignV_'):
                logger.warning('The file provided starts with a wrong prefix. Parser will still try to parse it.')
            self.dir_path = os.path.dirname(path)
            self._load(path)
        else:
            logger.error('The path provided is neither a file nor a directory.')
            raise FileNotFoundError('The path provided is neither a file nor a directory.')

    def _load(self, path: str):
        logger.info(f'Loading design index from {os.path.basename(path)}...')
        self._reader = BinaryReader(path=path)
        file_cnt = self._reader.read_b_uint()
        for _ in range(file_cnt):
            self.file_entries.append(FileEntry.from_reader(self._reader))
        for f in self.file_entries:
            for c in f.chunks:
                self.hash_map[c.hash] = c
        logger.info(f'Loaded {len(self.file_entries)} files')
        logger.info(f'Loaded {len(self.hash_map)} entries')

    def get_entry(self, hash_: int = None, name: str = None) -> Optional[DesignConfigEntry]:
        if (not hash_ and not name) or (hash_ and name):
            raise ValueError('Only one of hash_ and name should be provided')
        if not hash_:
            hash_ = get_stable_hash(name)
        entry = self.hash_map.get(hash_)
        if entry is None:
            logger.warning(f'Can\'t find entry for hash {hash_} ({name})')
        return entry

    def get_reader(self, hash_: int = None, name: str = None) -> Optional[BinaryReader]:
        entry = self.get_entry(hash_, name)
        if not entry:
            return None
        with open(os.path.join(self.dir_path, entry.parent.filename), 'rb') as f:
            buffer = f.read()
        return BinaryReader(buffer=buffer[entry.offset:entry.offset + entry.size])

    def dump(self, path: str, hash_: int = None, name: str = None):
        reader = self.get_reader(hash_, name)
        if not reader:
            return
        with open(path, 'wb') as f:
            f.write(reader.read_all())
