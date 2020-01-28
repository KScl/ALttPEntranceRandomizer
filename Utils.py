import os
import re
import subprocess
import sys

def parse_names_string(names):
    return {player: name for player, name in enumerate([n for n in re.split(r'[, ]', names) if n], 1)}

def int16_as_bytes(value):
    value = value & 0xFFFF
    return [value & 0xFF, (value >> 8) & 0xFF]

def int32_as_bytes(value):
    value = value & 0xFFFFFFFF
    return [value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF, (value >> 24) & 0xFF]

def pc_to_snes(value):
    return ((value<<1) & 0x7F0000)|(value & 0x7FFF)|0x8000

def snes_to_pc(value):
    return ((value & 0x7F0000)>>1)|(value & 0x7FFF)

def is_bundled():
    return getattr(sys, 'frozen', False)

def local_path(path):
    if local_path.cached_path is not None:
        return os.path.join(local_path.cached_path, path)

    if is_bundled():
        # we are running in a bundle
        local_path.cached_path = sys._MEIPASS # pylint: disable=protected-access,no-member
    else:
        # we are running in a normal Python environment
        local_path.cached_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(local_path.cached_path, path)

local_path.cached_path = None

def output_path(path):
    if output_path.cached_path is not None:
        return os.path.join(output_path.cached_path, path)

    if not is_bundled():
        output_path.cached_path = '.'
        return os.path.join(output_path.cached_path, path)
    else:
        # has been packaged, so cannot use CWD for output.
        if sys.platform == 'win32':
            #windows
            import ctypes.wintypes
            CSIDL_PERSONAL = 5       # My Documents
            SHGFP_TYPE_CURRENT = 0   # Get current, not default value

            buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
            ctypes.windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)

            documents = buf.value

        elif sys.platform == 'darwin':
            from AppKit import NSSearchPathForDirectoriesInDomains # pylint: disable=import-error
            # http://developer.apple.com/DOCUMENTATION/Cocoa/Reference/Foundation/Miscellaneous/Foundation_Functions/Reference/reference.html#//apple_ref/c/func/NSSearchPathForDirectoriesInDomains
            NSDocumentDirectory = 9
            NSUserDomainMask = 1
            # True for expanding the tilde into a fully qualified path
            documents = NSSearchPathForDirectoriesInDomains(NSDocumentDirectory, NSUserDomainMask, True)[0]
        else:
            raise NotImplementedError('Not supported yet')

        output_path.cached_path = os.path.join(documents, 'ALttPEntranceRandomizer')
        if not os.path.exists(output_path.cached_path):
            os.mkdir(output_path.cached_path)
        return os.path.join(output_path.cached_path, path)

output_path.cached_path = None

def open_file(filename):
    if sys.platform == 'win32':
        os.startfile(filename)
    else:
        open_command = 'open' if sys.platform == 'darwin' else 'xdg-open'
        subprocess.call([open_command, filename])

def close_console():
    if sys.platform == 'win32':
        #windows
        import ctypes.wintypes
        try:
            ctypes.windll.kernel32.FreeConsole()
        except Exception:
            pass

def make_new_base2current(old_rom='Zelda no Densetsu - Kamigami no Triforce (Japan).sfc', new_rom='working.sfc', out_file='data/base2current.json'):
    from collections import OrderedDict
    import json
    import hashlib
    with open(old_rom, 'rb') as stream:
        old_rom_data = bytearray(stream.read())
    with open(new_rom, 'rb') as stream:
        new_rom_data = bytearray(stream.read())
    # extend to 2 mb
    old_rom_data.extend(bytearray([0x00] * (2097152 - len(old_rom_data))))

    out_data = OrderedDict()
    for idx, old in enumerate(old_rom_data):
        new = new_rom_data[idx]
        if old != new:
            out_data[idx] = [int(new)]
    for offset in reversed(list(out_data.keys())):
        if offset - 1 in out_data:
            out_data[offset-1].extend(out_data.pop(offset))
    with open(out_file, 'wt') as outfile:
        json.dump([{key:value} for key, value in out_data.items()], outfile, separators=(",", ":"))

    basemd5 = hashlib.md5()
    basemd5.update(new_rom_data)
    return "New Rom Hash: " + basemd5.hexdigest()

def make_base_rom(json_patch='data/base2current.json', out='roms/base2current.sfc'):
    from Rom import LocalRom
    rom = LocalRom('Zelda no Densetsu - Kamigami no Triforce (Japan).sfc', json_patch)
    rom.write_to_file(out)

def make_branch_rom(json_patch='data/base2current.json', branch_patch='data/branch/base.json', out='roms/branch_base.sfc'):
    from Rom import LocalRom
    rom = LocalRom('Zelda no Densetsu - Kamigami no Triforce (Japan).sfc', json_patch)
    rom.apply_json_patch(branch_patch)
    rom.write_to_file(out)

def update_branch_base2current():
    print('Updating base patch')
    make_branch_rom('data/base2current.json', 'data/branch/base.json', 'roms/branch_base.sfc')
    print(make_new_base2current('Zelda no Densetsu - Kamigami no Triforce (Japan).sfc', 'roms/branch_base.sfc', 'data/branch/compiled_base.json'))

    print('Updating extmsu patch')
    make_branch_rom('data/base2current_extendedmsu.json', 'data/branch/extmsu.json', 'roms/branch_extmsu.sfc')
    print(make_new_base2current('Zelda no Densetsu - Kamigami no Triforce (Japan).sfc', 'roms/branch_extmsu.sfc', 'data/branch/compiled_extmsu.json'))
