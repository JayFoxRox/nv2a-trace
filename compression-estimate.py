import sys

cache = {}

cache_element_size = 0x10000 # The page size in bytes
hash_length = 16 # The length of a single hash in bytes
overhead = cache_element_size // 2 + hash_length # The number of virtual bytes we transfer for each hash lookup

def hash_func(data):
  return hash(data)

processed_bytes = 0
pad_bytes = 0

for path in sys.argv[1:]:

  print("Processing '%s'" % path)

  with open(path, 'rb') as f:
    while True:
      data = f.read(cache_element_size)
      if len(data) == 0:
        break
      processed_bytes += len(data)
      pad_size = cache_element_size - len(data)
      pad_bytes += pad_size
      data += bytes([0x00]) * pad_size
      assert(len(data) == cache_element_size)
      h = hash_func(data)
      if h in cache:
        assert(cache[h] == data)
      else:
        cache[h] = data

def mb(bytes):
  return bytes / 1024 / 1024

access_count = processed_bytes // cache_element_size

cache_size = len(cache) * (cache_element_size + hash_length)
overhead_size = access_count * overhead
traffic_size = cache_size + overhead_size

print("\nProcessed %.1f MiB and generated %.1f MiB of cache (%d element(s) x %d byte(s) per element), including %.1f MiB padding" % (mb(processed_bytes), mb(cache_size), len(cache), cache_element_size, mb(pad_bytes)))
print("That's %.1f MiB traffic, including %.1f MiB overhead (%d access(es) x %d bytes)" % (mb(traffic_size), mb(overhead_size), access_count, overhead))
print("Factor: %.2fx" % (processed_bytes / traffic_size))

