import struct

class NV2AState():
  pass

class MemoryBuffer():
  def __init__(self):
    self.blocks = {}

  def write(self, offset, data):
    if len(data) == 0:
      return

    # Avoid overlap
    #FIXME: Split block instead
    low = offset
    high = offset + len(data) - 1
    for offsets in self.blocks:
      is_left = (high < offsets[0])
      is_right = (low > offsets[-1])
      assert(is_left or is_right)

    self.blocks[range(low, high+1)] = data

  def read(self, offset, length):
    if length == 0:
      return bytes([])
    for offsets in self.blocks:
      if offset in offsets:
        block_offset = offset - offsets[0]
        max_length = min(length, offsets[-1] - block_offset + 1)
        data = self.blocks[offsets][block_offset:block_offset+max_length] + \
               self.read(offset+max_length, length-max_length)
        return data
    return bytes([0x00]) * length

  def write_from_files(self, path):
    pass #FIXME

  def read_to_files(self, path):
    pass #FIXME
    

class NV2AStateFromFile(NV2AState):

  def __init__(self, path):
    self.nv2a_pgraph_rdi = MemoryBuffer()
    self.nv2a_pgraph_rdi.write_from_files(path + "-nv2a_pgraph_rdi")
    self.nv2a_device_memory = MemoryBuffer()
    self.nv2a_device_memory.write_from_files(path + "-nv2a_device_memory")
    self.memory = MemoryBuffer()
    self.memory.write_from_files(path + "-memory")

    def _load(path, suffix):
      full_path = path + "_" + suffix
      try:
        return open(full_path, "rb").read()
      except FileNotFoundError:
        print("Failed to load '%s'" % full_path)
        return bytes([])

    # Legacy dump format
    self.nv2a_pgraph_rdi.write(0x100000, _load(path, "pgraph-rdi-vp-instructions.bin"))
    self.nv2a_pgraph_rdi.write(0x170000, _load(path, "pgraph-rdi-vp-constants0.bin"))
    self.nv2a_pgraph_rdi.write(0xCC0000, _load(path, "pgraph-rdi-vp-constants1.bin"))

    # Legacy dump format
    self.nv2a_device_memory.write(0x100000, _load(path, "pfb.bin"))
    self.nv2a_device_memory.write(0x400000, _load(path, "pgraph.bin"))

    # Legacy dump format
    color_offset = self.read_nv2a_device_memory_word(0x400828)
    depth_offset = self.read_nv2a_device_memory_word(0x40082C)
    color_base = self.read_nv2a_device_memory_word(0x400840)
    depth_base = self.read_nv2a_device_memory_word(0x400844)
    self.memory.write(color_base + color_offset, _load(path, "mem-2.bin"))
    self.memory.write(depth_base + depth_offset, _load(path, "mem-3.bin"))


  def read_nv2a_device_memory_word(self, offset):
    data = self.nv2a_device_memory.read(offset, 4)
    return struct.unpack("<L", data)[0]

  def read_nv2a_pgraph_rdi_word(self, offset):
    data = self.nv2a_pgraph_rdi.read(offset, 4)
    return struct.unpack("<L", data)[0]

  def read_memory(self, offset, length):
    data = self.memory.read(offset, length)
    return data
