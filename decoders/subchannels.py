def dump(state):
  print("Subchannels:")
  for i in range(8):
    grclass = state.read_nv2a_device_memory_word(0x400160 + i * 4) & 0xFF
    print("[%d] Graphics class: 0x%02X" % (i, grclass))
  print("")
