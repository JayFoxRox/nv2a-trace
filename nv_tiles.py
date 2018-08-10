# Based on https://github.com/envytools/envytools/blob/master/nvhw/tile.c

def is_igp(chipset):
  #  switch (chipset) {
  #    case 0x0a:
  #    case 0x1a:
  #    case 0x1f:
  #    case 0x2a:
  #    case 0x4e:
  #    case 0x4c:
  #    case 0x67:
  #    case 0x68:
  #    case 0x63:
  #    case 0xaa:
  #    case 0xac:
  #    case 0xaf:
  #      return 1;
  #    default:
  #      return 0;
  #  }

  # Hack, based on the following IRC discussion:
  #  mwk: JayFoxRox: don't treat the NV2A as an IGP
  #  mwk: it might be an IGP by definition, but the xbox.... is very strange
  #  mwk: in normal IGP setup, the GPU borrows memory from the main mem controller, but in xbox, it's the other way around -- all the memory in the xbox is VRAM, and the CPU borrows it
  #  mwk: so the memory controller is pretty much identical to a normal discrete GPU
  #  JayFoxRox: mwk: NV2A is chipset 0x2A, correct? so should I make is_igp return False in my use-case?
  #  mwk: is_igp... I guess it'd be OK to make is_igp false
  #  mwk: though it might be better to tie that to PFB type instead

  return False

def has_tile_factor_13(chipset):
  # return pfb_type(chipset) >= PFB_NV20 && chipset != 0x20

  # Not sure if NV2A / 0x2A actually qualifies, because it's before 0x25
  assert(False)

  return True

def has_large_tile(chipset):
  # return pfb_type(chipset) == PFB_NV40 || pfb_type(chipset) == PFB_NV41
  return False

PFB_NV10 = 1
PFB_NV20 = 2

def pfb_type(chipset):
  return PFB_NV20

def tile_pitch_valid(chipset, pitch):

  if (pitch & ~0x1ff00):
    return False, 0, 0

  pitch >>= 8
  if (pitch == 0):
    return False, 0, 0

  if (pitch == 1):
    return False, 0, 0
  if (pitch & 1) and ((pfb_type(chipset) == PFB_NV10) or (pfb_type(chipset) == PFB_NV44)):
    return False, 0, 0
  if (pitch > 0x100):
    return False, 0, 0

  shift = 0
  while ((pitch & 1) == 0):
    pitch >>= 1
    shift += 1

  if (shift >= 8) and has_large_tile(chipset) == False:
    return False, 0, 0

  if (pitch == 1):
    factor = 0
  elif (pitch == 3):
    factor = 1
  elif (pitch == 5):
    factor = 2
  elif (pitch == 7):
    factor = 3
  elif (pitch == 13):
    if has_tile_factor_13(chipset) == False:
      return False, 0, 0
    factor = 4
  else:
    return False, 0, 0

  return True, shift, factor

class mc_config:
  def __init__(self, cfg0, cfg1):
    self.mcbits = 0
    self.partbits = 0
    self.colbits_lo = 0
    self.burstbits = 0

    if True:
      #FIXME: Add https://github.com/envytools/envytools/blob/master/hwtest/nv10_tile.cc#L35
      self.mcbits = 2
      self.partbits = 2
      self.colbits_lo = 2
      self.burstbits = 0


def tile_translate_addr(chipset, pitch, address, mode, bankoff, mcc):
  bankshift = mcc.mcbits + mcc.partbits + mcc.colbits_lo
  is_vram = (mode == 1) or (mode == 4)
  if (is_igp(chipset)):
    is_vram = 0
  if (is_vram == False):
    bankshift = 12

  valid, shift, factor = tile_pitch_valid(chipset, pitch)
  if (valid == False):
    assert(False)

  x = address % pitch
  y = address // pitch
  ix = x & 0xff
  iy = y & ((1 << (bankshift - 8)) - 1)

  x >>= 8
  y >>= bankshift - 8
  iaddr = 0
  baddr = y * (pitch >> 8) + x
  part = 0
  tag = 0

  fb_type = pfb_type(chipset)
  if fb_type == PFB_NV10:
    iy = address >> (shift + 8) & ((1 << (bankshift - 8)) - 1)
    iaddr = ix | iy << 8
    if (y & 1):
      baddr ^= 1
    if (chipset > 0x10) and (mcc.mcbits + mcc.partbits + mcc.burstbits > 4) and (address & 0x100):
      iaddr ^= 0x10
    if (ppart or ptag):
      assert(False)
  elif fb_type == PFB_NV20:
    x1 = ix & 0xf
    ix >>= 4
    part = ix & ((1 << mcc.partbits) - 1)
    ix >>= mcc.partbits
    x2 = ix
    y1 = iy & 3
    iy >>= 2
    y2 = iy
    if (y2 & 1) and (mcc.partbits >= 1):
      part += 1 << (mcc.partbits - 1)
    if (y2 & 2) and (mcc.partbits >= 2):
      part += 1 << (mcc.partbits - 2)
    part &= (1 << mcc.partbits) - 1
    if (chipset >= 0x30):
      bank = baddr & 3
      if (shift >= 2):
        bank ^= y << 1 & 2
      if (shift >= 1):
        bank += y >> 1 & 1
      bank ^= bankoff
      bank &= 3
      baddr = (baddr & ~3) | bank
    else:
      baddr ^= bankoff
      if (y & 1) and shift:
        baddr ^= 1
    iaddr = y2

    iaddr <<= 4 - mcc.partbits
    iaddr |= x2
    
    iaddr <<= 2
    iaddr |= y1

    iaddr <<= mcc.partbits
    iaddr |= part

    iaddr <<= 4
    iaddr |= x1

    tag = x + y * (pitch >> 8)

    tag <<= bankshift - 10
    tag |= iy

    tag <<= (4 - mcc.partbits)
    tag |= x2

  else:
    assert(False)

  return tag, part, (iaddr | baddr << bankshift)


if False:
  chipset = 0x2A
  pitch = 2560

  #FIXME: Where to get these from? - probably NV_PFB_CFG0 / NV_PFB_CFG1 ?
  mode = 1
  bankoff = 0
  mcc = mc_config()
  mcc.mcbits = 2
  mcc.partbits = 2
  mcc.colbits_lo = 2
  mcc.burstbits = 0

  #<li>2 bits selecting byte inside a memory cell</li>
  #<li>2 bits selecting a column</li>
  #<li>0-2 more bits selecting byte inside a memory cell [depending on bus width]</li>
  #<li>6-8 more bits selecting a column</li>
  #<li>1 bit selecting a bank</li>
  #<li>8-12 bits selecting a row</li>
  #<li>0-1 more bits selecting a bank</li>

  for i in range(640*480):
    address = i
    out_address = tile_translate_addr(chipset, pitch, address * 4, mode, bankoff, mcc)
    print("%d: %d" % (address, out_address[2] // 4))

