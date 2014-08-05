# GHCN Tool

A collection of tools to work with data from Global Historical
Climatology Network (GHCN).

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
data in each year. It draws charts like this:

![plot with bump between 1951 and 1980](http://chart.apis.google.com/chart?chxt=x,y,x&chds=1,10000&chd=t:336,364,388,401,417,438,458,499,530,578,614,710,776,950,1059,1147,1198,1286,1336,1380,1426,1461,1515,1577,1613,1649,1681,1782,1836,1891,1927,1984,2017,2064,2119,2132,2155,2158,2197,2185,2227,2264,2305,2338,2368,2397,2460,2474,2476,2510,2563,2646,2684,2717,2725,2764,2826,2857,2900,2929,2944,3002,3036,3075,3096,3127,3165,3225,3338,3474,3599,4049,4266,4366,4426,4447,4508,4506,4545,4581,4637,4812,4900,4992,5019,5155,5202,5209,5234,5273,5253,5185,5194,5267,5246,5206,5139,5127,5117,5073,5031,4936,4849,4783,4754,4716,4667,4558,4564,4467,4187,3413,3290,3094,3057,2973,2995,2957,2948,2960,2936,2731,2753,2732,2762,2633,2601,2574,2582,2591,2588,2579,2519,2332,2015&chxp=2,50&chxr=0,1880,2014,10|1,0,10000&chco=6611cc&chbh=a,0,2&chs=440x330&cht=bvg&chxl=2:|year+(CE)&chdl=step2.v2 "popularity of years in ccc-gistemp records")

`split_year.py` splits an GHCN-M dataset into those stations
that still report in a particular year, and those that don't.

`stationplot.py` (unless you use the `-y` option). It plots
station records as an SVG file.

