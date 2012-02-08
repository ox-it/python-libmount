import ctypes
import functools
import os

__all__ = ['FilesystemTable']

libnames = ('libmount.so', 'libmount.so.1')
for libname in libnames:
    try:
        _libmount = ctypes.cdll.LoadLibrary(libname)
    except OSError:
        continue
    break
else:
    raise ImportError("Could not find libmount shared object. Is libmount installed?")

class FilesystemTable(list):
    class Options(set):
        """A sub-type of set for maintaining filesystem options."""
        def __init__(self, fs):
            self._fs = fs
            options_ptr = _libmount.mnt_fs_get_fs_options(self._fs)
            set.__ior__(self, set(ctypes.string_at(options_ptr).split(',') if options_ptr else []))

        def __getattribute__(self, name):
            """Wraps every set method to also update the underlying fs struct."""
            attr = super(FilesystemTable.Options, self).__getattribute__(name)
            if callable(attr):
                @functools.wraps(attr)
                def f(*args, **kwargs):
                    retvalue = attr(*args, **kwargs)
                    new_value = ctypes.c_char_p(','.join(self)) if self else 0
                    _libmount.mnt_fs_set_options(self._fs, new_value)
                    return retvalue
                return f
            return attr

    class Filesystem(object):
        def __init__(self, source, target, fstype, options=()):
            self._fs = _libmount.mnt_new_fs()
            self.source, self.target, self.fstype = source, target, fstype
            self._in_table = False

        def __del__(self):
            if not self._in_table:
                _libmount.mnt_free_fs(self._fs)

        @classmethod
        def _from_existing(cls, fs):
            self = super(cls, cls).__new__(cls)
            self._fs = fs
            self._in_table = True
            self._editable = True

            # Cache properties
            self.source, self.target, self.fstype, self.options

            return self
        
        def mutable_check(self):
            if self._fs is None:
                raise IOError("This Filesystem is now immutable as the underlying table has been closed.")

        def _fs_attrib(cache_name, get_name, set_name):
            def _get(self):
                if not hasattr(self, cache_name):
                    self.mutable_check()
                    addr = getattr(_libmount, get_name)(self._fs)
                    setattr(self, cache_name, ctypes.string_at(addr) if addr else None)
                return getattr(self, cache_name)
            def _set(self, value):
                self.mutable_check()
                setattr(self, cache_name, value)
                getattr(_libmount, set_name)(ctypes.c_char_p(value))
            return property(_get, _set)
        source = _fs_attrib('_source', 'mnt_fs_get_source', 'mnt_fs_set_source')
        target = _fs_attrib('_target', 'mnt_fs_get_target', 'mnt_fs_set_target')
        fstype = _fs_attrib('_fstype', 'mnt_fs_get_fstype', 'mnt_fs_set_fstype')
        del _fs_attrib

        def _get_options(self):
            if not hasattr(self, '_options'):
                self.mutable_check()
                self._options = FilesystemTable.Options(self._fs)
            return self._options
        def _set_options(self, value):
            self.mutable_check()
            value = ctypes.c_char_p(','.join(value)) if value else 0
            _libmount.mnt_fs_set_options(self._fs, value)
            del self._options
        options = property(_get_options, _set_options)

        def __unicode__(self):
            return "%s on %s type %s (%s)" % (self.source,
                                              self.target,
                                              self.fstype,
                                              ','.join(self.options))
        __repr__ = __unicode__

        def as_dict(self):
            return {'source': self.source,
                    'target': self.target,
                    'fstype': self.fstype,
                    'options': self.options}

    DEFAULT_FILENAME = '/etc/fstab'

    def __init__(self, filename=None, readonly=False):
        self._table, self._lock = None, None
        self._filename = filename or self.DEFAULT_FILENAME
        self._depth = 0 # To handle multiply-nested with blocks

        if readonly:
            with self: pass

    def __enter__(self):
        if not self._depth:
            self._lock = _libmount.mnt_new_lock(0, 0)
            self._table = _libmount.mnt_new_table_from_file(self._filename)
            if not _libmount.mnt_table_parse_file(self._table):
                raise Exception("Could not parse %s" % self.filename)
            self._get_fss()
        self._depth += 1
        return self

    def __exit__(self,exc_type, exc_value, traceback):
        self._depth -= 1
        if not self._depth:
            _libmount.mnt_free_table(self._table)
            _libmount.mnt_free_lock(self._lock)
            self._table, self._lock = None, None

            # The entries in the table will have been freed by the above call to
            # mnt_free_table. If we don't do this and someone tries to modify the
            # filesystem, segfaults might ensue.
            for fs in self:
                fs._fs = None

    def _get_fss(self):
        fs, mnt_iter = ctypes.c_void_p(), _libmount.mnt_new_iter()
        try:
            while _libmount.mnt_table_next_fs(self._table, mnt_iter, ctypes.byref(fs)) == 0:
                self.append(self.Filesystem._from_existing(fs.value))
        finally:
            _libmount.mnt_free_iter(mnt_iter)

    def find_fs_containing(self, path):
        match = None
        for fs in self:
            if not os.path.relpath(path, fs.target).startswith('..'):
                if not match or len(fs.target) > len(match.target):
                    match = fs
        return match
    def find_source(self, source):
        for fs in self:
            if fs.source == source:
                return fs
        raise ValueError("Could not find filesystem with source '%s'" % source)
    def find_target(self, target):
        for fs in self:
            if fs.target == target:
                return fs
        raise ValueError("Could not find filesystem with target '%s'" % target)

    def as_list(self):
        with self:
            return list(self)

    def save(self):
        _libmount.mnt_table_update_file(self._table)


def get_fstab_readonly():
    return FilesystemTable('/etc/fstab', readonly=True)
def get_current_mounts():
    return FilesystemTable('/proc/mounts', readonly=True)