#!/usr/bin/env python

# script supports either python2 or python3
#
# Attempts to do HTTP Gets with urllib2(py2) urllib.requets(py3) or subprocess
# if tlsv1.1+ isn't supported by the python ssl module
#
# Will download csv or json depending on which python module is available
#

from __future__ import (division, print_function, absolute_import, unicode_literals)

import argparse
import os
import os.path
import shutil
import sys
import time
import numpy
import wget
import modisDownload as download
from osgeo import gdal, gdalconst,gdal_array

def clipLaiandFpar(fpar,lai,names,FparPath,LaiPath):
    area = [482000, 3189000, 1574000, 4662000];
    outputBounds = [-704000, 2596000, 2207000, 5922000];

    fparFileName = 'MCD13A3H.%s.%s.%s.tif' % (names[1],names[3],"fpar");
    fparFile = os.path.join(FparPath,fparFileName);
    print(fparFile);
    gdal.Warp(fparFile, fpar, outputBounds=outputBounds, xRes=1000, yRes=1000, srcNodata=-9999, dstNodata=-9999,
              outputType=gdal.GDT_Float32,
              dstSRS="+proj=aea +ellps=WGS84 +datum=WGS84 +lon_0=105 +lat_1=25 +lat_2=47 +units=m +")

    fparHHHFileName = 'MCD13A3H.%s.%s.%s.tif' % (names[1], names[3], "huanghuaihai.fpar");
    fparHHHFile = os.path.join(FparPath,fparHHHFileName);
    gdal.Warp(fparHHHFile,fparFile,outputBounds=area);

    laiFileName = 'MCD13A3H.%s.%s.%s.tif' % (names[1], names[3], "lai");
    laiFile = os.path.join(LaiPath, laiFileName);
    gdal.Warp(laiFile, lai, outputBounds=outputBounds, xRes=1000, yRes=1000, srcNodata=-9999, dstNodata=-9999,
              outputType=gdal.GDT_Float32,
              dstSRS="+proj=aea +ellps=WGS84 +datum=WGS84 +lon_0=105 +lat_1=25 +lat_2=47 +units=m +")

    laiHHHFileName = 'MCD13A3H.%s.%s.%s.tif' % (names[1], names[3], "huanghuaihai.lai");
    laiHHHFile = os.path.join(LaiPath,laiHHHFileName);
    gdal.Warp(laiHHHFile,laiFile,outputBounds=area);


def CalLAIandFpar(files,filepath,LaiPath,FparPath):
    try:
        ll=[];
        names = None;
        for i in files:
            if(names is None):
                names = i.split('.');
            print(i);
            ds = gdal.Open(i);
            subdatasets = ds.GetSubDatasets();
            ll.append(subdatasets[0][0]);
        filename = '%s.%s.%s.%s.tif' % (names[0], names[1], names[3], 'Fpar_500m');
        fpar = gdal.Warp(filename, ll)
        ll.clear()

        for i in files:
            if (names is None):
                names = i.split('.');
            print(i);
            ds = gdal.Open(i);
            subdatasets = ds.GetSubDatasets();
            ll.append(subdatasets[1][0]);
        filename = '%s.%s.%s.%s.tif' % (names[0], names[1], names[3], 'Lai_500m');
        lai = gdal.Warp(filename, ll)
        ll.clear()

        clipLaiandFpar(fpar,lai,names,FparPath,LaiPath);

    except Exception as e:
        return True;

DESC = "This script will recursively download all files if they don't exist from a LAADS URL and stores them to the specified path"

def _main(argv):
    parser = argparse.ArgumentParser(prog=argv[0], description=DESC)
    parser.add_argument('-s', '--source',default='https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MCD15A3H/2007', dest='source', metavar='URL', help='Recursively download files at URL', required=False)
    parser.add_argument('-d', '--destination', dest='destination', metavar='DIR', help='Store directory structure in DIR', required=True)
    parser.add_argument('-fpar', '--fpar', dest='fpar', metavar='DIR',help='Store directory structure in DIR', required=True)
    parser.add_argument('-lai', '--lai', dest='lai', metavar='DIR', help='Store directory structure in DIR',required=True)
    parser.add_argument('-start','--start',dest='start',metavar='MUMBER',help='start day', required=True)
    parser.add_argument('-end', '--end', dest='end', metavar='MUMBER', help='end day', required=True)

    args = parser.parse_args(argv[1:])
    gdal.AllRegister()
    if not os.path.exists(args.destination):
        os.makedirs(args.destination)
    choices = [i*4+1 for i in range(92)]

    fparPath = args.fpar;
    laiPath = args.lai;
    if not os.path.exists(fparPath):
        os.makedirs(fparPath)
    if not os.path.exists(laiPath):
        os.makedirs(laiPath)
    for i in range(int(args.start),int(args.end)):
        if not i in choices:
            continue;
        url = args.source + '/%03d' % i
        path = args.destination + r'\%03d' % i

        print(i)
        print( url )
        print( path)
        if not 	os.path.exists(path):
            os.makedirs(path)
        downedfiles = download.sync(url, path, 'your own Token,which get from usgs')
        CalLAIandFpar(downedfiles, path, laiPath, fparPath)

# 7CCA54C2-C38A-11E8-B461-AFB1502E27AA
if __name__ == '__main__':
    try:
        sys.exit(_main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(-1)