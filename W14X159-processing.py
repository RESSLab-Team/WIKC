"""Generate imperfection and coupling text files without editing the input.

Run this file in PyCharm, or from the project root:
    python examples/W14X159/W14X159-processing.py

The source .inp is opened only for reading. A separate -final.inp contains
an absolute *IMPERFECTION INPUT reference resolved on the machine running
this script. Coupling keywords remain a separate text output.
"""

import hashlib
from pathlib import Path
import re
import sys


EXAMPLE_DIR = Path(__file__).resolve().parent
MODEL_NAME = 'cl-W14X159-5000-S-03-Fx'

for candidate in (EXAMPLE_DIR,) + tuple(EXAMPLE_DIR.parents):
    if (candidate / 'pywikc' / '__init__.py').is_file():
        sys.path.insert(0, str(candidate))
        break

import numpy as np
import pywikc
from pywikc.imperfections import AbaqusTxtWriter, generate_component_imp


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
    inp_file = EXAMPLE_DIR / (MODEL_NAME + '.inp')
    cdef_file = EXAMPLE_DIR / (MODEL_NAME + '-def.txt')
    out_dir = EXAMPLE_DIR / 'output'
    for source in (inp_file, cdef_file):
        if not source.is_file():
            raise FileNotFoundError('Missing input: {}'.format(source))
    original_hash = hashlib.sha256(inp_file.read_bytes()).hexdigest()

    reader = pywikc.AbaqusInpToComponentReader()
    components = reader.read(str(inp_file), str(cdef_file))

    # The uploaded model has small coordinate-rounding differences at its
    # two interfaces. Check the axial locations without moving any nodes.
    for component in components:
        for info in component.couplings_info:
            beam_id = reader.beam_sets[info['beam_set']][0]
            solid_ids = reader.continuum_sets[info['continuum_set']]
            beam_z = component.beam_nodes[beam_id][2]
            solid_z = np.array([component.continuum_nodes[n][2] for n in solid_ids])
            if not np.allclose(solid_z, beam_z, rtol=0., atol=2.e-6):
                raise ValueError('Axial mismatch at coupling {}'.format(info['beam_set']))
        generate_component_imp(component)

    out_dir.mkdir(parents=True, exist_ok=True)
    imp_file = out_dir / (MODEL_NAME + '-Imp.txt')
    AbaqusTxtWriter(components).write_imperfections(str(imp_file))
    couplings = [coupling for component in components for coupling in component.couplings]
    pywikc.AbaqusICouplingWriter(str(out_dir)).write(couplings)

    final_input = write_final_input(
        inp_file, out_dir / (MODEL_NAME + '-final.inp'), imp_file)

    if hashlib.sha256(inp_file.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError('Input file integrity check failed')

    print('pywikc package: {}'.format(Path(pywikc.__file__).resolve()))
    for component in components:
        print('{}: L={:.8f}, beam nodes={}, solid nodes={}, interfaces={}'.format(
            component.id, component.length, len(component.beam_nodes),
            len(component.continuum_nodes), len(component.couplings)))
    print('Generated: {}'.format(imp_file))
    print('Generated: {}'.format(out_dir / 'MPC_Keywords.txt'))
    print('Generated: {}'.format(final_input))
    print('Input unchanged (SHA-256): {}'.format(original_hash))
    print('Source input unchanged. Only the final copy references the absolute imperfection path.')


if __name__ == '__main__':
    main()
