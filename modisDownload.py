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
import subprocess
from osgeo import gdal, gdalconst,gdal_array


try:
    from StringIO import StringIO   # python2
except ImportError:
    from io import StringIO         # python3


################################################################################


#USERAGENT = 'tis/download.py_1.0--' + sys.version.replace('\n','').replace('\r','')
USERAGENT ='Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'

def geturl(url, token=None, out=None):

    headers = { 'User-Agent' : USERAGENT }
    if not token is None:
        headers['Authorization'] = 'Bearer ' + token
    try:
        import ssl
        CTX = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        if sys.version_info.major == 2:
            import urllib2
            try:
                fh = urllib2.urlopen(urllib2.Request(url, headers=headers), context=CTX)
        #        fh = urllib2.urlopen(urllib2.Request(url, headers=headers))
                if out is None:
                    return fh.read()
                else:
                    shutil.copyfileobj(fh, out)
            except urllib2.HTTPError as e:
                print('HTTP GET error code: %d' % e.code(), file=sys.stderr)
                print('HTTP GET error message: %s' % e.message, file=sys.stderr)
            except urllib2.URLError as e:
                print('Failed to make request: %s' % e.reason, file=sys.stderr)
            return None

        else:
           # from urllib import request
            from urllib.request import urlopen, Request, URLError, HTTPError
            try:
               #  request.urlretrieve(url,out)
                fh = urlopen(Request(url, headers=headers), context=CTX)
                if out is None:
                    return fh.read().decode('utf-8')
                else:
                    shutil.copyfileobj(fh, out)
            except HTTPError as e:
                print('HTTP GET error code: %s' % str(e.code()), file=sys.stderr)
                print('HTTP GET error message: %s' % e.message, file=sys.stderr)
            except URLError as e:
                print('Failed to make request: %s' % e.reason, file=sys.stderr)
            return None

    except AttributeError:
        # OS X Python 2 and 3 don't support tlsv1.1+ therefore... curl
        import subprocess
        try:
            args = ['curl', '--fail', '-sS', '-L', '--get', url]
            for (k,v) in headers.items():
                args.extend(['-H', ': '.join([k, v])])
            if out is None:
                # python3's subprocess.check_output returns stdout as a byte string
                result = subprocess.check_output(args)
                return result.decode('utf-8') if isinstance(result, bytes) else result
            else:
                subprocess.call(args, stdout=out)
        except subprocess.CalledProcessError as e:
            print('curl GET error message: %' + (e.message if hasattr(e, 'message') else e.output), file=sys.stderr)
        return None



################################################################################


DESC = "This script will recursively download all files if they don't exist from a LAADS URL and stores them to the specified path"


def sync(src, dest, tok):
    '''synchronize src url with dest directory'''
    #hvs = ['.h25v03.','.h25v04.','.h26v03.','.h26v04.','.h26v05.','.h26v06.','.h27v04.','.h27v05.','.h27v06.','.h28v05.','.h28v06.']
    hvs = [ '.h26v04.', '.h26v05.', '.h27v04.', '.h27v05.','.h28v05.','.h28v06.']
    try:
        import csv
        files = [ f for f in csv.DictReader(StringIO(geturl('%s.csv' % src, tok)), skipinitialspace=True) ]
    except ImportError:
        import json
        files = json.loads(geturl(src + '.json', tok))
    downedfiles = []
    # use os.path since python 2/3 both support it while pathlib is 3.4+
    for f in files:
        # currently we use filesize of 0 to indicate directory
        filesize = int(f['size'])
        path = os.path.join(dest, f['name'])
        inHV = False
        for hv in hvs:
         #   hv = hv.encode('utf-8')
            if hv  in f['name']:
                inHV = True
                break
        if not inHV:
            continue

        url = src + '/' + f['name']
        if filesize == 0:
            try:
                print('creating dir:', path)
                os.mkdir(path)
                sync(src + '/' + f['name'], path, tok)
            except IOError as e:
                print("mkdir `%s': %s" % (e.filename, e.strerror), file=sys.stderr)
                sys.exit(-1)
        else:
            try:
                if not IsDownloaded(path):
                 #   downedfiles.append('wget %s -P %s\n' % (url, dest))
                    print(dest)
                    cmd = 'wget -e robots=off -m -np -R .html,.tmp -nH --cut-dirs=3 "%s" --header "Authorization: Bearer %s" -P %s' %(url,tok,dest);
                    #cmd = 'wget --no-check-certificate %s -P %s' % (url, dest)
                    print(cmd)
                    status = subprocess.call(cmd)
                    if status != 0:
                      #  log.write('\nFailed:' + each_item)
                        continue
                    else:
                 #       log.write('\nSuccess:' + each_item)
                #    wget.download(url, out=path)
                        downedfiles.append(path)
                #    print('downloading: ' , path)
                #    with open(path, 'w+b') as fh:
                 #       geturl(url, tok, fh)
                else:
                    downedfiles.append(path)
                    print('skipping: ', path)
            except IOError as e:
                print("open `%s': %s" % (e.filename, e.strerror), file=sys.stderr)
              #  sys.exit(-1)
                return 1
        #    downedfiles.append( path )


    return downedfiles

def IsDownloaded(path):
    if not os.path.exists(path):
        return False
    else:
        # is can be open
        try:
            ds = gdal.Open(path, 0)
            if ds is None:
                os.remove(path)
                return False
            else:
                ds = None
                return True
        except Exception:
            return True



def _main(argv):
    parser = argparse.ArgumentParser(prog=argv[0], description=DESC)
    #-s https://ladsweb.modaps.eosdis.nasa.gov/archive/allData/6/MOD09GA/2018/122 -d h:\liangfeng -t 7CCA54C2-C38A-11E8-B461-AFB1502E27AA
    parser.add_argument('-s', '--source', dest='source', metavar='URL', help='Recursively download files at URL', required=True)
    parser.add_argument('-d', '--destination', dest='destination', metavar='DIR', help='Store directory structure in DIR', required=True)
    parser.add_argument('-start', '--start', dest='start', metavar='MUMBER', help='start day', required=True)
    parser.add_argument('-end', '--end', dest='end', metavar='MUMBER', help='end day', required=True)


    args = parser.parse_args(argv[1:])
    gdal.AllRegister()
    if not os.path.exists(args.destination):
        os.makedirs(args.destination)
    for i in range(int(args.start),int(args.end)+1):
        url = args.source + '/%03d' % i
        path = args.destination + r'\%03d' % i
        print( url )
        print( path)
        if not 	os.path.exists(path):
            os.makedirs(path)

        downedfiles = sync(url, path, '7CCA54C2-C38A-11E8-B461-AFB1502E27AA')



# 7CCA54C2-C38A-11E8-B461-AFB1502E27AA
if __name__ == '__main__':
    try:
        sys.exit(_main(sys.argv))
    except KeyboardInterrupt:
        sys.exit(-1)