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
import modisDownload as download
from osgeo import gdal, gdalconst,gdal_array

DESC = "This script will recursively download all files if they don't exist from a LAADS URL and stores them to the specified path"

def makeLST8(rsb01,names,lst8path):
    if(rsb01 is  None):
        return

    areas = {'HuangHuaiHai': [482000, 3189000, 1574000, 4662000],
             'ChangJiangZhongXiaYou': [-704000, 2596000, 1574000, 3841000],
             'DongBei': [1033000, 4267000, 2207000, 5922000]}

    outputBounds = [-704000, 2596000, 2207000, 5922000]
    #   NdviFileName = '%s.%s.%s.%s.tif' % (names[0], names[1], names[3], 'HuangHuaiHai.ndvi')

    lst8FileName = 'MOD11A2.%s.%s.%s.tif' % ( names[1], names[3], "LST_8Day_1km")
    lst8File = os.path.join(lst8path, lst8FileName)
    gdal.Warp(lst8File, rsb01, outputBounds=outputBounds, xRes=1000, yRes=1000, srcNodata=-9999, dstNodata=-9999,
              outputType=gdal.GDT_Float32,
              dstSRS="+proj=aea +ellps=WGS84 +datum=WGS84 +lon_0=105 +lat_1=25 +lat_2=47 +units=m +")

    for name, bound in areas.items():
        areaLSTFileName = 'MOD11A2.%s.%s.%s.%s.tif' % (names[1], names[3],name,"LST_8Day_1km")
        areaLSTFile = os.path.join(lst8path, areaLSTFileName)
        gdal.Warp(areaLSTFile, lst8File, outputBounds=bound)




    outNdvi = None

def CalcLST8(files,filepath,lst8path):
    try:
        ll = []
        names = None
        for i in files:
            if( names is None):
                names = i.split('.')
            ll.append( 'HDF4_EOS:EOS_GRID:"%s":MODIS_Grid_8Day_1km_LST:LST_Day_1km' % ( os.path.join(filepath,i) ) )
        filename = 'MOD11A2.%s.%s.%s.tif' % ( names[1], names[3],'LST_8Day_1km')
        b01 = os.path.join( filepath,filename)
        rsb01 = gdal.Warp( b01,ll )
        ll.clear()



        makeLST8(rsb01,names,lst8path)


    except Exception as e:
        return True


def _main(argv):
    parser = argparse.ArgumentParser(prog=argv[0], description=DESC)
    parser.add_argument('-s', '--source', default='https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MOD11A2/2020',dest='source', metavar='URL', help='Recursively download files at URL', required=False)
    parser.add_argument('-d', '--destination', dest='destination', metavar='DIR', help='Store directory structure in DIR', required=True)

    parser.add_argument('-lst8', '--lst8', dest='lst8', metavar='DIR',help='Store directory structure in DIR', required=True)

    parser.add_argument('-start', '--start', dest='start', metavar='MUMBER', help='start day', required=True,type=int)
    parser.add_argument('-end', '--end',dest='end', metavar='MUMBER',
                        help='start day', required=True, type=int)

    args = parser.parse_args(argv[1:])
    gdal.AllRegister()
    if not os.path.exists(args.destination):
        os.makedirs(args.destination)
    choices = [i * 8 + 1 for i in range(46)]
    for i in range(int(args.start), int(args.end) + 1):
        if not i in choices:
            continue
        # i=args.day

        url = args.source + '/%03d' % i
        path = args.destination + r'\%03d' % i
        lst8path=args.lst8+ r'\%03d' % i

        if not 	os.path.exists(path):
            os.makedirs(path)
        if not os.path.exists(lst8path):
            os.makedirs(lst8path)

        #token在usgs上注册就有了
        downedfiles = download.sync(url, path, 'a token get from usgs')
        if (len(downedfiles) > 1):
            CalcLST8(downedfiles, path,lst8path)


# 7CCA54C2-C38A-11E8-B461-AFB1502E27AA
if __name__ == '__main__':
    try:
        sys.exit(_main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(-1)
    sys.exit(0)