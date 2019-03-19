# Chess-Chiller
Read pgn files, parse positions in the game and save interesting positions for problem-solving sessions.

### A. Requirements
* Python 3 
* Python-Chess 
* Chess engines that supports multipv and movetime commands 
* PGN file

Python 3 can be found at https://www.python.org/downloads/ \
Python-chess can be found at https://github.com/niklasf/python-chess \
Chess engine that supports multipv and movetime is Stockfish. Download it from https://stockfishchess.org/download/ \
PGN file which contain game records can be downloaded from http://theweekinchess.com/

### B. Command line
python chess-chiller.py --inpgn aeroflotopa19.pgn --engine sf10.exe --threads 1 --hash 128 --mintime 5.0 --maxtime 20.0

Interesting positions will be saved in interesting.epd

### C. Options and flags
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

### D. Output
An example output epd would look like this.

`4rbrk/5Rpp/p3b3/1p1B4/4p3/1P2P3/PB6/2K3R1 w - - bm Rxf8; ce 323; sm Rxf8; acd 28; acs 20; fmvn 28; hmvc 0; pv Rxf8 Rexf8 Bxe6 h6 Bxg8; c0 "Cheparinov, Ivan - Zeng, Chongsheng, TCh-CHN 2018, China CHN, 2018.04.11, R1.2"; c1 "Complexity: 2"; c2 "bestscore2: -28"; c3 "Analyzing engine: Stockfish 10 64 POPCNT";`

The board image from that epd.

![](https://i.imgur.com/0x41SJp.png "From chess-chiller epd output, white to move!")

### E. Process flow
1. The script will read the pgn file given from --inpgn [user pgn file].
2. Will read each game in the pgn file.
3. Will parse the moves in the game in reverse. If the game has 40 moves, it will visit first the end position at 40th move, 39th move and so on.
4. In every position visited the chess engine specified in --engine [engine] will be run at multipv 2 at a given maxtime from --maxtime [time in sec]. We are interested on saving the 1st best score from multipv 1 call it (bs1) and the 2nd best score from multipv 2 call it (bs2).
5. Basically when the engine shows that the side to move has a decisive advantage say bs1 >= 300 cp (centipawn) and bs2 is not winning say bs2 <= 50 cp then the program will save that position in interesting.epd file. Take a look at the example epd output in section D. The ce (centipawn evaluation) has a value of 323. That is actually bs1. And that of bs2 is at c2 "bestscore2: -28"; in this case bs2 is -28 cp.
6. The program has score thresholds which will control if the position is saved or not. The value 300 cp can be controlled by the user via the parameter [minbest1score1](https://github.com/fsmosca/chess-chiller/blob/0c2349964372bb641ee1e0c327583ced16510e24/chess-chiller.py#L417) currently hard-coded but later will be exposed as an option. And that 50 cp is also a parameter called maxbest2score1. If you want the program to generate mate positions, just set minbest1score1 to 30000 and maxbest2score1 to 500. The code would look like this.\
`if bs1 >= minbest1score1 and bs2 <= maxbest2score1, then save this position.`
7. There are some enhancements to save the position or not, one of those is, if the side to move is in-check, don't save such position. Another one is if the best move is a capture and this position is not complicated according to the analyzing engine, such position is also not saved.

