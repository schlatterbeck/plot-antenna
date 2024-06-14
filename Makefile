# To use this Makefile, get a copy of my SF Release Tools
# git clone git://git.code.sf.net/p/sfreleasetools/code sfreleasetool
# And point the environment variable RELEASETOOL to the checkout
ifeq (,${RELEASETOOL})
    RELEASETOOL=../releasetool
endif
LASTRELEASE:=$(shell $(RELEASETOOL)/lastrelease -n -rv)
VERSIONPY=plot_antenna/Version.py
VERSIONTXT=VERSION
VERSION=$(VERSIONPY) $(VERSIONTXT)
README=README.rst
PROJECT=plot-antenna

all: $(VERSION)

test:
	$(PYTHON) -m pytest test

clean:
	rm -f README.html $(VERSION) announce_pypi
	rm -rf dist build upload upload_homepage ReleaseNotes.txt $(CLEAN)
	rm -rf plot_antenna.egg-info
	rm -f *.ppm

.PHONY: clean test

include $(RELEASETOOL)/Makefile-pyrelease
