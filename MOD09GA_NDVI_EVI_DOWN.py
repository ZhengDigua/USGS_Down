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


def makeNDVIandEVI(state_1,rsb01,rsb02,rsb03 , names, NdviPath, EviPath):
    areas = {'HuangHuaiHai': [482000, 3189000, 1574000, 4662000],
             'ChangJiangZhongXiaYou': [-704000, 2596000, 1574000, 3841000],
             'DongBei': [1033000, 4267000, 2207000, 5922000]}

    outputBounds = [-704000, 2596000, 2207000, 5922000]
    if(state_1 is None):
        print("state_1 is None")
        return
    if(rsb01 is  None):
        return
    if(rsb02 is  None):
        return
    if(rsb03 is None):
        return

    #state1是对遥感的像元质量检测，去掉没有云的
    state1 = gdal_array.BandReadAsArray(state_1.GetRasterBand(1))
    b3 = gdal_array.BandReadAsArray(rsb03.GetRasterBand(1))
    b2 = gdal_array.BandReadAsArray(rsb02.GetRasterBand(1))
    b1 = gdal_array.BandReadAsArray(rsb01.GetRasterBand(1))

    ## NDVI
    ndvi = ((b2 - b1) * 1.0) / ((b2 + b1) * 1.0)
    ndvi[numpy.isnan(ndvi)] = -9999
    ndvi[numpy.isinf(ndvi)] = -9999

    ndvi[ndvi > 1] = -9999
    ndvi[ndvi < -1] = -9999
    nodata = rsb02.GetRasterBand(1).GetNoDataValue()
    ndvi[b2 == nodata] = -9999

    nodata = rsb01.GetRasterBand(1).GetNoDataValue()
    ndvi[b1 == nodata] = -9999

    try:
        state1_10 = state1 << 10
        for i in range(0,3600):
            for j in range(0,3600):
                if state1_10[i][j]==0 :
                    ndvi[2*i][2*j] = -9999;
                    ndvi[2*i][2*j+1] = -9999;
                    ndvi[2*i+1][2*j] = -9999;
                    ndvi[2*i+1][2*j+1] = -9999;
    except Exception as e:
        print(e)

    outNdvi = gdal_array.SaveArray(ndvi, "fgf", format="MEM", prototype=rsb01)

    NdviFileName = 'MOD09GA.%s.%s.%s.tif' % ( names[1], names[3], 'ndvi')
    NdviFile = os.path.join(NdviPath, NdviFileName)
    gdal.Warp(NdviFile, outNdvi, outputBounds=outputBounds, xRes=1000, yRes=1000, srcNodata=-9999, dstNodata=-9999,
              outputType=gdal.GDT_Float32,
              dstSRS="+proj=aea +ellps=WGS84 +datum=WGS84 +lon_0=105 +lat_1=25 +lat_2=47 +units=m +")

    #only huanghuaihai
    
    areaNdviFileName = 'MOD09GA.%s.%s.%s.tif' % (names[1], names[3], 'huanghuaihai.ndvi')
    areaNdviFile = os.path.join(NdviPath, areaNdviFileName)
    gdal.Warp(areaNdviFile, NdviFile, outputBounds=[482000, 3189000, 1574000, 4662000])
    

    #only dongbei
    '''
    areaNdviFileName = 'MOD09GA.%s.%s.%s.tif' % (names[1], names[3], 'dongbei.ndvi')
    areaNdviFile = os.path.join(NdviPath, areaNdviFileName)
    gdal.Warp(areaNdviFile, NdviFile, outputBounds=[1033000, 4267000, 2207000, 5922000])
    '''


def CalcNDVIandEVI( files,filepath,NdviPath,EviPath):
    try:
        ll = []
        names = None
        for i in files:
            if( names is None):
                names = i.split('.')
            print(i);
            ds= gdal.Open(i);
            subdatasets = ds.GetSubDatasets();
            ll.append(subdatasets[1][0]);
        filename = '%s.%s.%s.%s.tif' % (names[0], names[1], names[3],'state_1km')
        state_1 = gdal.Warp( filename,ll )
        ll.clear()

        for i in files:
            if( names is None):
                names = i.split('.')
            print(i);
            ds= gdal.Open(i);
            subdatasets = ds.GetSubDatasets();
            ll.append(subdatasets[11][0]);
        filename = '%s.%s.%s.%s.tif' % (names[0], names[1], names[3],'sur_refl_b01_1')
        rsb01 = gdal.Warp( filename,ll )
        ll.clear()

        for i in files:
            ds = gdal.Open(i);
            subdatasets = ds.GetSubDatasets();
            ll.append(subdatasets[12][0]);

        filename = '%s.%s.%s.%s.tif' % (names[0], names[1], names[3], 'sur_refl_b02_1')

        rsb02 = gdal.Warp(filename,ll )
        ll.clear()

        for i in files:
            ds = gdal.Open(i);
            subdatasets = ds.GetSubDatasets();
            ll.append(subdatasets[13][0]);
            #ll.append( 'HDF4_EOS:EOS_GRID:"%s":MODIS_Grid_500m_2D:sur_refl_b03_1' % (os.path.join(filepath,i)) )

        filename = '%s.%s.%s.%s.tif' % (names[0], names[1], names[3], 'sur_refl_b03_1')
        #b03 = os.path.join(filepath, filename);
        #print(b03, " ", filename);
        rsb03 = gdal.Warp(filename,ll )
        ll.clear()
        makeNDVIandEVI(state_1,rsb01,rsb02,rsb03,names,NdviPath,EviPath)

    except Exception as e:
        return True


DESC = "This script will recursively download all files if they don't exist from a LAADS URL and stores them to the specified path"

def _main(argv):
    parser = argparse.ArgumentParser(prog=argv[0], description=DESC)
    parser.add_argument('-s', '--source',default='https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MOD09GA/2013', dest='source', metavar='URL', help='Recursively download files at URL', required=False)
    parser.add_argument('-d', '--destination', dest='destination', metavar='DIR', help='Store directory structure in DIR', required=True)
    parser.add_argument('-ndvi', '--ndvi', dest='ndvi', metavar='DIR',help='Store directory structure in DIR', required=True)
    parser.add_argument('-evi', '--evi', dest='evi', metavar='DIR', help='Store directory structure in DIR',
                        required=True)
    parser.add_argument('-start','--start',dest='start',metavar='MUMBER',help='start day', required=True)
    parser.add_argument('-end', '--end', dest='end', metavar='MUMBER', help='end day', required=True)
    args = parser.parse_args(argv[1:])
    
    gdal.AllRegister()
    if not os.path.exists(args.destination):
        os.makedirs(args.destination)
    for i in range(int(args.start),int(args.end)):
        url = args.source + '/%03d' % i
        path = args.destination + r'\%03d' % i
        ndvipath = args.ndvi #+ r'\%03d' % i
        evipath= args.evi #+r'\%03d' % i
    
        print( url )
        print( path)
        if not 	os.path.exists(path):
            os.makedirs(path)

        #usgs官网注册就会有token
        downedfiles = download.sync(url, path, 'a token get from usgs')

        if not os.path.exists(ndvipath):
            os.makedirs(ndvipath)
        if not os.path.exists(evipath):
            os.makedirs(evipath)
        CalcNDVIandEVI(downedfiles, path, ndvipath, evipath)



# 7CCA54C2-C38A-11E8-B461-AFB1502E27AA
if __name__ == '__main__':
    try:
        sys.exit(_main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(-1)