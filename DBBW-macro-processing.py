"""Generate this DBBW example with the current pywikc_clean package.

Run from any working directory, or use Run in PyCharm:
    python examples/DBBW/DBBW-macro-processing.py

The supplied input already contains the MPC, amplitude and field keywords.
Do not append MPC_Keywords.txt to it a second time. A separate -final.inp
uses the absolute imperfection path resolved on the machine running this
script. The source input is unchanged. Abaqus solving is a separate step.
"""

from pathlib import Path
import re
import sys


EXAMPLE_DIR = Path(__file__).resolve().parent

# Prefer the package belonging to this example, including in PyCharm.
for candidate in (EXAMPLE_DIR,) + tuple(EXAMPLE_DIR.parents):
    if (candidate / 'pywikc' / '__init__.py').is_file():
        sys.path.insert(0, str(candidate))
        break

import pywikc
from pywikc.imperfections.options import normalize_imperfection_options


def write_final_input(source, destination, imp_file):
    """Write an absolute INPUT reference in a copy; preserve other bytes."""
    if source.resolve() == destination.resolve():
        raise ValueError('The final input must be separate from the source input')
    absolute_path = imp_file.resolve(strict=True).as_posix()
    if any(char in absolute_path for char in ('"', '\r', '\n')):
        raise ValueError('The imperfection path contains an unsupported character')
    absolute_path_bytes = absolute_path.encode('utf-8')
    original = source.read_bytes()
    newline = b'\r\n' if b'\r\n' in original else b'\n'
    lines = original.splitlines(keepends=True)
    indices = [i for i, line in enumerate(lines)
               if line.split(b',', 1)[0].strip().upper() == b'*IMPERFECTION']
    if len(indices) > 1:
        raise ValueError('Expected at most one *IMPERFECTION keyword')
    if indices:
        index = indices[0]
        pattern = rb'(?i)(\bINPUT\s*=\s*)(?:"[^"]*"|[^,\r\n]+)'
        lines[index], count = re.subn(
            pattern, lambda match: match.group(1) + absolute_path_bytes, lines[index])
        if count != 1:
            raise ValueError('Existing *IMPERFECTION must specify an INPUT file')
    else:
        step = next((i for i, line in enumerate(lines)
                     if line.split(b',', 1)[0].strip().upper() == b'*STEP'), None)
        if step is None:
            raise ValueError('Cannot locate the first *STEP for the imperfection reference')
        lines.insert(step, b'*IMPERFECTION, INPUT=' + absolute_path_bytes + newline)
    destination.write_bytes(b''.join(lines))
    return destination


def main():
    inp_file = EXAMPLE_DIR / 'DBBW-Macro.inp'
    cdef_file = EXAMPLE_DIR / 'DBBW-Macro-CDef.txt'
    out_dir = EXAMPLE_DIR / 'output'
    for source in (inp_file, cdef_file):
        if not source.is_file():
            raise FileNotFoundError('Missing example input: {}'.format(source))

    # Check the current input schema before generating files.
    reader = pywikc.AbaqusInpToComponentReader()
    components = reader.read(str(inp_file), str(cdef_file))
    for component in components:
        normalize_imperfection_options(component.imperfection_props)

    out_dir.mkdir(parents=True, exist_ok=True)
    pywikc.gen_aba_couples_imperfections(
        str(inp_file), str(cdef_file), str(out_dir)
    )

    imp_file = out_dir / 'DBBW-Macro-Imp.txt'
    job_input = write_final_input(
        inp_file, out_dir / 'DBBW-Macro-final.inp', imp_file)

    print('\npywikc package: {}'.format(Path(pywikc.__file__).resolve()))
    print('Definition file: {}'.format(cdef_file))
    for component in components:
        print('{}: L={:g}, beam nodes={}, shell nodes={}, couplings={}'.format(
            component.id, component.length, len(component.beam_nodes),
            len(component.continuum_nodes), len(component.couplings)))
    print('Generated files:')
    for name in ('DBBW-Macro-Imp.txt', 'MPC_Keywords.txt', job_input.name):
        print('  {}'.format(out_dir / name))
    print('Preprocessing complete. No Abaqus analysis has been submitted.')


if __name__ == '__main__':
    main()
