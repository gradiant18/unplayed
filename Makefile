run:
	./venv/bin/python3 ./src/main.py

test:
	./venv/bin/python3 ./src/main.py -sn

clean:
	rm -rf ./build ./dist .__pycache__ ./src/__pycache__ ./unplayed
	rm -f *.spec *.bin *.log

build:
	pyinstaller ./src/main.py -F --noconsole --name "unplayed"
