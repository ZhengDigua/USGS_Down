#!/usr/bin/env python

# script supports either python2 or python3
#
# Attempts to do HTTP Gets with urllib2(py2) urllib.requets(py3) or subprocess
# if tlsv1.1+ isn't supported by the python ssl module
#
# Will download csv or json depending on which python module is available
#

###################将HDF拼接成TIF#################################

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

def makeNDVIEVI16(satellitename,rb1,rb2,names,ndvi16path,evi16path):
	if (rb1 is None):
		return
	if (rb2 is None):
		return

	'''
	areas = {'HuangHuaiHai': [482000, 3189000, 1574000, 4662000],
	         'ChangJiangZhongXiaYou': [-704000, 2596000, 1574000, 3841000],
	         'DongBei': [1033000, 4267000, 2207000, 5922000]};
	'''
	areas = {'HuangHuaiHai': [482000, 3189000, 1574000, 4662000],
	         'DongBei': [1033000, 4267000, 2207000, 5922000]};

	########make NDVI file###########
	outputBounds = [-704000, 2596000, 2207000, 5922000];
	NDVI16FileName='%s.%s.%s.%s.tif'%(satellitename,names[1],names[3],"ndvi");
	NDVIFile = os.path.join(ndvi16path, NDVI16FileName);
	gdal.Warp(NDVIFile, rb1, outputBounds=outputBounds, xRes=1000, yRes=1000, srcNodata=-9999, dstNodata=-9999,
	          outputType=gdal.GDT_Float32,
	          dstSRS="+proj=aea +ellps=WGS84 +datum=WGS84 +lon_0=105 +lat_1=25 +lat_2=47 +units=m +");

	for name, bound in areas.items():
		areaLSTFileName = '%s.%s.%s.%s.%s.tif' % (satellitename,names[1], names[3], name, "ndvi")
		areaLSTFile = os.path.join(ndvi16path, areaLSTFileName)
		gdal.Warp(areaLSTFile, NDVIFile, outputBounds=bound)

	##########make evi file#################
	bandevi = gdal_array.BandReadAsArray(rb2.GetRasterBand(1))
	bandevi[numpy.isnan(bandevi)] = -9999
	bandevi[numpy.isinf(bandevi)] = -9999
	bandevi = bandevi / 10000.0
	bandevi[bandevi > 2] = -9999
	bandevi[bandevi < -1] = -9999

	nodata = rb2.GetRasterBand(1).GetNoDataValue()
	bandevi[bandevi == nodata] = -9999
	outevi = gdal_array.SaveArray(bandevi, "fgf", format="MEM", prototype=rb2)

	evi16filename = '%s.%s.%s.%s.tif' % (satellitename,names[1], names[3], "evi")

	eVIFile = os.path.join(evi16path, evi16filename)
	gdal.Warp(eVIFile, outevi, outputBounds=outputBounds, xRes=1000, yRes=1000, srcNodata=-9999, dstNodata=-9999,
	          outputType=gdal.GDT_Float32,
	          dstSRS="+proj=aea +ellps=WGS84 +datum=WGS84 +lon_0=105 +lat_1=25 +lat_2=47 +units=m +")

	for name, bound in areas.items():
		areaLSTFileName = '%s.%s.%s.%s.%s.tif' % (satellitename,names[1], names[3], name, "evi")
		areaLSTFile = os.path.join(evi16path, areaLSTFileName)
		gdal.Warp(areaLSTFile, eVIFile, outputBounds=bound)

def CalNDVI16EVI16(satellitename,files,filepath,NDVI16PATH,EVI16PATH):
    try:
        ll = []
        names = None
        for i in files:
            if( names is None):
                names = i.split('.')
            ds=gdal.Open(os.path.join(filepath,i));
            subdatasets=ds.GetSubDatasets();
            ll.append(subdatasets[0][0]);
            print(i);
        filename = '%s.%s.%s.%s.%s.tif' % (satellitename,names[1], names[3], names[4],'ndvi')
        b01 = os.path.join( filepath,filename)
        rsb01 = gdal.Warp( b01,ll )
        ll.clear()

        for i in files:
            if( names is None):
                names = i.split('.')
            ds = gdal.Open(os.path.join(filepath, i));
            subdatasets = ds.GetSubDatasets();
            ll.append(subdatasets[1][0]);
        filename = '%s.%s.%s.%s.%s.tif' % (satellitename,names[1], names[3], names[4],'evi')
        b02 = os.path.join( filepath,filename)
        rsb02 = gdal.Warp( b02,ll )
        makeNDVIEVI16(satellitename,rsb01,rsb02,names,NDVI16PATH,EVI16PATH )
    except Exception as e:
        return True

def _main(argv):
	parser = argparse.ArgumentParser(prog=argv[0], description=DESC)
	parser.add_argument('-d', '--destination', dest='destination', metavar='DIR',help='Store directory structure in DIR', required=True)

	parser.add_argument('-ndvi16', '--ndvi16', dest='ndvi16', metavar='DIR', help='Store directory structure in DIR',required=True)
	parser.add_argument('-evi16', '--evi16', dest='evi16', metavar='DIR', help='Store directory structure in DIR',required=True)
	parser.add_argument('-start', '--start', dest='start', metavar='MUMBER', help='start day', required=True);
	parser.add_argument('-end', '--send', dest='end', metavar='MUMBER', help='end day', required=True);

	args = parser.parse_args(argv[1:])
	gdal.AllRegister()
	if not os.path.exists(args.destination):
		os.makedirs(args.destination)
	destination = args.destination;
	p_ndvi16 = args.ndvi16;
	p_evi16 = args.evi16;
	dstart = int(args.start);
	dend = int(args.end);
	for i in range(dstart, dend+ 1):
		if(i%16==1):
			url = 'https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MOD13Q1/2005' + '/%03d' % i
			path = destination #+'\MOD13Q1'+r'\%04d'%2019 + r'\%03d' % i;
			ndvi16path = p_ndvi16 #+ r'\%03d' % i;
			evi16path = p_evi16 #+ r'\%03d' % i;
			if not os.path.exists(path):
				os.makedirs(path);
			if not os.path.exists(ndvi16path):
				os.makedirs(ndvi16path);
			if not os.path.exists(evi16path):
				os.makedirs(evi16path);
			downedfiles = [];
			downedfiles = download.sync(url, path, 'a token you can get from usgs')
			if (len(downedfiles) > 1):
				CalNDVI16EVI16('MOD13Q1',downedfiles, path, ndvi16path, evi16path)
		if (i % 16 == 9):
			url = 'https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MYD13A2/2005' + '/%03d' % i;
			path = destination # + '\MYD13A2'+r'\%04d'%2019 + r'\%03d' % i;
			ndvi16path = p_ndvi16 #+ r'\%03d' % i;
			evi16path = p_evi16 #+ r'\%03d' % i
			if not os.path.exists(path):
				os.makedirs(path);
			if not os.path.exists(ndvi16path):
				os.makedirs(ndvi16path);
			if not os.path.exists(evi16path):
				os.makedirs(evi16path);
			downedfiles = [];
			downedfiles = download.sync(url, path, 'a token you can get from usgs');
			if (len(downedfiles) > 1):
				CalNDVI16EVI16('MYD13A2', downedfiles, path, ndvi16path, evi16path)

if __name__ == '__main__':
    try:
        sys.exit(_main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(-1)
    sys.exit(0)





