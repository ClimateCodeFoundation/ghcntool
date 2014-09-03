#!/usr/bin/env python3

"""
scalpel. After Rohde et al 2013

Cuts a dataset up into pieces. The cuts are made where there are
gaps in the data. For a configurable parameter, N, the cuts are
made whereever there is a gap of length N or more.

Applying the scalpel effectively new stations, though these
stations have the same metadata as their "parent" station. The
new stations are given mutated IDs. Where a child station is cut
from its parent, the the parent's ID is mutated by changing the
rightmost occurence of the ASCIIbetically least character in the
ID (note: this will often be a '0'); this character is changed
to 'a' (note: lowercase) for the child with the oldest data, 'b'
for the child with the next oldest data, and so on, up to the
child with the most recent data which has the privilege of
retaining its parent ID.

A new .dat file and a new .inv file are output.
"""

import itertools
import sys

class Config:
    """Just a blank struct to hold the config."""

config = Config()
config.N = 18

class Station:
    def __init__(self, **k):
        self.data = []
        self.__dict__.update(k)

    def add_row(self, row):
        assert not hasattr(self, 'first_month')
        year = int(row[11:15])
        if not hasattr(self, 'first_year'):
            self.first_year = year

        # Subsequent rows must be for later years.
        assert self.first_year + len(self.data) // 12 <= year

        # If we skip a year, pad the data
        while self.first_year + len(self.data) // 12 < year:
            self.data.extend([None] * 12)
        for m in range(12):
            v = int(row[19+m*8:24+m*8])
            if v == -9999:
                self.data.append(None)
            else:
                self.data.append(int(v))

    def trim(self):
        """
        Remove initial and trailing periods of repeated None.
        (and modify the station from using .first_year to using
        .first_month).
        """

        # Months are numbered so that January of year 0 is 0.
        first_month = self.first_year * 12
        del self.first_year
        while self.data[0] is None:
            self.data = self.data[1:]
            first_month += 1
        while self.data[-1] is None:
            self.data = self.data[:-1]
        self.first_month = first_month

    def write_ghcnm_v3(self, out):
        """
        Write out data to `out` in GHCN-M v3 format. Destroys
        the data in self.data.
        """

        # Undo the trimming, by padding out to year boundaries.
        while self.first_month % 12 != 0:
            self.data = [None] + self.data
            self.first_month -= 1
        while len(self.data) % 12 != 0:
            self.data.append(None)

        while self.data:
            year = self.first_month // 12
            year_data = self.data[:12]
            self.data = self.data[12:]
            self.first_month += 12
            if year_data == [None]*12:
                # Whole year has invalid data, skip it.
                continue
            assert 11 == len(self.id)
            assert 4 == len(self.element)
            out.write("{}{:4d}{}{}\n".format(
              self.id, year, self.element,
              convert_to_ghcnm(year_data)))

def convert_to_ghcnm(l):
    """Convert 12 values in l to GHCN-M v3 format."""
    def convert1(x):
        if x is None:
            return '-9999   '
        else:
            return '{:5d}   '.format(x)

    assert 12 == len(l)
    return ''.join(convert1(v) for v in l)


def scalpel(dat, inp_inv, out_dat, out_inv):
    mutants = {}
    for station in records(dat):
        station.trim()

        # Copy station data onto data, until we see a gap that's
        # big enough to cut.
        data = []
        # The first month of the data in data[]
        month = station.first_month
        for gap, block in itertools.groupby(station.data, lambda x: x is None):
            block = list(block)
            if gap and len(block) >= config.N:
                id = mutate(station.id, mutants)
                child = Station(id=id,
                  first_month=month,
                  element=station.element, data=data)
                child.write_ghcnm_v3(out_dat)
                # Update month and reset data
                month += len(data) + len(block)
                data = []
            else:
                data.extend(block)
        # This child, the most recent one, keeps its parent's id.
        child = Station(id=station.id,
          first_month=month,
          element=station.element, data=data)
        child.write_ghcnm_v3(out_dat)

    # Write out the new inv file (which copies the inp_inv
    # file for each child of the parent).
    inv = dict((row[:11], row) for row in inp_inv)
    for id, row in sorted(inv.items()):
        out_inv.write(row)
        for child_id in mutants.get(id, []):
            out_inv.write("{}{}".format(child_id, row[11:]))

def mutate(id, mutants):
    """
    Pick a mutated id, store the mutants as a list associated
    with id in the dict of mutants.
    """

    # ASCIIbetically least character.
    t = sorted(id)[0]
    # Rightmost position of t.
    i = id.rindex(t)

    if id not in mutants:
        new_id = id[:i] + 'a' + id[i+1:]
        mutants[id] = [new_id]
        return new_id

    letters = 'abcdefghijklmnopqrstuvwxyz'
    modified_t = letters[len(mutants[id])]
    new_id = id[:i] + modified_t + id[i+1:]
    mutants[id].append(new_id)
    return new_id

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
            station = Station(id=id, element=elem)
            for row in rows:
                station.add_row(row)
            yield station

def main(argv=None):
    import getopt

    if argv is None:
        argv = sys.argv

    opt, arg = getopt.getopt(argv[1:], 'o:')

    out_dat_name = None
    for k,v in opt:
        if k == '-o':
            out_dat_name = v

    if out_dat_name is None:
        raise Exception('-o thing.dat is required')
    if out_dat_name.endswith('.dat'):
        out_inv_name = out_dat_name[:-4] + '.inv'
    else:
        raise Exception('.dat file must end .dat')

    if arg[0].endswith('.dat'):
        inv_name = arg[0][:-4] + '.inv'
    else:
        raise Exception('.dat file must end .dat')

    with open(arg[0]) as dat, open(inv_name) as inv,\
          open(out_dat_name, 'w') as out_dat,\
          open(out_inv_name, 'w') as out_inv:
        scalpel(dat, inv, out_dat, out_inv)
        

if __name__ == '__main__':
    main()
