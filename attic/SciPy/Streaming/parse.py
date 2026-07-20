import regex
import regex as re

def get_next_block(string: str, start_idx: int):
  regex_str = r"/\*\s*Block\s+(\w+)\s*([\s\S]*?)\*/"
  return re.search(regex_str, filestring)

def parse_block(block: str):
  regex_str = r"<\|\s(\w+)\s*([\s\S]*?)\|>"
  start_idx = 0
  results = {}
  while True:
    m = re.search(regex_str, block[start_idx:])
    if not m or m.lastindex != 2: return results
    results[m.group(1)] = m.group(2)
    start_idx += m.end()

#def parse_file()




if __name__ == '__main__':

  filename = 'blocks.src'
  file = open(filename)
  filestring = file.read()

  results = {}
  start_idx = 0
  m = get_next_block(filestring, start_idx)
  results[m.group(1)] = parse_block(m.group(2))
  pass

