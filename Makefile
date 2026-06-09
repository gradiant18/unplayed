BINARY_NAME = unplayed
MAIN_FILE = src/main.py

ifeq ($(OS),Windows_NT)
    VENV_PYTHON = venv\Scripts\python.exe
    RM = del /S /Q
    RMDIR = rmdir /S /Q
    MOVE = move /Y
    MKDIR = mkdir
    EXE_EXT = .exe
    PLATFORM_FLAGS = --windows-disable-console --enable-plugin=pyqt6 --windows-icon-from-ico=assets/icon.ico
else
    VENV_PYTHON = ./venv/bin/python3
    RM = rm -f
    RMDIR = rm -rf
    MOVE = mv -f
    MKDIR = mkdir -p
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
	$(RMDIR) dist __pycache__ src/__pycache__ $(BINARY_NAME).dist $(BINARY_NAME).build src/$(BINARY_NAME).egg-info

build:
	$(VENV_PYTHON) -m nuitka $(NUITKA_FLAGS) \
		--output-filename=$(BINARY_NAME) \
		$(MAIN_FILE)
	-$(MKDIR) dist
	$(MOVE) $(BINARY_NAME)$(EXE_EXT) dist/$(BINARY_NAME)$(EXE_EXT)
