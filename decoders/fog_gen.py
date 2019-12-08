def dump(state):
  print("\nFog-gen:")

  csv0_d = state.read_nv2a_device_memory_word(0x400FB4)

  fog_mode = (csv0_d >> 21) & 1
  fog_modes_str = ('LINEAR', 'EXP')
  print("Mode: %s" % (fog_modes_str[fog_mode]))

  fog_genmode = (csv0_d >> 22) & 0x7
  fog_genmodes_str = ('SPEC_ALPHA', 'RADIAL', 'PLANAR', 'ABS_PLANAR', 'FOG_X')
  print("Gen-Mode: %s" % (fog_genmodes_str[fog_genmode]))

  fog_enable = (csv0_d >> 19) & 1
  print("Fog-Enable: %s" % (str(fog_enable)))

  print("")
