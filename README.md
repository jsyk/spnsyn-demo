spnsyn-demo
===========

Sythesis of Synchronous Petri nets (SPN) into hardware.

Required tools
----------------

* Python 3
* GHDL
* gtkwave
* espresso [http://code.google.com/p/eqntott/downloads/list]
* eqntott [http://code.google.com/p/eqntott/downloads/list]

The espresso and eqntott tools have to be downloaded, built and installed in the system $PATH. 
Both programs in the source code can be obtained at the same google-
code project page linked above.

The GHDL is the VHDL simulator used in the automated testing. The gtkwave can be used to visualize
the digital waveforms generated in the GHDL simulator.



Runnning the unit tests and examples
--------------------------------------

The t/ directory contains tests and examples. Run `make' in any of the subdirectories to execute the
test. This will generate RTL VHDL and run it through the GHDL simulator with a testbench. To
visualize the output you may run `make show' afterwards; a gtkwave window will open and load the
generated waveform.

