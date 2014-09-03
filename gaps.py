#!/usr/bin/env python3

"""
For each station--element in the input file, output the gaps. A
gap is a period where there is no data, immediately surrounded
before and after by a period with data.

The output is a series of lines, one for each gap:

  ID ELEM GAP

The following UNIX pipeline will produce a table:

  cumulative count gap

where `gap` gives the length of the gap in months;
`count` gives the number of gaps of that length;
`cumulative` give the cumulative number of gaps of at least that length

  awk '{print$3}' gaps-ghcnm | sort -r -n | uniq -c |
  awk '{s+=$1;print s, $1, $2}'
"""

import itertools
import sys

class Station:
    def __init__(self, **k):
        self.data = []
        self.__dict__.update(k)

    def add_row(self, row):
        year = int(row[11:15])
        while self.first_year + len(self.data) // 12 < year:
            self.data.extend([None] * 12)
        for m in range(12):
            v = int(row[19+m*8:24+m*8])
            if v == -9999:
                self.data.append(None)
            else:
                self.data.append(int(v))

def gaps(inp):
    for station in records(inp):
        data = station.data

        # Strip None from beginning and end.
        while data[0] is None:
            data = data[1:]
        while data[-1] is None:
            data = data[:-1]

        for gap, block in itertools.groupby(data, lambda x: x is None):
            if gap:
                print(station.id, station.element, len(list(block)))

def records(inp):
    """
    Given `inp` in GHCN-M v3 format (or ISTI's variant), yield a
    sequence of Station instances; where a station has several
    elements recorded in the file (ISTI style), an instance for
    each element will be yielded.
    """

    def get_id(l):
        return l[:11]

    def get_elem(l):
        return l[15:19]

    for id, station_block in itertools.groupby(inp, get_id):
        sorted_by_element = sorted(station_block, key=get_elem)
        for elem, rows in itertools.groupby(sorted_by_element, get_elem):
            rows = list(rows)
            station = Station(id=id, element=elem, first_year=int(rows[0][11:15]))
            for row in rows:
                station.add_row(row)
            yield station

def main(argv=None):
    if argv is None:
        argv = sys.argv

    arg = argv[1:]
    with open(arg[0]) as inp:
        gaps(inp)

if __name__ == '__main__':
    main()
