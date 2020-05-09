# DO NOT EDIT
# This makefile makes sure all linkable targets are
# up-to-date with anything they link to
default:
	echo "Do not invoke directly"

# Rules to remove targets that are older than anything to which they
# link.  This forces Xcode to relink the targets from scratch.  It
# does not seem to check these dependencies itself.
PostBuild.block_test.Debug:
/Users/andy/Dropbox/Developer/AudioDev/GenericDsp/Common/SciPy/BlockTest/xcode/Debug/block_test.cpython-37m-darwin.so:
	/bin/rm -f /Users/andy/Dropbox/Developer/AudioDev/GenericDsp/Common/SciPy/BlockTest/xcode/Debug/block_test.cpython-37m-darwin.so


PostBuild.block_test.Release:
/Users/andy/Dropbox/Developer/AudioDev/GenericDsp/Common/SciPy/BlockTest/xcode/Release/block_test.cpython-37m-darwin.so:
	/bin/rm -f /Users/andy/Dropbox/Developer/AudioDev/GenericDsp/Common/SciPy/BlockTest/xcode/Release/block_test.cpython-37m-darwin.so


PostBuild.block_test.MinSizeRel:
/Users/andy/Dropbox/Developer/AudioDev/GenericDsp/Common/SciPy/BlockTest/xcode/MinSizeRel/block_test.cpython-37m-darwin.so:
	/bin/rm -f /Users/andy/Dropbox/Developer/AudioDev/GenericDsp/Common/SciPy/BlockTest/xcode/MinSizeRel/block_test.cpython-37m-darwin.so


PostBuild.block_test.RelWithDebInfo:
/Users/andy/Dropbox/Developer/AudioDev/GenericDsp/Common/SciPy/BlockTest/xcode/RelWithDebInfo/block_test.cpython-37m-darwin.so:
	/bin/rm -f /Users/andy/Dropbox/Developer/AudioDev/GenericDsp/Common/SciPy/BlockTest/xcode/RelWithDebInfo/block_test.cpython-37m-darwin.so




# For each target create a dummy ruleso the target does not have to exist
