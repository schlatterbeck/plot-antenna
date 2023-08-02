# To use this Makefile, get a copy of my SF Release Tools
# git clone git://git.code.sf.net/p/sfreleasetools/code sfreleasetools
# And point the environment variable RELEASETOOLS to the checkout
ifeq (,${RELEASETOOLS})
    RELEASETOOLS=../releasetools
endif
LASTRELEASE:=$(shell $(RELEASETOOLS)/lastrelease -n -rv)
VERSIONPY=plot_antenna/Version.py
VERSION=$(VERSIONPY)
README=README.rst
PROJECT=plot-antenna

all: $(VERSION)

test:
	$(PYTHON) -m pytest test

clean:
	rm -f README.html plot_antenna/Version.py announce_pypi
	rm -rf dist build upload upload_homepage ReleaseNotes.txt $(CLEAN)
	rm -rf plot_antenna.egg-info
	rm *.ppm

.PHONY: clean test

include $(RELEASETOOLS)/Makefile-pyrelease
