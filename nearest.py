#!/usr/bin/env python3

"""
nearest -LT+LON

Print a list of the nearest stations to the given location.
"""

import math
import os
import re

def nearest(target, inv):
    m = re.match(r'([-+]\d+(?:\.(?:\d+))?)([-+]\d+(?:\.(?:\d+))?)',
      target)
    lat, lon = [float(s) for s in m.groups()]

    target_xyz = xyz(lat, lon)

    def distance_from_target(thing):
        return distance(thing[0], target_xyz)

    i = 0
    for _, row in sorted(xyz_inv(inv), key=distance_from_target):
        print(row[:69].strip())
        i += 1
        if i >= 10:
            break


def distance(pv, qv):
    """
    Return the distance between the two vectors pv and qv.
    """
    assert len(pv) == len(qv)
    s = sum((p-q)**2 for p, q in zip(pv, qv))
    return s**0.5

def xyz_inv(inv):
    """
    For each row of the .inv file `inv` yield ((x,y,z), row).
    """
    for row in inv:
        lat = float(row[12:20])
        lon = float(row[21:30])
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            # CRUTEM4 has stations with invalid coords.
            continue
        yield xyz(lat, lon), row


def xyz(lat, lon):
    lat, lon = [math.radians(p) for p in (lat, lon)]
    z = math.sin(lat)
    x = math.cos(lon) * math.cos(lat)
    y = math.sin(lon) * math.cos(lat)
    return (x,y,z)


def main(argv=None):
    import codecs
    import glob
    import sys

    if argv is None:
        argv = sys.argv

    arg = argv[1:]

    pattern = os.path.expanduser("~/.local/share/data/ghcn/ghcnm*/*.inv")
    invs = glob.glob(pattern)
    inv = sorted(invs)[-1]
    # See http://www.evanjones.ca/python-utf8.html for use of codecs.
    with codecs.open(inv, 'r', 'iso8859-1') as inp:
        nearest(arg[0], inp)

if __name__ == '__main__':
    main()
