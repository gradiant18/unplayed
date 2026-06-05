run:
	./venv/bin/python3 ./src/main.py

test:
	./venv/bin/python3 ./src/main.py -n

clean:
	rm -rf ./build ./dist .__pycache__ ./src/__pycache__ ./unplayed
	rm -f *.spec *.bin *.log *_skipped.txt

build: ./src/*
	python -m nuitka --follow-imports --output-filename=unplayed src/main.py
