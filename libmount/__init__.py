import ctypes
import functools

_libmount = ctypes.cdll.LoadLibrary("libmount.so")

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
                    _libmount.mnt_fs_set_fs_options(self._fs, new_value)
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
            return self
            
        def _fs_attrib(get_name, set_name):
            def _get(self):
                return ctypes.string_at(getattr(_libmount, get_name)(self._fs))
            def _set(self, value):
                getattr(_libmount, set_name)(ctypes.c_char_p(value))
            return property(_get, _set)
        source = _fs_attrib('mnt_fs_get_source', 'mnt_fs_set_source')
        target = _fs_attrib('mnt_fs_get_target', 'mnt_fs_set_target')
        fstype = _fs_attrib('mnt_fs_get_fstype', 'mnt_fs_set_fstype')
        del _fs_attrib
        
        def _get_options(self):
            if not hasattr(self, '_options'):
                self._options = FilesystemTable.Options(self._fs)
            return self._options
        def _set_options(self, value):
            value = ctypes.c_char_p(value) if value else 0
            _libmount.mnt_fs_set_fs_options(self._fs, value)
            del self._options
            
        options = property(_get_options)
        
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

    def __init__(self, filename=None):
        self._table, self._lock = None, None
        self._filename = filename or self.DEFAULT_FILENAME

    def __enter__(self):
        self._lock = _libmount.mnt_new_lock(0, 0)
        self._table = _libmount.mnt_new_table_from_file(self._filename)
        if not _libmount.mnt_table_parse_file(self._table):
            raise Exception("Could not parse %s" % self.filename)
        self._get_fss()
        return self

    def __exit__(self,exc_type, exc_value, traceback):
        _libmount.mnt_free_table(self._table)
        _libmount.mnt_free_lock(self._lock)
        self._table, self._lock = None, None
    
    def _get_fss(self):
        fs, mnt_iter = ctypes.c_void_p(), _libmount.mnt_new_iter()
        try:
            while _libmount.mnt_table_next_fs(self._table, mnt_iter, ctypes.byref(fs)) == 0:
                self.append(self.Filesystem._from_existing(fs.value))
        finally:
            _libmount.mnt_free_iter(mnt_iter)
    
    def save(self):
        _libmount.mnt_table_update_file(self._table)
