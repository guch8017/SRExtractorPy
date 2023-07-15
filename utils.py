import ctypes


def bytes_to_hex_string(b: bytes) -> str:
    return ''.join(f'{x:02x}' for x in b)


def get_stable_hash(s: str) -> int:
    """
    Python version of GNUHash, copy from @CMAGMDKBOOB
    :param s:
    :return:
    """
    if s is None:
        return 0

    num = 5381
    num2 = num
    for i in range(0, len(s), 2):
        num = ctypes.c_int32(((num << 5) + num) ^ ord(s[i])).value
        if i + 1 >= len(s):
            break
        num4 = ctypes.c_int32(((num2 << 5) + num2) ^ ord(s[i + 1])).value
        num2 = num4

    return ctypes.c_int32(num + num2 * 1566083941).value
