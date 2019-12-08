#!/usr/bin/env python3

import sys

import state


path = sys.argv[1]
state = state.NV2AStateFromFile(path)


from decoders import subchannels
subchannels.dump(state)

# Dump pipeline
if False:
  csv0_d = state.read_nv2a_device_memory_word(0x400FB4)

  pipeline = (csv0_d >> 30) & 0x3
  pipelines_str = ("Fixed-Function", "<unknown:1>", "Program")
  print("\nVertex Pipeline: %s" % (pipelines_str[pipeline]))

  if pipeline == 0:
    print("<Fixed-Function configuration>")
  elif pipeline == 2:
    from decoders import vertex_program
    vertex_program.dump(state)
  else:
    assert(False)

from decoders import fog_gen
fog_gen.dump(state)

from decoders import textures
textures.dump(state)

from decoders import texture_shaders
texture_shaders.dump(state)

from decoders import register_combiners
register_combiners.dump(state)

from decoders import fog
fog.dump(state)

if False:
  from decoders import tiles
  tiles.dump(state)

from decoders import surfaces
surfaces.dump(state)

