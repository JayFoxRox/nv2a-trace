from xboxpy import *
from hashlib import sha1
from time import perf_counter
import atexit
import struct

def get_hash(address, size):

  # We need to reserve a buffer for this structure:
  #
  # typedef struct {
  #   DWORD		FinishFlag;
  #   BYTE		HashVal[20];
  #   DWORD state[5];
  #   DWORD count[2];
  #   unsigned char buffer[64];
  # } A_SHA_CTX;
  sha_size = 4 + 20 + 5 * 4 + 2 * 4 + 64
  if get_hash.sha_address is None:
    get_hash.sha_address = ke.MmAllocateContiguousMemory(sha_size + 20)
    get_hash.sha_clean = read(get_hash.sha_address, sha_size - 64)

  # We need complete blocks, so the hash is always valid without XcSHAFinal.
  # This means we can retrieve it faster.
  assert(size % 64 == 0)

  # Writing a custom initialization is faster than doing a call
  if False:
    ke.XcSHAInit(get_hash.sha_address)
  else:
    write(get_hash.sha_address, get_hash.sha_clean)

  ke.XcSHAUpdate(get_hash.sha_address, address, size)  

  # We can read the result straight from the SHA context
  if False:
    sha_value_address = get_hash.sha_address + sha_size
    ke.XcSHAFinal(get_hash.sha_address, sha_value_address)
    sha_value = read(sha_value_address, 20)
  else:
    #FIXME: This doesn't return a sha1, but something else.
    #       Would need more logic: https://github.com/NVIDIA/winex_lgpl/blob/master/winex/dlls/advapi32/crypt_sha.c
    sha_value = read(get_hash.sha_address + 24, 20)
  return sha_value

@atexit.register
def free_get_hash():
  if get_hash.sha_address is not None:
    ke.MmFreeContiguousMemory(get_hash.sha_address)
    get_hash.sha_address = None

get_hash.sha_address = None


address = 0x11000
size = 512 * 1024 #0x100000

t0 = perf_counter()
h1 = get_hash(address, size)
t1 = perf_counter() 
h2 = get_hash(address, size)
t2 = perf_counter()
h3 = sha1(read(address, size)).digest()
t3 = perf_counter()

data = read(address, size)


def get_hashes(address, size, count=1):
  data = interface.if_xbdm.xbdm_command("getsum addr=0x%X length=0x%X blocksize=0x%X" % (address, size * count, size), length=count * 4)[1]
  return struct.unpack("<%dL" % count, data)

import zlib
print("0x%X" % zlib.crc32(data))
print("0x%X" % get_hashes(address, size)[0])

d = bytes([0x00] * 8)
def xboxcrc(d):
  h = zlib.crc32(d)
  h ^= 0xFFFFFFFF

  def reverse(x):
      result = 0
      for i in range(32):
          if (x >> i) & 1: result |= 1 << (31 - i)
      return result

  return reverse(h)
  
print("0x%X for 8 x zero" % xboxcrc(d))
write(address, d)
print("0x%X" % get_hashes(address, len(d))[0])



h4 = get_hashes(address, size // 16, 16)
t4 = perf_counter()


print("Hashed %d bytes" % size)
print("Initialization: %.2f ms [%s]" % ((t1 - t0) * 1000, h1.hex()))
print("Hash on Xbox:   %.2f ms [%s]" % ((t2 - t1) * 1000, h2.hex()))
print("Hash on Host:   %.2f ms [%s]" % ((t3 - t2) * 1000, h3.hex()))
print("Hash in XBDM:   %.2f ms %s" % ((t4 - t3) * 1000, str(list(hex(x) for x in h4))))

