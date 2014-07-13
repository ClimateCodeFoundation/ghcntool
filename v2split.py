#!/usr/bin/env python
#
# v2split.py
#
# David Jones, Ravenbrook Limited, 2010-02-26

"""
python ghcn_split.py YYYY

Splits a GHCN-M file, on stdin, into two files: ghcnm-preYYYY,
ghcnm-postYYYY.  The split is made on the basis of which stations are
reporting in the year YYYY or a more recent year.  ghcnm-postYYYY will
contain records for all the stations that have a record in the year YYYY
or a more recent year; ghcnm-preYYYY will contain the records for all
the other stations.
"""

def get_year(line):
    if len(line) == 116:
        # GHCN-M v3
        return int(line[11:15])
    else:
        # GHCN-M v2
        return int(line[12:16])

def split(inp, out, splitat):
    """Input flle: *inp*;
    Output files: *out* (a pair);
    The year used to split the stations: *splitat*.
    """

    import itertools

    def id11(line):
        """
        The 11-digit station identifier for a record.
        """
        return line[:11]

    for stationid,lines in itertools.groupby(inp, id11):
        lines = list(lines)
        # Gather the set of years for which there are records (across
        # all duplicates for a single station, if using GHCN-M v2).
        years = set(get_year(line) for line in lines)
        if max(years) >= splitat:
            out[1].writelines(lines)
        else:
            out[0].writelines(lines)

def main(argv=None):
    import sys
    if argv is None:
        argv = sys.argv

    year = int(argv[1])
    out = [open('ghcnm-pre%d' % year, 'w'),
           open('ghcnm-post%d' % year, 'w')]

    return split(sys.stdin, out, year)

if __name__ == '__main__':
    main()
