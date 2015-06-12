#!/usr/bin/env python
# MIT License, (c) Joshua Wright jwright@willhackforsushi.com
# https://github.com/joswr1ght/bitfit
import os, sys, hashlib, getpass, csv, glob
from datetime import datetime

VER="1.0.0"

def hasher(filename, blocksize=-1):
    hashmd5 = hashlib.md5()
    hashsha1 = hashlib.sha1()
    with open(filename, "rb") as f:
        for block in iter(lambda: f.read(blocksize), ""):
            hashmd5.update(block)
            hashsha1.update(block)
    return (hashmd5.hexdigest(), hashsha1.hexdigest())

def usage():
    print "Bitfit %s"%VER
    print "Usage: %s [OPTIONS] [STARTING DIRECTORY]"%os.path.basename(sys.argv[0])
    print "     - With no arguments, recursively calculate hashes for all files"
    print "-v   - Search for a VERSION verification file and validate hashes"
    print "-l   - Reduce memory consumption for hashing on low memory systems"
    print ""
    print "In verification mode, + indicates a file not present in the VERSION file, -"
    print "indicates a missing file in the directory tree, and ! indicates content"
    print "mismatch."

def validate_hashes(verfile, startdir, hashes):
    verhashes = []
    observedfiles = []
    verified=True
    # Open file and build a new hashlist
    reader = csv.reader(open(verfile, 'rb'))
    for line in reader:
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
                print "!  %s"%diff[0]
            else:
                print "-  %s"%diff[0]

    addeddiff = list(set(hashes) - set(verhashes))
    if addeddiff:
        verified=False
        for diff in addeddiff:
            if diff[0] not in observedfiles:
                print "+  %s"%diff[0]

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

    # The last argument must be a directory
    opt_startdir = sys.argv[-1]
    if not os.path.isdir(opt_startdir):
        sys.stdout.write("Error: Last argument must be the starting directory for content.\n")
        sys.exit(-1)

    if opt_lowmem:
        hashblocklen=65536
    else:
        # Optimize for memory rich systems
        hashblocklen=-1

    # If we are verifying, before we calculate the hashes make sure we can find the verification file
    if opt_verify:
        verfile = glob.glob(opt_startdir + '/' + 'VERSION-*.txt')
        if len(verfile) != 1:
            sys.stdout.write("Error: Too many matching filenames for verification. Please rename or move the\n")
            sys.stdout.write("files in the starting directory %s.\n"%opt_startdir)
            sys.exit(-1)
        verfile=verfile[0]

    # Build a list of (filename, md5hash, sha1hash) for each file, regardless of specified options
    filelist = []
    # Walk all subdirectories returning (filename, md5hash, sha1hash) for each file
    for (directory, _, files) in os.walk(opt_startdir):
        for f in files:
            if f.startswith("VERSION-"): continue
            pathfile = os.path.join(directory, f)
            hashes = hasher(pathfile, hashblocklen)
            filelist.append((linfname(os.path.relpath(pathfile,opt_startdir)),hashes[0], hashes[1]))
    filelist.sort()

    # With the filelist built, compare to the negative match list, or print
    # the results.
    if opt_verify:
        if validate_hashes(verfile, opt_startdir, filelist):
            print "Validation complete, no errors."
        else:
            print "Validation failed."
    else:
        # Just print out the list with Linux-syle filenames
        print "# bitfit %s output generated on %s by %s\r"%(VER,str(datetime.now()),getpass.getuser())
        print "# " + " ".join(sys.argv) + "\r"
        print "# filename,MD5,SHA1\r"
        writer = csv.writer(sys.stdout)
        writer.writerows(filelist)
