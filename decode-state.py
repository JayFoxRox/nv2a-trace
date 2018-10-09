#!/usr/bin/env python3

import sys
import struct

import helper

def align_up(v, alignment):
  return v + (alignment - (v % alignment)) % alignment

def load(path, suffix):
  full_path = path + "_" + suffix
  try:
    return open(full_path, "rb").read()
  except FileNotFoundError:
    print("Failed to load '%s'" % full_path)
    return None

def read_nv2a_mem_word(accessor, offset):
  assert((offset & 0xFF000000) == 0)
  section = (offset >> 16) & 0xFF
  offset &= 0xFFFF
  if section == 0x10:
    storage = accessor[1] # PFB
  elif section == 0x40:
    storage = accessor[2] # PGRAPH
  else:
    assert(False)
  return struct.unpack_from("<L", storage, offset)[0]

def read_nv2a_pgraph_rdi_word(accessor, offset):
  assert((offset & 0xFF000000) == 0)
  section = (offset >> 16) & 0xFF
  offset &= 0xFFFF
  if section == 0x10:
    storage = accessor[1] # vp-instructions
  elif section == 0x17:
    storage = accessor[2] # vp-constants0
  elif section == 0xCC:
    storage = accessor[3] # vp-constants1
  else:
    assert(False)
  return struct.unpack_from("<L", storage, offset)[0]

def read_word(accessor, offset):
  return accessor[0](accessor, offset)

def decode_float(word):
  return struct.unpack("<f", struct.pack("<L", word))[0]

path = sys.argv[1]

# Load memory dumps
mem_color = load(path, "mem-2.bin")
mem_depth = load(path, "mem-3.bin")
pgraph = load(path, "pgraph.bin")
pfb = load(path, "pfb.bin")
pgraph_rdi_vp_instructions = load(path, "pgraph-rdi-vp-instructions.bin")
pgraph_rdi_vp_constants0 = load(path, "pgraph-rdi-vp-constants0.bin")
pgraph_rdi_vp_constants1 = load(path, "pgraph-rdi-vp-constants1.bin")


# Put memory dumps into structure so they can be accessed

nv2a_mem = (
  read_nv2a_mem_word, # callback
  pfb,
  pgraph
)

nv2a_pgraph_rdi = (
  read_nv2a_pgraph_rdi_word, # callback
  pgraph_rdi_vp_instructions,
  pgraph_rdi_vp_constants0,
  pgraph_rdi_vp_constants1
)


# Dump PGRAPH subchannel information

print("\nSubchannels:")
for i in range(8):
  grclass = read_word(nv2a_mem, 0x400160 + i * 4) & 0xFF
  print("[%d] Graphics class: 0x%02X" % (i, grclass))
print("")
