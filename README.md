# Chess-Chiller
Read pgn files, parse positions in the game and save interesting positions for problem-solving sessions.

### Requirements
* Python 3 
* Python-Chess 
* Chess engines that supports multipv and movetime commands 
* PGN file

### Command line
python chess-chiller.py --inpgn aeroflotopa19.pgn --engine sf10.exe --threads 1 --hash 128 --mintime 5.0 --maxtime 20.0

Interesting positions will be saved in interesting.epd

### Options and flags
#### --pin
A flag used to saved only those positions when there is a piece of the side not to move that is pinned.\
`python chess-chiller.py --inpgn aeroflotopa19.pgn --engine sf10.exe --pin`

#### --skipdraw
A flag used to ignore games with draw results. Useful when you are only interested on generating positions from games with 1-0 or 0-1 results.\
`python chess-chiller.py --inpgn aeroflotopa19.pgn --engine sf10.exe --skipdraw`

#### --minpiecevalue [value]
An option used to control the number of pieces (not kings and not pawns) remaining on the board for saved positions. Default value is 62 from 2*Q + 4*R + 4*B + 4*N, where Q=9, R=5, B=3 and N=3. If you want middle phase positions, you may use for example 2Q + 4R + 2B + 2N or 50. Any positions with less than 50 piece value will not be saved.\
`python chess-chiller.py --inpgn aeroflotopa19.pgn --engine sf10.exe --minpiecevalue 50`

#### --log [value]
An option used to save logs to all.log file. value can be **debug, info, warning, error and critical**, default is critical. If you want to see all the logs including the engine analysis, use value debug. Error messages will be saved in error.log file.\
`python chess-chiller.py --inpgn aeroflotopa19.pgn --engine sf10.exe --log debug`
