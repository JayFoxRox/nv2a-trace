def dump(state):
  import nv_tiles

  print("\nTiles:")

  # This configures how tiling works
  cfg0 = state.read_nv2a_device_memory_word(0x100200)
  cfg1 = state.read_nv2a_device_memory_word(0x100204)
  mcc = nv_tiles.mc_config(cfg0, cfg1)

  for i in range(8):

    # Also in PGRAPH 0x900?!
    tile = state.read_nv2a_device_memory_word(0x100240 + 16 * i)
    valid = tile & 1
    bank_sense = tile & 2
    address = tile & 0xFFFFC000

    tlimit = state.read_nv2a_device_memory_word(0x100244 + 16 * i)
    #FIXME: This is apparently 18+14 bits, much like address, but lower bits always set?
    assert((tlimit & 0x3FFF) == 0x3FFF)

    tsize = state.read_nv2a_device_memory_word(0x100248 + 16 * i)
    pitch = tsize & 0xFFFF
    assert(pitch & 0xFF == 0x00)

    tstatus = state.read_nv2a_device_memory_word(0x10024C + 16 * i)
    prime = (1, 3, 5, 7)[tstatus & 3]
    factor = 1 << ((tstatus >> 4) & 7)
    region_valid = tstatus & 0x80000000

    valid_str = "valid" if valid else "invalid"
    region_valid_str = "valid" if region_valid else "invalid"

    print("[%d] %s; bank sense %d; address 0x%08X, limit 0x%08X, pitch 0x%X, prime %d, factor %d, region %s" % (i, valid_str, bank_sense, address, tlimit, pitch, prime, factor, region_valid_str))

    fb_zcomp = state.read_nv2a_device_memory_word(0x100300 + 4 * i)
    zcomp_enabled = fb_zcomp & 0x80000000

    pgraph_zcomp = state.read_nv2a_device_memory_word(0x400980 + 4 * i)

    zcomp_enabled_str = "compressed" if zcomp_enabled else "uncompressed"

    print("    Z-compression: %s 0x%08X, 0x%08X" % (zcomp_enabled_str, fb_zcomp, pgraph_zcomp))

  print("")
