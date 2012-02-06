import ctypes

_libc = ctypes.cdll.LoadLibrary("libc.so.6")

# Simple wrapper around mount(2) and umount(2).
# Not thoroughly tested, and not very talkative.

class FLAGS:
    def __new__(self):
        raise NotImplementedError("This class is non-instantiable.")

    def flag_bits(count):
        flag = 1
        for i in range(count):
            yield flag
            flag <<= 1
    
    (
        MS_RDONLY,      #  0
        MS_NOSUID,      #  1
        MS_NODEV,       #  2
        MS_NOEXEC,      #  3
        MS_SYNCHRONOUS, #  4
        MS_REMOUNT,     #  5
        MS_MANDLOCK,    #  6
        MS_DIRSYNC,     #  7
        _, _,           # SKIP 8, 9
        MS_NOATIME,     # 10
        MS_NODIRATIME,  # 11
        MS_BIND,        # 12
        MS_MOVE,        # 13
        MS_REC,         # 14
        MS_SILENT,      # 15
        MS_POSIXACL,    # 16
        MS_UNBINDABLE,  # 17
        MS_PRIVATE,     # 18
        MS_SLAVE,       # 19
        MS_SHARED,      # 20
        MS_RELATIME,    # 21
        MS_KERNMOUNT,   # 22
        MS_I_VERSION,   # 23
        MS_STRICTATIME, # 24
        _, _, _, _, _,  # SKIP 25-29
        MS_ACTIVE,      # 30
        MS_NOUSER,      # 31
    ) = flag_bits(32)
    
    del flag_bits, _
    
    MS_MGC_VAL = 0xc0ed0000
    MS_MGC_MSK = 0xffff0000

def mount(source, target, fstype, flags=0, data=None):
    flags = (flags & FLAGS.MS_MGC_MSK) | FLAGS.MS_MGC_VAL
    
    result = _libc.mount(ctypes.c_char_p(source),
                         ctypes.c_char_p(target),
                         ctypes.c_char_p(fstype),
                         flags,
                         ctypes.c_char_p(data) if data is not None else 0)
    
    if result != 0:
        raise OSError(ctypes.get_errno())

def umount(target):
    result = _libc.umount(ctypes.c_char_p(target))

    if result != 0:
        raise OSError(ctypes.get_errno())