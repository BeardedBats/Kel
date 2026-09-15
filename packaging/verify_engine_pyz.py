"""Gate 0 provenance (structural equality): every kel.* module embedded in a built
KelEngine.exe must be structurally identical to the current Kel-Prototype source.
(Value-based canon() equality; the earlier marshal-digest variant is unreliable
because marshal output depends on string interning state.)"""
import marshal, sys, types
from pathlib import Path
from PyInstaller.archive.readers import CArchiveReader

SRC = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else (Path(__file__).resolve().parent.parent / 'runtime' / 'kel')

def canon(code):
    consts = []
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            consts.append(canon(const))
        elif isinstance(const, (str, bytes, int, float, complex, bool, type(None), tuple, frozenset)):
            consts.append(const)
        else:
            consts.append(repr(const))
    return (code.co_code, tuple(code.co_names), tuple(code.co_varnames),
            code.co_argcount, code.co_kwonlyargcount, tuple(consts))

exe = sys.argv[1]
c = CArchiveReader(exe)
z = c.open_embedded_archive('PYZ.pyz')
kel_mods = sorted(n for n in z.toc if n == 'kel' or n.startswith('kel.'))
print('kel modules in PYZ:', len(kel_mods))
print('module list:', ', '.join(kel_mods))
ok, mismatch, missing = [], [], []
for name in kel_mods:
    rel = name.split('.', 1)[1].replace('.', '/') if '.' in name else '__init__'
    src_file = SRC / (rel + '.py')
    if not src_file.exists():
        missing.append(name)
        continue
    e = z.extract(name)
    if isinstance(e, bytes):
        e = marshal.loads(e)
    s = compile(src_file.read_bytes(), name, 'exec')
    (ok if canon(e) == canon(s) else mismatch).append(name)
print('matched:', len(ok))
print('MISMATCH:', mismatch)
print('no source file:', missing)
print('RESULT:', 'OK' if not mismatch and not missing else 'REVIEW')
