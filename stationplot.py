#!/usr/bin/env python
#
# stationplot.py
#
# David Jones, Clear Climate Code, 2010-03-04
# David Jones, Climate Code Foundation, 2014-07
#
# Require Python 2.6.
#
# For testing purposes it might be interesting to note the following:
# 61710384000 longest timespan
# 10160400001 briefest timespan
# 22224266000 greatest temperature variation
# 50894004001 least temperature variation
# 30781001000 widest aspect ratio
# 21544218001 tallest aspect ratio

"""
Usage: python stationplot.py [options] station-id

The options are:
  [-c config]
  [--colour blue,black,...]
  [-d input/ghcnm.tavg.qca.dat]
  [--caption figure1]
  [--mode anom] [-a] [-y]
  [-o file.svg]
  [--offset 0,+0.2]
  [-t YYYY,YYYY]
  [--title title]
  [-s 0.01]

Tool to plot the records for a station.  Stations have an 11-digit
identifier. In GHCN-M v2 (now obsolete) each station can have several
"duplicate" records, each record having a single digit added, the
duplicate marker, to form a 12-digit record identifier.

Specifying an 11-digit identifier will plot the station (in the
case of a GHCN-M v2 file, all the duplicates associated with that
station shall be plotted); a 12-digit identifier will plot only a
single record.

Colours can be explicitly assigned using the --colour option.  A station
will be assigned its corresponding colour in the list of comma separated
colours, if that station identifier is associated with exactly one
record (in other words, if an 11 digit ID is used and there are several
associated station records, none of them will be coloured according to
the --colour option).

--mode controls whether temperatures or anomalies are plotted, and
controls monthly or annual resolution.  --mode requires an argument
which should be: 'anom' for monthly anomalies; 'annanom' for annual
anomalies (average of monthly anomalies; 6 required); 'annual' for
annual temperatures (annual anomalies with average climatology added
back). '-a' is obsolete shorthand for '--mode anom'; '-y' is obsolete
shorthand for '--mode annanom'.

Series can be offset vertically using the --offset option.  The argument
should be a comma separated list of offsets, each offset will be applied
to the corresponding station (positive offset will shift upwards,
negative downwards).  All of the duplicates for a station will be
offset by the same amount.

The -t option will restrict the time axis so that only records between
the beginning of the first year and the beginning of the second year are
displayed (in other words, the second year is excluded from the
displayed range).

Normally the output is an SVG document written to the file
station-id.svg (in other words, the first argument with ".svg" appended).
The -o option can be used to change where it written ("-o -" specifies stdout).

Normally the input is the GHCN-M v3 dataset input/ghcnm.tavg.qca.dat;
the -d option specifies an alternate input file ("-d -" for stdin).

Normally the input data is scaled according to the GHCN-M TAVG
convention (units of 0.01C for v3, 0.1C for v2).  The -s option
can be used to specify a different sized unit.

The -c option can be used to set various configuration options.  Best to
examine the source code for details.
"""

import codecs
import math
import os
import sys

# :todo: Should really import this from somewhere.  Although this BAD
# value is entirely internal to this module.
BAD = 9999

class Error(Exception):
    """
    Some sort of error.
    """

class Config:
    """
    A record of the configuration parameters used to style the plot.
    Just a struct really.
    """

config = Config()
config.debug = False
config.fontsize = 16
# Amount by which tick shoots out at the bottom.
config.overshoot = 16
# Pixels per year.
config.xscale = 6
# Pixels per degree C.
config.yscale = 10
config.rscale = 200
# Ticks on Y axis (in scaled data units, that is, degrees C).
config.ytick = 5
# Ticks on R axis.
config.rtick = 0.01
# Label on Y axis (None means it is magic).
config.ylabel = None
# Style of legend.  'pianola' or 'none'.
config.legend = 'pianola'
# Workaround a bug in InkScape when it renders the SVG to PDF.
config.buginkscapepdf = False

def derive_config(config):
    """
    Some configuration parameters are derived from others if they
    haven't been set.
    """

    def titlesize(c):
        c.titlesize = 1.25*c.fontsize

    d = dict(titlesize=titlesize)
    for attr,fn in d.items():
        if not hasattr(config, attr):
            fn(config)


# The hex colours come from
# http://www.personal.psu.edu/cab38/ColorBrewer/ColorBrewer.html
# (and reordered)
colour_list = """
blue
deeppink
green
orange
olive
navy
aqua
#745C12
gray
#1f77b4
#33a02c
#fb9a99
#cab2d6
#e31a1c
#fdbf6f
#ff7f00
#6a3d9a
#b2df8a
#a6cee3
""".split()

# https://docs.python.org/2/library/itertools.html#recipes
def grouper(seq, n):
    return zip(*[iter(seq)]*n)

def curves(series, K):
    """
    `series` is a (data,begin,axis) tuple (axis is ignored).
    The output is a number of curves, each curves specified by (x,y)
    pairs: Each input datum becomes a y-coordinate and its associated
    x-coordinate is its fractional year.  There is one curve for
    each contiguous chunk of data.

    The results are intended to be suitable for plotting.

    *K* is the number of data items per year.  This is 12 for monthly
    data; 1 for annual data.

    A sequence of lists is returned, each list being a list of
    (year, datum) pairs.  year will be a fractional year.
    """

    from itertools import groupby

    def enum_frac(data):
        """
        Like enumerate, but decorating each datum with a fractional
        year coordinate."""

        for m,datum in enumerate(data):
            yield (first + (m+0.5)/K, datum)

    data,first,_ = series

    for isbad,block in groupby(enum_frac(data), lambda x: x[1] == BAD):
        if isbad:
            continue
        yield list(block)

def get_titles(title, datadict, meta):
    if title:
        return title

    meta = get_meta(datadict, meta)
    if not meta:
        return ''

    a = []
    for id11,d in meta.items():
        a.append('%s %+06.2f%+07.2f  %s' %
          (id11, d['lat'], d['lon'], d['name']))
    # Note, the '\n' is an attempt to get SVG to use more than one
    # "line".  But it doesn't work.  So... :todo: fix that then.
    return '\n'.join(a)

def treat_mode(datadict, mode):
    """
    *datadict* is a dict, as returned by `select_records`.

    If `mode` is 'anom' then data are converted to monthly
    anomalies; if `mode` is 'annanom' then data are converted to annual
    anomalies (a simple average of monthly anomalies is used, as
    long as there are 6 valid months); if `mode` is 'annual'
    then data are converted to annual temperatures by first
    computing annual anomalies and then adding the average
    annual temperature (the average of the 12 monthly
    temperatures).
    
    Otherwise the data are not converted.

    A fresh dict is returned.
    """

    if mode not in ('anom', 'annual', 'annanom'):
        return dict(datadict)

    result = {}
    for key, tupl in datadict.iteritems():
        data = tupl[0]
        if mode == 'anom':
            data, _ = as_monthly_anomalies(data)
        if mode == 'annanom':
            data, _ = as_annual_anomalies(data)
        if mode == 'annual':
            data = as_annual_temps(data)
        result[key] = (data,) + tupl[1:]
    return result

def treat_offset(datadict, stations, offset):
    """
    *offset* can be used to offset each station.

    if `offset` is None then there is no effect and a fresh dict
    is returned with unmodified data.

    Otherwise, each station in `stations` has its data biased by adding
    *offset*.

    The visual effect is to displace stations upward (if the offset
    is positive).
    """

    result = dict(datadict)
    
    if not offset:
        return result

    for station,off in zip(stations, offset):
        data = datadict[station][0]
        data = apply_data_offset(data, off)
        result[station] = (data,) + datadict[station][1:]
    return result

def plot(stations, out, meta, colour=[], timewindow=None, mode='temp',
  offset=None, scale=None, caption=None, title=None, axes=None):
    """
    Create a plot of the stations specified in the list `stations`
    (each element is a `Station` instance that has a `source`
    and `id` property).  Plot is written to `out`.  Metadata (station
    name, location) is taken from the `meta` file.

    `mode` should be 'temp' to plot temperatures, or 'anom' to plot
    monthly anomalies.
    
    `timewindow` restricts the plot to a particular
    range of times: None means that the entire time range is plotted;
    otherwise, it should be a pair of numbers (y1,y2) and only records
    that have a time t where y1 <= t < y2 are displayed.  Normally y1
    and y2 are years in which case records from the beginning of y1 up
    to the beginning of y2 are displayed.
    """

    import itertools
    import struct

    def valid(datum):
        return datum != BAD

    datadict = select_records(stations, axes=axes, scale=scale)

    if not datadict:
        raise Error('No data found for %r' % stations)

    title = get_titles(title, datadict, meta)

    datadict = window(datadict, timewindow)

    datadict = treat_mode(datadict, mode)

    datadict = treat_offset(datadict, stations, offset)

    # Assign number of data items per year.
    global K # :todo: made not global.
    if mode.startswith('ann'):
        K = 1
    else:
        K = 12

    # Calculate first and last year, and highest and lowest temperature.
    minyear = 9999
    limyear = -9999
    # Max and mins for the data that are assigned to each of the two
    # vertical axes.
    axismax = dict(r=-9999, y=-9999)
    axismin = dict(r=9999, y=9999)
    for _,(data,begin,axis) in datadict.items():
        minyear = min(minyear, begin)
        limyear = max(limyear, begin + (len(data)//K))
        valid_data = filter(valid, data)
        ahigh = max(valid_data)
        alow = min(valid_data)
        axismax[axis] = max(axismax[axis], ahigh)
        axismin[axis] = min(axismin[axis], alow)
    # The data should be such that a station cannot have entirely
    # invalid data.  At least one year should have at least one valid
    # datum.
    assert axismax['y'] > -9999
    assert axismin['y'] < 9999

    axesused = [k for k,v in axismax.items() if v > -9999]

    # Bounds of the box that displays data.  In SVG viewBox format.
    databox = (minyear, axismin['y'],
      limyear-minyear, axismax['y']-axismin['y'])

    plotwidth = databox[2] * config.xscale

    # Bottom edge and top edge of plot area, after data has been scaled.
    # Forcing them to be integers means our plot can be aligned on
    # integer coordinates.
    bottom = {}
    top = {}
    for axis in 'yr':
        scale = getattr(config, axis+'scale')
        # Half a pixel of extra space top and bottom.
        smidgin = 0.5
        bottom[axis] = math.floor(axismin[axis]*scale-smidgin)
        top[axis] = math.ceil(axismax[axis]*scale+smidgin)
    del axis
    # The plot is sized according to the y axis (on the left); the r
    # axis is subsidiary.
    plotheight = top['y'] - bottom['y']
    legendh = legend_height(datadict)
    captionh = caption_height(caption)
    lborder = 125
    rborder = 65

    if title:
        # It's extremely difficult to find out the width of
        # of this piece of text when it's rendered to SVG.
        # So we make a reasonable estimate here.
        titlewidth = len(title) * config.titlesize * 0.70
    else:
        titlewidth = 0
    content_width = max(plotwidth, titlewidth)

    out.write("""<svg width='%.0fpx' height='%.0fpx'
      xmlns="http://www.w3.org/2000/svg"
      xmlns:xlink="http://www.w3.org/1999/xlink"
      version="1.1">\n""" %
      (content_width+lborder+rborder, plotheight+100+legendh+captionh))

    # Style
    out.write("""<defs>
  <style type="text/css">
    .debug { %s }
    path { stroke-width: 1.4; fill: none }
    path.singleton { stroke-width: 2.8; stroke-linecap: round }
    g#axes path { stroke-width:1; fill:none; stroke: #888 }
    g#legend path { stroke-width:1; fill:none }
    text { fill: black; font-family: Verdana }
""" % ('display: none', '')[config.debug])

    colours = itertools.chain(colour_list, colour_iter())
    # Assign colours from --colour argument, if and only if there is
    # exactly one entry in datadict corresponding to the station id.
    # :todo: currently just assumes there is always exactly one
    # such entry (fixing it will mean working with GHCN-M duplicates).
    colourdict = {}
    for key,c in zip(stations,colour):
        colourdict[key] = c
    for station,c in zip(sorted(datadict, key=lambda s:s.id), colours):
        c = colourdict.get(station, c)
        cssidescaped = cssidescape(station.classname())
        out.write("    g.%s { stroke: %s }\n" % (cssidescaped, c))
    out.write("  </style>\n</defs>\n")

    # Push chart down and right to give a bit of a border.
    with Tag(out, 'g', attr=dict(transform=('translate(%.1f,80)' % lborder))):
      # In this section 0,0 is at top left of chart, and +ve y is down.
      if title:
          with Tag(out, 'g', attr=dict(id='title')):
              out.write(
                "  <text font-size='%.1f' x='0' y='-4'>%s</text>\n" %
                (config.titlesize, title))

      # Transform so that (0,0) on chart is lower left
      out.write("<g transform='translate(0, %.1f)'>\n" % plotheight)
      # In this section 0,0 should coincide with bottom left of chart,
      # but oriented as per SVG default.  +ve y is down.
      # We are 1-1 with SVG pixels.
      # Use yscale and xscale to scale to/and from data coordinates.

      # Colour legend.
      with Tag(out, 'g', attr=dict(id='legend')):
          ly = render_legend(out, datadict, minyear)

      # Caption, below legend.
      if caption:
          with Tag(out, 'g', attr=dict(id='caption')):
              render_caption(out, ly, caption)

      # Start of "axes" group.
      out.write("<g id='axes'>\n")
      w = limyear - minyear
      # Ticks on the horizontal axis.
      s = (-minyear)%10
      # Where we want ticks, in years offset from the earliest year.
      # We have ticks every decade.
      tickat = range(s, w+1, 10)
      out.write("  <path d='" +
        ''.join(map(lambda x: 'M%d %.1fl0 %.1f' %
        (x*config.xscale, config.overshoot, -(plotheight+config.overshoot)),
        tickat)) +
        "' />\n")
      # Horizontal labels.
      for x in tickat:
          out.write("  <text text-anchor='middle'"
            " font-size='%.1f' x='%d' y='%d'>%d</text>\n" %
            (config.fontsize, x*config.xscale, config.overshoot, minyear+x))
      # Vertical axis.
      with Tag(out, 'g', attr={'id':'vaxis',
        'font-size':('%.1f' % config.fontsize),}):
          for axis in axesused:
              render_vaxis(out, axis, mode, bottom, top, plotwidth)

          # Horizontal rule at datum==0
          out.write("  <path d='M0 %.1fl%.1f 0' />\n" %
            (bottom['y'], plotwidth))

      # End of "axes" group.
      out.write("</g>\n")

      # Transform so that up (on data chart) is +ve.
      with Tag(out, 'g', attr=dict(transform='scale(1, -1)')):
          xdatabox = (0, 0, databox[2]*config.xscale,
            databox[3]*config.yscale)
          out.write("""<rect class='debug'
            x='%d' y='%.1f' width='%d' height='%.1f'
            stroke='pink' fill='none' opacity='0.30' />\n""" % xdatabox)

          def scale(points, vaxis='y'):
              """
              Take a sequence of (year,datum) pairs and scale onto
              the databox (which has 0,0 at lower left and is 1 to 1
              with SVG pixels)).

              *minyear* and *config.xscale* are used to scale the
              x value.

	      There can be multiple vertical axes and multiple
	      scales.  If *vaxis* is 'y' then *y* values are
	      transformed into (y*config.yscale - ybottom); if
	      *vaxis* is 'r' (for right) then *y* values are
	      transformed into (y*config.rscale - rbottom).
              """

              subtrahend = bottom[vaxis]
              vscale = getattr(config, vaxis+'scale')

              scaled = [((x-minyear)*config.xscale, y*vscale - subtrahend)
                for x,y in points]
              return scaled

          for station in stations:
              if station not in datadict:
                  # No data, or removed by windowing.
                  continue
              series = datadict[station]
              out.write("<g class='%s'>\n" % station.classname())
              axis = series[2]
              for segment in curves(series, K):
                  out.write(aspath(scale(segment, axis))+'\n')
              out.write("</g>\n")
      out.write("</g>\n")
    out.write("</svg>\n")


class Tag(object):
    """
    Use in the 'with' statement in order to automatically balance XML
    tags.
    """

    def __init__(self, out, name, attr):
        """
        Create a context manager (with __enter__ and __exit__
        methods) that will write out the start and end tags.
        """

        self.out = out
        self.name = name
        self.attr = attr

    def __enter__(self):
        # http://docs.python.org/release/2.5.4/lib/module-xml.sax.saxutils.html
        from xml.sax.saxutils import quoteattr

        self.out.write("<%s" % self.name)
        for name,value in self.attr.items():
            self.out.write(' %s=%s' % (name, quoteattr(value)))
        self.out.write('>\n')

    def __exit__(self, *_):
        self.out.write("</%s>\n" % self.name)

            
def legend_height(datadict):
    """
    Height of the legend.  Seems to include the x-axis label (?).
    """

    if config.legend == 'pianola':
        return config.fontsize*(len(datadict)+1)
    else:
        return config.fontsize

def caption_height(caption):
    """
    Height of the caption.
    """

    # :todo: not very general.
    return 1.5 * config.fontsize

def render_legend(out, datadict, minyear):
    """
    Write the SVG for the legend onto the stream *out*.  Return the
    lowest y coordinate used.
    """


    if config.legend == 'pianola':
        return render_pianola(out, datadict, minyear)

def render_pianola(out, datadict, minyear):
    """
    Render the pianola legend.
    """

    import itertools

    # Includes range indicators for each series.
    # Start of the top line of text for the legend.
    yleg = config.overshoot+config.fontsize
    yleg += 0.5
    for i,(station,(data,begin,_)) in enumerate(
      sorted(datadict.items(), key=lambda p: p[0].id)):
        length = len(data)//K
        y = yleg + config.fontsize*i
        out.write("  <text alignment-baseline='middle'"
          " text-anchor='end' x='0' y='%.1f'>%s</text>\n" %
          (y, station.id))
        classname = station.classname()
        with Tag(out, 'g', {'class': classname}):
            for is_bad, block in itertools.groupby(
              enumerate(data), lambda x: x[1] == BAD):
                if is_bad:
                    continue
                l = list(block)
                length = float(len(l)) / K
                b = float(l[0][0]) / K
                out.write("<path d='M%.1f %.1fl%.1f 0' />" %
                  ((begin-minyear+b)*config.xscale, y, length*config.xscale))
    return y

def render_caption(out, y, caption):
      """*
      y* is the y coordinate of the bottom edge of the printed
      region immediately above the caption (which is normally the
      legend).
      """

      # :todo: Abstract; multi-line; XML escape.
      out.write("  <text font-size='%.1f' x='0' y='%.1f'>" %
        (config.fontsize, y+caption_height(caption)))
      out.write(caption + "</text>\n")

def render_vaxis(out, axis, mode, bottom, top, plotwidth):
    """
    Either the 'y' (on left) or the 'r' axis (on right).
    """

    # In this function, (0,0) is the bottom left of the chart,
    # and +ve y is downwards (same as initial SVG system). We
    # are 1 to 1 with SVG pixels.

    # Mostly this function uses positive values for y
    # coordinates above the bottom of the chart; they are
    # negated immediately before writing the SVG.

    if 'y' == axis:
        anchor = 'end'
        # x coordinate of the axis to be drawn.
        xcoord = 0
        # *tickvec* is negative (to the left) for the y-axis.
        tickvec = -8
    else:
        anchor = 'start'
        xcoord = plotwidth
        # *tickvec* is positive (to the right) for the r-axis
        # (which is drawn on the right of the chart).
        tickvec = 8

    with Tag(out, 'g', attr={'text-anchor':anchor}):
        vscale = getattr(config, axis+'scale')
        tick = getattr(config, axis+'tick')
        # Height, in pixels, of the range of data on this axis.
        height = top[axis] - bottom[axis]

        # Ticks on the vertical axis.
        # Ticks every *tick* degrees C.
        every = tick*vscale
        # Works best when *every* is an integer.
        assert int(every) == every
        every = int(every)
        # *s* the offset, in pixels, of the lowest tick from the
        # bottom of the chart.
        s = (-bottom[axis]) % every
        # Works best when *s* is an integer.
        assert int(s) == s
        s = int(s)
        slimit = height+1
        if (slimit - s) // every == 0:
            # Only one tick mark, make it easier to get another one.
            nearly = 0.6
        else:
            nearly = 0.8
        if 0: print(dict(top=top[axis], bottom=bottom[axis],
          every=every, s=s, slimit=slimit, nearly=nearly))
        # If the top is nearly at a tick mark, force an extra tick mark.
        if (slimit % every) > nearly * every:
            slimit += every
        tickat = range(s, int(slimit), every)
        # The actual tick marks.
        out.write("  <path d='" +
          ''.join(['M%.1f %.1fl%d 0' % (xcoord, -y, tickvec)
            for y in tickat]) +
          "' />\n")

        # The labels for the ticks.
        # *prec* gives the number of figures after the decimal point
        # for the y-axis tick label.
        prec = -int(round(math.log10(tick) - 0.001))
        prec = max(0, prec)
        tickfmt = '%%.%df' % prec
        # Correct for a bug when InkScape renders to PDF.
        # (alignment-baseline is ignored, and the labels are a
        # half-line too high).
        if config.buginkscapepdf:
            yoffset = config.fontsize * 0.3
        else:
            yoffset = 0
        for y in tickat:
            out.write(("  <text alignment-baseline='middle'"
              " x='%.1f' y='%.1f'>" + tickfmt + "</text>\n") %
              (xcoord+tickvec, -y+yoffset, (y+bottom[axis])/float(vscale)))

        # Vertical label.  Only for y axis.
        if 'y' == axis:
            out.write(
              "  <defs><path id='pvlabel' d='M-%d %.1fl0 -800'/></defs>\n" %
              (3.5*config.fontsize-8, -height*0.5+400))
            # :todo: make label configurable.
            if config.ylabel is None:
                label = 'Anomaly'
                if 'temp' in mode:
                    label = 'Temperature'
                label += u" (\N{DEGREE SIGN}C)"
            else:
                label = config.ylabel
            out.write("  <text text-anchor='middle'>"
              "<textPath xlink:href='#pvlabel' startOffset='50%%'>"
              u"%s</textPath></text>\n" % label)

def cssidescape(identifier):
    """
    Escape an identifier so that it is suitable for use as a CSS
    identifier.  See http://www.w3.org/TR/CSS2/syndata.html.
    """

    import re

    def f(m):
       return '\\'+m.group()

    x0 = identifier[0]

    # Escape all but initial character.
    x = re.sub(r'([^a-zA-Z0-9_-])', f, identifier[1:])
    # Initial character needs escaping too.
    if x0 in '0123456789':
        x0 = '\\%02x' % ord(x0)
    elif not re.match(r'^[a-zA-Z_]', x0):
        x0 = '\\' + x0
    return x0 + x

def window(datadict, timewindow):
    """
    Restrict the data series in *datadict* to be between the two
    times specified in the `timewindow` pair.  A fresh dict is returned.
    """

    if timewindow is None:
        return dict(datadict)

    # Number of data items per year.
    K = 12

    t1,t2 = timewindow
    # The window must be on a year boundary to preserve the fact that
    # data is a multiple of 12 long.
    assert int(t1) == t1
    assert int(t2) == t2
    d = {}
    for station, tup in datadict.items():
        (data, begin) = tup[:2]
        if t2 <= begin:
            continue
        end = begin+len(data)//K
        if end <= t1:
            continue
        if t2 < end:
            data = data[:K*(t2-end)]
        if begin < t1:
            data = data[K*(t1-begin):]
            begin = t1
        d[station] = (data, begin) + tup[2:]
    return d

def get_meta(stations, meta):
    """
    For the stations in `stations`, get the metadata
    extracted from the file `meta`.  A dictionary is returned that
    maps from 11-digit id to an info dictionary.  The info
    dictionary has keys: name, lat, lon (and maybe more in future).
    """

    # :todo: it only ends up using one metadata file; really
    # ought to allow different stations to have different metadata
    # files.

    sources = [s.source for s in stations]
    for source in sources:
        m = open_metafile(meta, source)
        if m:
            break
    meta = m
    if not meta:
        return

    full = {}
    for line in meta:
        id = line[:11]
        # Guess the format, v2 or v3, from the line length.
        if len(line) in (69, 108):
            # 108 is true GHCN-M v3.
            # 69 is ISTI's emulation of GHCN-M v3 format.
            full[id] = dict(
                name=line[38:70].strip(),
                lat=float(line[12:20]),
                lon=float(line[21:30]),
            )
        else:
            # GHCN-M v2
            full[id] = dict(
                name = line[12:42].strip(),
                lat = float(line[43:49]),
                lon = float(line[50:57]),
            )
    d = {}
    ids = set(s.id[:11] for s in stations)
    for id11 in ids:
        if id11 in full:
            d[id11] = full[id11]
    return d

def aspath(l):
    """
    Encode a list of data points as an SVG path element.  The element
    is returned as a string.
    """

    assert len(l) > 0

    # Format an (x,y) tuple.
    def fmt(t):
        return "%.3f %.1f" % (t[0], t[1])

    d = 'M'+fmt(l[0])+'L'+' '.join(map(fmt, l[1:]))
    decorate = ''
    if len(l) == 1:
        # For singletons we:
        # - draw a length 0 segment to force a real stroke;
        # - add a class attribute so that they can be styled with larger
        # blobs.
        assert d[-1] == 'L'
        d = d[:-1] + 'l 0 0'
        decorate = "class='singleton' "
    return "<path %sd='%s' />" % (decorate, d)

# Pasted from
# http://code.google.com/p/ccc-gistemp/source/browse/trunk/code/step1.py?r=251
# :todo: abstract properly.
def from_years(years):
    """
    *years* is a list of year records (lists of temperatures) that
    comprise a station's entire record.  The data are converted to a
    linear array (could be a list/tuple/array/sequence, I'm not
    saying), *series*, where series[m] gives the temperature (a
    floating point value in degrees C) for month *m*, counting from 0
    for the January of the first year with data.

    (*series*,*begin*) is returned, where *begin* is
    the first year for which there is data for the station.

    This code is also in step0.py at present, and should be shared.
    """

    begin = None
    # Previous year.
    prev = None
    series = []
    for (year, data) in years:
        if begin is None:
            begin = year
        # The sequence of years for a station record is not
        # necessarily contiguous.  For example "1486284000001988" is
        # immediately followed by "1486284000001990", missing out 1989.
        # Extend with blank data.
        while prev and prev < year-1:
            series.extend([BAD]*12)
            prev += 1
        prev = year
        series.extend(data)
    return (series, begin)

def from_months(months):
    """
    Convert into linear array and starting year, as per
    from_years, but handling the case when the input is a series
    of (year, month, value) triples. (month is 0-based)
    """

    series = []
    # First year.
    begin = None
    # Previous month counting 0 as January year 0.
    prev = None
    for year, month, value in months:
        if begin is None:
            begin = year
            prev = year*12 - 1
        m = year * 12 + month
        while prev+1 < m:
            series.append(BAD)
            prev += 1
        prev = m
        series.append(value)
    return (series, begin)


def from_lines(lines, scale=None):
    """
    *lines* is a list of lines (strings) that comprise a station's
    entire record.  The lines are expected to be an extract from a
    file in the GHCN-M format (either v2 or v3), or ISTI format.

    The data are converted to a linear array (could be a
    list/tuple/array/sequence, I'm not saying), *series*, where
    series[m] gives the temperature (a floating point value in degrees
    C) for month *m*, counting from 0 for the January of the first
    year with data.

    (*series*,*begin*) is returned, where *begin* is
    the first year for which there is data for the station.

    Invalid data are marked in the input file with -9999 but are
    translated in the data arrays to BAD.

    In the case of ISTI files (in either GHCN-M v3 format or
    native ISTI format), only TAVG values are extracted.
    """

    # :todo: it is a bit ugly that this function handles both
    # year-per-row (GHCN) and month-per-row (ISTI).

    # Used for GHCN-M (v2 and v3) format.
    years = []
    # Used for ISTI format.
    months = []
    # Year from previous line.
    prev = None
    # The previous line itself.
    prevline = None
    for line in lines:
        if len(line) == 116:
            # GHCN-M v3
            format = 'v3'
        elif len(line) == 133:
            # ISTI
            format = 'isti-v1'
        else:
            # GHCN-M v2
            format = 'v2'

        if 'isti-v1' == format:
            field = line.split()
            date = field[4]
            month = int(date[4:6]) - 1
            year = int(date[:4])
            value = int(field[7]) * 0.01
            months.append((year, month, value))
            continue

        if 'v3' == format:
            element = line[15:19]
            if element != 'TAVG':
                continue

        if 'v3' == format:
            year = int(line[11:15])
        else:
            year = int(line[12:16])
        if prev == year:
            # There is one case where there are multiple lines for the
            # same year for a particular station.  Some versions
            # of the v2.mean input file have 3 identical lines for
            # "8009991400101971" (this bug in the data file is
            # believe to be functionally extinct as of 2014).
            if line == prevline:
                print "NOTE: repeated record found: Station %s year %s; data are identical" % (line[:12],line[12:16])
                continue
            # This is unexpected.
            if 'v2' == format:
                q = 16
            else:
                q = 15
            assert 0, "Two lines specify different data for %s" % line[:q]
        # Check that the sequence of years increases.
        assert not prev or prev < year

        prev = year
        prevline = line
        temps = []
        for m in range(12):
            if len(line) == 116:
                # GHCN-M v3
                datum = int(line[19+8*m:24+8*m])
                default_scale = 0.01
            else:
                # GHCN-M v2
                datum = int(line[16+5*m:21+5*m])
                default_scale = 0.1
            if datum == -9999:
                datum = BAD
            else:
                # Convert to floating point and degrees C.
                datum *= scale or default_scale
            temps.append(datum)
        years.append((year, temps))

    assert months or years
    assert not (months and years)

    if years:
        return from_years(years)
    if months:
        return from_months(months)

def as_monthly_anomalies(data):
    """
    Convert `data`, which should be a sequence of monthly values,
    to a sequence of monthly _anomalies_. This is done by
    computing the _climatology_ (mean value for each named
    calendar month), and
    subtracting that from each corresponding monthly datum.

    A pair of (monthly_anomalies, climatology) is returned.
    """

    import itertools

    # One mean for each of 12 months.
    climatology = []
    for m in range(12):
        monthly_data = [data[i] for i in range(m, len(data), 12)]
        monthly_data = [datum for datum in monthly_data if datum != BAD]
        if monthly_data:
            mean = float(sum(monthly_data)) / len(monthly_data)
        else:
            mean = BAD
        climatology.append(mean)

    def sub1(datum, mean):
        """
        Subtract mean from datum, taking into account BAD data.
        """
        if datum == BAD:
            return BAD
        return datum - mean

    anomalies = [sub1(datum, mean)
      for datum, mean in zip(data, itertools.cycle(climatology))]
    return anomalies, climatology

def as_annual_anomalies(data):
    """
    A pair of (annual_anomalies, annual_average) is returned.
    """
    monthlies, average_monthly_temp = as_monthly_anomalies(data)
    yearly_blocks = grouper(monthlies, 12)

    def mean12(data):
        good_data = [x for x in data if x != BAD]
        if len(good_data) < 6:
            return BAD
        return sum(good_data) / float(len(good_data))

    annual_anomalies = [mean12(block) for block in yearly_blocks]
    return annual_anomalies, mean12(average_monthly_temp)

def as_annual_temps(data):
    anoms, average_temp = as_annual_anomalies(data)
    def to_temp(d):
        if d == BAD:
            return d
        return d + average_temp
    return [to_temp(d) for d in anoms]

# :todo: fix for GHCN-M v2. It used to produce multiple results,
# one for each duplicate of a station.
def select_records(stations, axes, scale=None):
    """
    `stations` should be a list of `Station` instances.
    
    The records for these stations are extracted
    and returned as a dictionary that maps `Station` instance to
    (data,begin,axis) tuple.
    """

    sources = [s.source for s in stations]

    # dict of indexed record files.
    index = dict((source, fast_access(source)) for source in sources)

    table = {}
    if not axes:
        axes = 'y' * len(stations)

    for station,axis in zip(stations, axes):
        for id12,rows in index[station.source].get(station.id):
            data,begin = from_lines(rows, scale)
            table[station] = (data,begin,axis)

    return table

class ISTI_data:
    def __init__(self, source):
        self.source = source

    def get(self, id):
        yield (id, open(self.source).readlines())

def fast_access(source):
    """
    Arrange "fast access" to the file of station records `source`.
    The protocol is that this function returns an object with a
    .get() method, which when called with a station id returns
    a sequence of (id, rows) pairs.
    """

    # ghcntool directory
    import ghcnm_index

    if source.endswith("_monthly_stage2"):
        # An ISTI record, which is not optimised.
        return ISTI_data(source)
    else:
        return ghcnm_index.File(source)

def apply_data_offset(data, offset):
    def off(x):
        if x != BAD:
           return x+offset
        return x
    return [off(x) for x in data]

def colour_iter(background=(255,255,255)):
    """
    Generate a random sequence of colours, all different.
    """

    import random

    def distance(u, v):
        return sum((p-q)**2 for p,q in zip(u,v))**0.5

    # Internally all colour components are from 0 to 1; so convert
    # background.
    background = [c/255.0 for c in background]
    
    # Randomly generate colours and check that they are distance *b*
    # from the background colour and *r* from each other.  If we take
    # too many tries to find one... Make *r* smaller.

    b = 0.3
    r = 0.4
    # Ratio to reduce *r* by
    s = 0.7
    # Number of failures before reducing *r*.
    n = 8
    # List of all colours generated.
    l = []
    # Number of fails.
    fail = 0
    while 1:
        c = [random.random() for _ in range(3)]
        if (distance(c, background) > b and
          all(distance(c, x) > r for x in l)):
            yield "#%02x%02x%02x" % tuple(round(255*x) for x in c)
        fail += 1
        if fail > n:
            fail = 0
            r *= s


def update_config(config, v):
    """
    *config* is a configuration object used to store parameters.  *v*
    is an argument string of the form "parm1=value1;parm2=value2;...".
    Each "parm=value" pair sets an attribute of the config object.
    """

    l = v.split(';')
    for binding in l:
        attr,value = binding.split('=')
        attr = attr.strip()
        value = value.strip()
        for convert in [int, float, str]:
            try:
                value = convert(value)
                break
            except ValueError:
                pass
        setattr(config, attr, value)
    return config

def parse_topt(v):
    """
    Parse the t option which restricts the years to a particular
    range.  *v* is a string that is 2 (4-digit) years separated by a
    comma.  A pair of years is returned.
    """

    return map(int, v.split(','))

def open_metafile(metafile, inp):
    """
    `metafile` and `inp` are both filenames.
    """

    if metafile:
        # Name of metafile supplied. Open it.
        return open(metafile)

    # A series of defaults to try...
    names = ['input/v3.inv', 'input/v2.inv']
    # ... including a default based on the name of the input.
    if inp.endswith('.dat'):
        metaname = inp[:-4] + '.inv'
        names = [metaname] + names
    for name in names:
        try:
            metafile = open(name)
            return metafile
        except IOError:
            pass

class Usage(Exception):
    pass

def opt_one(arg, single=''):
    """
    Process a single optional argument from the argument list
    `arg`. An option is assumed be allowed to have an optional
    value associated with it, unless it is one of the single
    chatacter arguments in `single`.

    A pair (opt, v) is returned where `opt` starts with either
    '-' or '--'.
    """

    # :todo: Doesn't work for --style arguments that don't have
    # a value (would need to change interface).

    if arg[0].startswith('--'):
        if arg[0].find('=') >= 0:
            i = arg[0].index('=')
            opt = arg[0][:i]
            v = arg[0][1+1:]
            del arg[0]
            return opt,v
        else:
            opt = arg[0]
            v = arg[1]
            del arg[:2]
            return opt,v
    elif arg[0].startswith('-'):
        opt = arg[0][:2]
        if arg[0][1] in single:
            # We're allowed to specify multiple single arguments
            # in one go. EG: cmd -abc --extra=fun
            v = None
            if len(arg[0]) == 2:
                del arg[0]
            else:
                arg[0] = '-' + arg[0][2:]
            return opt,v
        else:
            # Could have value in same arg, or as extra arg:
            # -fname -f name.
            if len(arg[0]) == 2:
                v = arg[1]
                del arg[:2]
            else:
                v = arg[0][2:]
                del arg[0]
            return opt,v
        
def main(argv=None):
    import sys
    if argv is None:
        argv = sys.argv

    infile = 'input/ghcnm.tavg.qca.dat'
    metafile = None
    outfile = None

    arg = argv[1:]
    key = {}
    while arg:
        if not arg[0].startswith('-'):
            break
        opt, v = opt_one(arg, single='ay')
        if opt == '--axes':
            key['axes'] = v
        if opt == '--caption':
            key['caption'] = v
        if opt == '--colour':
            key['colour'] = v.split(',')
        if opt == '-c':
            update_config(config, v)
        if opt == '--mode':
            key['mode'] = v
        if opt == '--offset':
            key['offset'] = [float(x) for x in v.split(',')]
        if opt == '-a':
            key['mode'] = 'anom'
        if opt == '-o':
            outfile = v
        if opt == '-d':
            infile = v
        if opt == '-m':
            metafile = v
        if opt == '-t':
            key['timewindow'] = parse_topt(v)
        if opt == '--title':
            key['title'] = v
        if opt == '-y':
            key['mode'] = 'annanom'
        if opt == '-s':
            key['scale'] = float(v)
    if not arg:
        return usage('At least one identifier must be supplied.')
    outfile = prepare_outfile(outfile, arg)

    """
    if infile == '-':
        infile = sys.stdin
    else:
        infile = open(infile)
    metafile = open_metafile(metafile, infile)
    """

    derive_config(config)

    stations = []
    while arg:
        if arg[0] == '-d':
            infile = arg[1]
            arg = arg[2:]
        else:
            stations.append(Station(id=arg[0], source=infile))
            arg = arg[1:]

    return plot(stations, out=outfile, meta=metafile, **key)

class Station:
    def __init__(self, **k):
        self.__dict__.update(k)

    def __repr__(self):
        return "Station(**%r)" % self.__dict__

    def classname(self):
        """
        A classname suitable for using as an SVG class attribute.
        """
        return 'record-%s-%s' % (self.source, self.id)

def prepare_outfile(outfile, arg):
    """
    Pick an outfile and return it as a UTF-8 encoded writable
    stream.
    """

    if outfile is None:
        outfile = arg[0] + '.svg'
    if outfile == '-':
        outfile = sys.stdout
    else:
        outfile = open(outfile, 'w')
    # See http://drj11.wordpress.com/2007/05/14/python-how-is-sysstdoutencoding-chosen/#comment-3770
    return codecs.getwriter('utf-8')(outfile)

def usage(m):
    if m:
        sys.stdout.write('%s\n' % str(m))
    sys.stdout.write(__doc__)
    return 99

if __name__ == '__main__':
    sys.exit(main())
