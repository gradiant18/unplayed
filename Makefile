BINARY_NAME = unplayed
MAIN_FILE = src/main.py

ifeq ($(OS),Windows_NT)
    VENV_PYTHON = venv\Scripts\python.exe
    RM = del /S /Q
    RMDIR = rmdir /S /Q
    EXE_EXT = .exe
    PLATFORM_FLAGS = --windows-disable-console --enable-plugin=pyqt6
else
    VENV_PYTHON = ./venv/bin/python3
    RM = rm -f
    RMDIR = rm -rf
    EXE_EXT = 
    PLATFORM_FLAGS = --enable-plugin=pyqt6
endif

NUITKA_FLAGS = --standalone \
               --onefile \
               --remove-output \
               $(PLATFORM_FLAGS)


.PHONY: run test clean build

run:
	$(VENV_PYTHON) $(MAIN_FILE)

test:
	$(VENV_PYTHON) $(MAIN_FILE) -n

clean:
	$(RMDIR) build dist __pycache__ src/__pycache__ unplayed.dist unplayed.build 2>nul || true
	$(RM) *.spec *.bin *.log *_skipped.txt $(BINARY_NAME)$(EXE_EXT) 2>nul || true

build:
	$(VENV_PYTHON) -m nuitka $(NUITKA_FLAGS) \
		--output-filename=$(BINARY_NAME) \
		$(MAIN_FILE)
