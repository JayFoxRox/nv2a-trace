def dump(state):
  print("\nTexture Units:")

  def get_texture_format_name(index):
    return '<format:0x%X>' % index

  for i in range(4):
    offset = state.read_nv2a_device_memory_word(0x401A24 + i * 4) # NV_PGRAPH_TEXOFFSET0
    ctl1 = state.read_nv2a_device_memory_word(0x4019DC + i * 4) # NV_PGRAPH_TEXCTL1_0
    fmt = state.read_nv2a_device_memory_word(0x401A04 + i * 4) # NV_PGRAPH_TEXFMT0
    
    pitch = (ctl1 >> 16) & 0xFFFF
    is_cubemap = bool((fmt >> 2) & 0x1)
    border_source = (fmt >> 3) & 0x1
    dimensionality = (fmt >> 6) & 0x3
    fmt_color = (fmt >> 8) & 0x7F
    levels = (fmt >> 16) & 0xF
    width_shift = (fmt >> 20) & 0xF
    height_shift = (fmt >> 24) & 0xF
    depth_shift = (fmt >> 28) & 0xF
    width = 1 << width_shift
    height = 1 << height_shift
    depth = 1 << depth_shift

    ctl0 = state.read_nv2a_device_memory_word(0x4019CC + i * 4)
    #   define NV_PGRAPH_TEXCTL0_0_ALPHAKILLEN                      (1 << 2)
    #   define NV_PGRAPH_TEXCTL0_0_MAX_LOD_CLAMP                    0x0003FFC0
    #   define NV_PGRAPH_TEXCTL0_0_MIN_LOD_CLAMP                    0x3FFC0000
    enabled = bool((ctl0 >> 30) & 1)

    #FIXME: What do these do?
    #define NV_PGRAPH_TEXCTL2_0                              0x000019EC
    #define NV_PGRAPH_TEXCTL2_1                              0x000019F0

    border_sources = ('Texture', 'Color')

    texture_filters = ('<invalid:0>',
                       'BOX_LOD0',
                       'TENT_LOD0',
                       'BOX_NEARESTLOD',
                       'TENT_NEARESTLOD',
                       'BOX_TENT_LOD',
                       'TENT_TENT_LOD',
                       'CONVOLUTION_2D_LOD0')

    filter0 = state.read_nv2a_device_memory_word(0x4019F4 + i * 4) # NV_PGRAPH_TEXFILTER0
    lod_bias = (filter0 >> 0) & 0x1FFF
    min_filter = (filter0 >> 16) & 0x3F
    mag_filter = (filter0 >> 24) & 0xF
    a_signed = bool((filter0 >> 28) & 0x1)
    r_signed = bool((filter0 >> 29) & 0x1)
    g_signed = bool((filter0 >> 30) & 0x1)
    b_signed = bool((filter0 >> 31) & 0x1)

    signed = []
    if a_signed: signed += ['A']
    if r_signed: signed += ['R']
    if g_signed: signed += ['G']
    if b_signed: signed += ['B']

    print("[%d] %s; %dD%s; format 0x%X (%s)" % (i, "enabled" if enabled else "disabled", dimensionality, " cubemap" if is_cubemap else "", fmt_color, get_texture_format_name(fmt_color)))
    print("    lod-bias: 0x%X; min-filter: %s; mag-filter: %s; signed: {%s}" % (lod_bias, texture_filters[min_filter], texture_filters[mag_filter], ",".join(signed)))

    imagerect = state.read_nv2a_device_memory_word(0x401A14 + i * 4) # NV_PGRAPH_TEXIMAGERECT0
    imagerect_width = (imagerect >> 16) & 0x1FFF
    imagerect_height = (imagerect >> 0) & 0x1FFF

    print("    linear-size: %d x %d" % (imagerect_width, imagerect_height))

    addressings = ('<invalid:0>', 'WRAP', 'MIRROR', 'CLAMP_TO_EDGE', 'BORDER', 'CLAMP_OGL')

    address = state.read_nv2a_device_memory_word(0x4019BC + i * 4) # NV_PGRAPH_TEXADDRESS

    address_u = (address >> 0) & 0x7
    wrap_u = bool((address >> 4) & 0x1)
    address_v = (address >> 8) & 0x7
    wrap_v = bool((address >> 12) & 0x1)
    address_p = (address >> 16) & 0x7
    wrap_p = bool((address >> 20) & 0x1)
    wrap_q = bool((address >> 24) & 0x1)

    def yesno(x):
      return "Yes" if x else "No"

    print("    addressing: %s, %s, %s; wrap: %s, %s, %s, %s" % (addressings[address_u], addressings[address_v], addressings[address_p],
                                                                yesno(wrap_u), yesno(wrap_v), yesno(wrap_p), yesno(wrap_q)))
#FIXME:
#define NV_PGRAPH_TEXPALETTE0                            0x00001A34
#   define NV_PGRAPH_TEXPALETTE0_CONTEXT_DMA                    (1 << 0)
#   define NV_PGRAPH_TEXPALETTE0_LENGTH                         0x0000000C
#       define NV_PGRAPH_TEXPALETTE0_LENGTH_256                     0
#       define NV_PGRAPH_TEXPALETTE0_LENGTH_128                     1
#       define NV_PGRAPH_TEXPALETTE0_LENGTH_64                      2
#       define NV_PGRAPH_TEXPALETTE0_LENGTH_32                      3
#   define NV_PGRAPH_TEXPALETTE0_OFFSET                         0xFFFFFFC0

    real_pitch = pitch # FIXME: look at swizzled / linear format
    for level in range(levels):
      print("    level %d: 0x%08X; %d x %d x %d; pitch: 0x%X" % (level, offset, width, height, depth, pitch))        
      offset += real_pitch
      if width >= 2: width //= 2
      if height >= 2: height //= 2
      if depth >= 2: depth //= 2
      pitch //= 2
  print("")
