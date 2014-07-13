# GHCN Tool

A collection of tools to work with data from Global Historical
Climate Network (GHCN).

# Status

As of 2014-07 these have just been split from
ClimateCodeFoundation/ccc-gistemp and dumped here. Consequently,
many of the tools don't run without having various directories
and modules from ccc-gistemp made available to them.

We intend to fix that situation, so that the tools here work
standalone, or almost so.

Many of the tools only work with the (now obsolete) GHCN v2, we
would like them to work with GHCN-M v3.

# Tools that should work

`popchart.py` draws a (google) chart that show number of rows of
data in each year.

`split_year.py` splits an GHCN-M dataset into those stations
that still report in a particular year, and those that don't.

`stationplot.py` (unless you use the `-y` option). It plots
station records as an SVG file.

