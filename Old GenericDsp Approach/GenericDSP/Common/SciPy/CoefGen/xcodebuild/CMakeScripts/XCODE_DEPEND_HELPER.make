# DO NOT EDIT
# This makefile makes sure all linkable targets are
# up-to-date with anything they link to
default:
	echo "Do not invoke directly"

# Rules to remove targets that are older than anything to which they
# link.  This forces Xcode to relink the targets from scratch.  It
# does not seem to check these dependencies itself.
PostBuild.coefgen.Debug:
/Users/andy/Dropbox/Developer/AudioDev/GenericDSP/Common/SciPy/CoefGen/xcodebuild/Debug/coefgen.cpython-37m-darwin.so:
	/bin/rm -f /Users/andy/Dropbox/Developer/AudioDev/GenericDSP/Common/SciPy/CoefGen/xcodebuild/Debug/coefgen.cpython-37m-darwin.so


PostBuild.coefgen.Release:
/Users/andy/Dropbox/Developer/AudioDev/GenericDSP/Common/SciPy/CoefGen/xcodebuild/Release/coefgen.cpython-37m-darwin.so:
	/bin/rm -f /Users/andy/Dropbox/Developer/AudioDev/GenericDSP/Common/SciPy/CoefGen/xcodebuild/Release/coefgen.cpython-37m-darwin.so


PostBuild.coefgen.MinSizeRel:
/Users/andy/Dropbox/Developer/AudioDev/GenericDSP/Common/SciPy/CoefGen/xcodebuild/MinSizeRel/coefgen.cpython-37m-darwin.so:
	/bin/rm -f /Users/andy/Dropbox/Developer/AudioDev/GenericDSP/Common/SciPy/CoefGen/xcodebuild/MinSizeRel/coefgen.cpython-37m-darwin.so


PostBuild.coefgen.RelWithDebInfo:
/Users/andy/Dropbox/Developer/AudioDev/GenericDSP/Common/SciPy/CoefGen/xcodebuild/RelWithDebInfo/coefgen.cpython-37m-darwin.so:
	/bin/rm -f /Users/andy/Dropbox/Developer/AudioDev/GenericDSP/Common/SciPy/CoefGen/xcodebuild/RelWithDebInfo/coefgen.cpython-37m-darwin.so




# For each target create a dummy ruleso the target does not have to exist
