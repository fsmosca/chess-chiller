# Chess-Chiller
Read pgn files, parse positions in the game and save interesting positions for problem-solving sessions.

### A. Requirements
* Python 3 
* Python-Chess 
* Chess engines that supports multipv and movetime commands 
* PGN file

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
