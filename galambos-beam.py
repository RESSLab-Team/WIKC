from src.reader import AbaqusInpReader
from src.writer import AbaqusCouplingWriter

inp_file = 'run_files/galambos-beam/Center_Tor_Macro-EQN.inp'
def_file = 'run_files/galambos-beam/galambos-beam-def.txt'
out_dir = 'run_files/galambos-beam/output/'

reader = AbaqusInpReader()
writer = AbaqusCouplingWriter(out_dir, input_path_prepend='constr_files/')
couplings = reader.read(inp_file, def_file)
writer.write(couplings)
