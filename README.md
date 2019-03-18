# Chess-Chiller
Read pgn files, parse positions in the game and save interesting positions for problem-solving sessions.

#### Requirements
* Python 3 
* Python-Chess 
* Chess engines that supports multipv and movetime commands 
* PGN file

#### Command line
python chess-chiller.py --inpgn aeroflotopa19.pgn --engine sf10.exe --threads 1 --hash 128 --mintime 5.0 --maxtime 20.0
