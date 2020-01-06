# Based on
# https://gist.github.com/jamesacampbell/2f170fc17a328a638322078f42e04cbc
# 20191225 RDW: adapted to work with Python3 str-type Strings

import os
import hashlib


def hash_password(password: str) -> str:

    # supply password
    secret = password.encode('utf-8')

    # static 'count' value later referenced as "c"
    indicator = bytes(chr(96), 'ascii')

    # generate salt and append indicator value so that it
    salt = os.urandom(8)
    salt += indicator

    # That's just the way it is. It's always prefixed with 16
    prefix = '16:'

    # swap variables just so I can make it look exactly like the RFC example
    c = salt[8]

    # generate an even number that can be divided in subsequent sections. (Thanks Roman)
    EXPBIAS = 6
    count = (16 + (c & 15)) << ((c >> 4) + EXPBIAS)

    d = hashlib.sha1()

    # take the salt and append the password
    tmp = salt[:8] + secret

    # hash the salty password as many times as the length of
    # the password divides into the count value
    slen = len(tmp)
    while count:
        if count > slen:
            d.update(tmp)
            count -= slen
        else:
            d.update(tmp[:count])
            count = 0
    hashed = d.digest()

    # Convert to hex
    salt = bytes.hex(salt[:8]).upper()
    indicator = bytes.hex(indicator).upper()
    torhash = bytes.hex(hashed).upper()

    # Put it all together into the proprietary Tor format.
    retval = f'{prefix}{salt}{indicator}{torhash}'
    return retval
