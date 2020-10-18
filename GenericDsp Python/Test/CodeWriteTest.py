# This is a sample Python script.

# Press ⌃R to execute it or replace it with your code.
# Press Double ⇧ to search everywhere for classes, files, tool windows, actions, and settings.

bufspec = [('buf1', 128), ('buf2', 1024)]
blocks = [('filt', 'filtA', ['a','b']), ('gain', 'gainA', [])]

def print_hi():
    str = ''
    for spec in bufspec:
        str += f'float {spec[0]}[{spec[1]}];\n'
    str += '\n'
    for block in blocks:
        str += f'{block[0]} {block[1]}({",".join(block[2])});\n'
    print(str)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    print_hi()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
