mainwindow.py: mainwindow.ui
	pyuic4 -o mainwindow.py mainwindow.ui

clean: FORCE
	rm mainwindow.py

FORCE:
