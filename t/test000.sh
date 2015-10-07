#!/bin/bash
touch test000/unreadable_file
chmod 000 test000/unreadable_file
x=`python ../bitfit.py test000 2>&1`
echo $x | grep "Unable to read the file" >/dev/null
if [ $? -ne 0 ] ; then
    echo "Test000: FAILED"
else
    echo "Test000: PASSED"
fi
chmod 644 test000/unreadable_file
