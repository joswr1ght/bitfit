#!/usr/bin/env python3
# MIT License, (c) Joshua Wright jwright@willhackforsushi.com
# https://github.com/joswr1ght/bitfit
# encoding=utf8
import sys
import importlib

import os, hashlib, getpass, csv, glob, re, textwrap, time
from datetime import datetime
import pdb

VER="1.2.0"
SMALLBLOCK=65536

def hasher(filename, blocksize=-1):
    # Hash the file, returning MD5 and SHA1 in an optimal manner. Most of this code is error handling.
    hashmd5 = hashlib.md5()
    hashsha1 = hashlib.sha1()
    try:
        with open(filename, "rb") as f:
            while True:
                block = f.read(blocksize)
                if not block:
                    break
                hashmd5.update(block)
                hashsha1.update(block)

    except IOError:
        err = "Error: Unable to read the file \"%s\". Make sure you have permission to read this file.  You may have " \
                "to disable or uninstall anti-virus to stop it from denying access to the file.  Correct this " \
                "problem and try again."%filename
        sys.stderr.write(textwrap.fill(err, width=term_width()) + "\n")
        sys.exit(-1)

    except MemoryError:
        # OOM, revert to the smaller blocksize for this file
        #print "DEBUG: Reducing block size for the file %s"%filename
        if blocksize != -1:
            # Blocksize is already small - bail
            err = "Error: Unable to read the file \"%s\" into memory. This could be caused by anti-virus, or by " \
                    "other system instability issues. Kill some running processes before trying again."%filename
            sys.stderr.write(textwrap.fill(err, width=term_width()) + "\n")
            sys.exit(-1)

        # We can't recover if this fails, so no try/except block.
        with open(filename, "rb") as f:
            for block in iter(lambda: f.read(SMALLBLOCK), ""):
                hashmd5.update(block)
                hashsha1.update(block)

    return (hashmd5.hexdigest(), hashsha1.hexdigest())

def usage():
    print("Bitfit %s"%VER)
    print("Usage: %s [OPTIONS] [STARTING DIRECTORY]"%os.path.basename(sys.argv[0]))
    print("     - With no arguments, recursively calculate hashes for all files")
    print("-v   - Search for a VERSION verification file and validate hashes")
    print("-l   - Reduce memory consumption for hashing on low memory systems")
    print("-t   - Print timing and media speed information on STDERR")
    print("")
    msg="In verification mode, + indicates a file not present in the VERSION file, - " \
          "indicates a missing file in the directory tree, and ! indicates content mismatch."
    print(textwrap.fill(msg, width=term_width()) + "\n")

def term_width():
    """ Return the width of the terminal, or 80 """
    try:
        if os.name == 'nt': # Windows
            return int(re.findall('\s+ Columns:\s+(\d+)',os.popen("mode con:", "r").read())[0])-1
        else:
            return int(os.popen('stty size', 'r').read().split()[1])
    except:
        return 80

def validate_hashes(verfile, startdir, hashes):
    verhashes = []
    observedfiles = []
    verified=True
    # Open file, handling ASCII or Unicode (PowerShell output)
    try:
        fp = open(verfile)
    except IOError:
        sys.stderr.write("Cannot open version file %s. Exiting.\n"%verfile)
        sys.exit(-1)

    verfilestr=fp.read()
    try:
        verdatalist = verfilestr.split("\n")
    except UnicodeDecodeError:
        # Handle PowerShell-generated unicode files
        fp.seek(2)
        verfilestr=fp.read()
        verdatalist = verfilestr.split("\r\n\r\n")

    # Build a new hashlist
    reader = csv.reader(verdatalist[:-1]) # Skip the last list entry, which is the EOF marker
    for line in reader:
        if line == []:
            break
        if line[0].startswith("#") or line[0].startswith("VERSION-"):
            continue
        verhashes.append((line[0], line[1], line[2]))
    verhashes.sort()

    missingdiff = list(set(verhashes) - set(hashes))
    if missingdiff:
        verified=False
        for diff in missingdiff:
            # Check if the file exists - if it does, it's a change to the file
            if os.path.isfile(os.path.join(startdir,diff[0])):
                # only report this entry as a change once
                observedfiles.append(diff[0])
                print("!  %s"%diff[0])
            else:
                print("-  %s"%diff[0])

    addeddiff = list(set(hashes) - set(verhashes))
    if addeddiff:
        verified=False
        for diff in addeddiff:
            if diff[0] not in observedfiles:
                print("+  %s"%diff[0])

    return verified

# Produce a Windows-style filename
def winfname(filename):
    return filename.replace("/","\\")

# Produce a Linux-style filename
def linfname(filename):
    return filename.replace("\\","/")

# Normalize filename based on platform
def normfname(filename):
    if os.name == 'nt': # Windows
        return filename.replace("/", "\\")
    else:
        return filename.replace("\\","/")

if __name__ == '__main__':
    
    opt_verify = None
    opt_lowmem = None
    opt_timing = None
    opt_startdir = None

    if len(sys.argv) == 1:
        usage()
        sys.exit(0)

    args = sys.argv[1:]
    it = iter(args)
    for i in it:
        if i == '-l':
            opt_lowmem = True
            continue
        elif i == '-v':
            opt_verify = True
            continue
        elif i == "-t":
            opt_timing = True
            continue
        elif i == "-h" or i == "--help":
            usage()
            sys.exit(0)

    # The last argument must be a directory
    opt_startdir = sys.argv[-1]
    if not os.path.isdir(opt_startdir):
        sys.stdout.write("Error: Last argument must be the starting directory for content.\n")
        sys.exit(-1)

    if opt_lowmem:
        hashblocklen=SMALLBLOCK
    else:
        # Optimize for memory rich systems
        hashblocklen=-1

    # If we are verifying, before we calculate the hashes make sure we can find the verification file
    if opt_verify:
        verfile = glob.glob(opt_startdir + '/' + 'VERSION-*.txt')
        if len(verfile) == 0:
            err="Error: I can't find a VERSION-*.txt file in %s. Make sure the file exists, has a filename " \
                    "extension of \".txt\" and is readable, then try again.\n"%opt_startdir
            sys.stderr.write(textwrap.fill(err, width=term_width()) + "\n")
            sys.exit(-1)
        if len(verfile) != 1:
            err="Error: Too many matching filenames for verification. Please rename or move the files in the " \
                    "starting directory %s.\n"%opt_startdir
            sys.stderr.write(textwrap.fill(err, width=term_width()) + "\n")
            sys.exit(-1)
        verfile=verfile[0]

    # Build a list of (filename, md5hash, sha1hash) for each file, regardless of specified options
    filelist = []

    if opt_timing:
        # Establish variable to store sum of sizes for all files hashed, used for crude media speed calculation
        file_size = 0
        # Establish wall clock time at start of the main loop
        start_time = time.time()

    # Walk all subdirectories returning (filename, md5hash, sha1hash) for each file
    for (directory, _, files) in os.walk(opt_startdir):
        for f in files:
            if f.startswith("VERSION-"): continue
            pathfile = os.path.join(directory, f)
            hashes = hasher(pathfile, hashblocklen)
            filelist.append((linfname(os.path.relpath(pathfile,opt_startdir)),hashes[0], hashes[1]))
            if opt_timing:
                file_size = file_size + os.path.getsize(pathfile) / 1024
    filelist.sort()

    if opt_timing:
        # Establish wall clock time at end of main loop
        end_time = time.time()
        elapsed_time = end_time - start_time

        # convert file_size to MB
        file_size = file_size / 1024

    # With the filelist built, compare to the negative match list, or print
    # the results.
    if opt_verify:
        try:
            if validate_hashes(verfile, opt_startdir, filelist):
                print("Validation complete, no errors.")
            else:
                print("Validation failed.")
        except:
            print(sys.exc_info())
            sys.stderr.write(textwrap.fill("Error parsing contents of the VERSION file \"" + verfile + "\". Ensure the file was generated with bitfit and not another tool. If the problem persists, open a ticket at https://github.com/joswr1ght/bitfit/issues and attach the VERSION file.", width=term_width()) + "\n")
    else:
        # Just print out the list with Linux-syle filenames
        print("# bitfit %s output generated on %s by %s\r"%(VER,str(datetime.now()),getpass.getuser()))
        print("# " + " ".join(sys.argv) + "\r")
        print("# filename,MD5,SHA1\r")
        writer = csv.writer(sys.stdout)
        writer.writerows(filelist)

    if opt_timing:
        # Display basic speed stats to STDERR
        timespeed = "Took %.2f seconds to hash %d MB (%.2f MB/sec)" % (elapsed_time, file_size, (file_size/elapsed_time))
        sys.stderr.write(textwrap.fill(timespeed, width=term_width()) + "\n")
