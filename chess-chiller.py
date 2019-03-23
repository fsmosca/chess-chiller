# -*- coding: utf-8 -*-
"""
chess-chiller.py

Requirements:
    * python 3
    * python-chess v0.26.0 or up, https://github.com/niklasf/python-chess
    * Analysis engine that supports multipv and movetime commands
    * PGN file with games
    
"""


import argparse
import logging
from logging.handlers import RotatingFileHandler
import time
import chess.pgn
import chess.engine


VERSION = 'v0.1'


def initialize_logger(logger_level):
    logger = logging.getLogger()
    logger.setLevel(logger_level)
     
    # Creates console handler for info/warning/error/critical logs
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
 
    # Creates error/critical file handler
    handler = RotatingFileHandler("error.log", mode='w',
                                  maxBytes=5000000, backupCount=5)  
    handler.setLevel(logging.ERROR)
    formatter = logging.Formatter("%(asctime)s [%(threadName)-10.10s] [%(funcName)-12.12s] [%(levelname)-5.5s] > %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
 
    # Creates debug/info/warning/error/critical file handler
    handler = RotatingFileHandler("all.log", mode='w',
                                  maxBytes=5000000, backupCount=5)   
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s [%(threadName)-10.10s] [%(funcName)-12.12s] [%(levelname)-5.5s] > %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    
def save_as_pgn(outpgnfn, game, fen, bm):
    """ Save the epd in pgn format """
    mygame = chess.pgn.Game()
    mynode = mygame

    with open(outpgnfn, 'a') as f:
        for k, v in game.headers.items():
            if k == 'Result':
                mygame.headers[k] = '*'
            else:
                mygame.headers[k] = v
        mygame.headers['FEN'] = fen
            
        mynode = mynode.add_main_variation(bm)
        
        f.write('{}\n\n'.format(mygame))


def piece_value(board):
    """ Returns piece value of the board except pawns and kings """
    epd = board.epd().split()[0]
    bn = epd.count('n') * 3
    bb = epd.count('b') * 3
    br = epd.count('r') * 5
    bq = epd.count('q') * 9
    wn = epd.count('N') * 3
    wb = epd.count('B') * 3
    wr = epd.count('R') * 5
    wq = epd.count('Q') * 9
    
    pcvalue = bn + bb + br + bq + wn + wb + wr + wq
    
    logging.info('piece value: {}'.format(pcvalue))
            
    return pcvalue  


def interesting_pos(board, bs1, bs2, minbs1th1, minbs1th2, minbs1th3,
                   maxbs2th1, maxbs2th2, maxbs2th3):
    """ 
    board: board position
    bs1: bestscore1 from multipv 1
    bs2: bestscore2 from multipv 2
    
    minbs1th1: minimum best score 1 threshold 1
    minbs1th2: minimum best score 1 threshold 2
    minbs1th3: minimum best score 1 threshold 3
    
    minbs1th1 > minbs1th2 > minbs1th3
    
    maxbs2th1: maximum best score 2 threshold 1
    maxbs2th2: maximum best score 2 threshold 2
    maxbs2th3: maximum best score 2 threshold 3
    
    maxbs2th1 > maxbs2th2 > maxbs2th3
    
    """
    logging.info('bestscore1: {}, bestscore2: {}'.format(bs1, bs2))
    if bs1 >= minbs1th1:
        # mate score
        if bs1 >= 30000 and bs2 <= min(2000, 2*maxbs2th1):
            return True
        if bs2 <= maxbs2th1:
            return True
    elif bs1 >= minbs1th2:
        if bs2 <= maxbs2th2:
            return True
    elif bs1 >= minbs1th3:
        if bs2 <= maxbs2th3:
            return True
    
    logging.info('Not an interesting pos: {}'.format(board.fen()))
    
    return False


def positional_pos(board, bs1, bs2, minbs1th1, minbs1th2, minbs1th3,
                   maxbs2th1, maxbs2th2, maxbs2th3):
    """ 
    * The engine bestscore1 is not winning and bestscore2 is not lossing
    * The score gap between bestscore1 and bestcore2 is  generally smaller    
    """
    if bs1 >= minbs1th1 and bs1 <= minbs1th1 + 50:
        if bs2 <= maxbs2th1 and bs2 >= maxbs2th1 - 25:
            return True
    if bs1 >= minbs1th2 and bs1 <= minbs1th1:
        if bs2 <= maxbs2th2 and bs2 >= maxbs2th2 - 25:
            return True
    if bs1 >= minbs1th3 and bs1 <= minbs1th2:
        if bs2 <= maxbs2th3 and bs2 >= maxbs2th3 - 25:
            return True
    
    logging.info('Not positional: {}'.format(board.fen()))
    
    return False


def abs_pinned(board, color):
    """ Returns true if one or more pieces of color color is pinned """
    for sq in chess.SQUARES:
        if board.is_pinned(color, sq) \
            and board.piece_at(sq) != chess.Piece(chess.PAWN, color):
            logging.info('piece at square {} ({}) is pinned'.format(sq, board.piece_at(sq)))
            logging.debug('\n{}'.format(board))
            squares = chess.SquareSet([sq])
            logging.debug('\n{}'.format(squares))
            return True
    
    return False 


def analyze_game(game, engine, enginefn, hash_val, thread_val,
                 analysis_start_move_num, outepdfn, gcnt, engname,
                 dullfn, outpgnfn,
                 mintime=5.0, maxtime=15.0, minscorediffcheck=25,
                 minbs1th1=2000, minbs1th2=1000, minbs1th3=500,
                 maxbs2th1=300, maxbs2th2=200, maxbs2th3=100,
                 weightsfile=None, skipdraw=False, pin=False,
                 positional=False, minpiecevalue=0, maxpiecevalue=62):
    """ """

    limit = chess.engine.Limit(time=maxtime)
    
    # Copy orig game header to our epd output
    ev = game.headers['Event']
    si = game.headers['Site']
    da = game.headers['Date']
    ro = game.headers['Round']
    wp = game.headers['White']
    bp = game.headers['Black']
    res = game.headers['Result']
    
    # If result of this game is a draw and skipdraw is true, we skip it
    if skipdraw and res == '1/2-1/2':
        return
    
    c0_val = wp + ' - ' + bp + ', ' + ev + ', ' + si + ', ' + da + ', R' + ro 
    
    poscnt = 0   
    
    # Parse move in reverse
    game_end = game.end()
    curboard = game_end.board()
    
    while curboard:
        board = curboard        
        fmvn = board.fullmove_number
        
        if fmvn < analysis_start_move_num:
            logging.warning('move start limit is reached, exit from this game')
            break
        
        g_move = board.pop()
        curboard = board
        fen = curboard.fen()
        
        # Print the fen before g_move is made on the board
        poscnt += 1  
        
        print('game {} / position {} \r'.format(gcnt, poscnt), end='')
        
        logging.info('game {} / position {}'.format(gcnt, poscnt))
        logging.info('{}'.format(board.fen()))
        logging.info('game move: {}'.format(curboard.san(g_move)))
        
        # piece value conditions
        pcval = piece_value(curboard)
        if pcval < minpiecevalue:
            logging.warning('Skip this pos piece value {} is below minimmum of {}'.format(pcval, minpiecevalue))
            continue
        
        if pcval > maxpiecevalue:
            logging.warning('Skip this pos and game piece value {} is above maximum of {}'.format(pcval, maxpiecevalue))
            break
        
        # Skip this position if --pin is set and no one of the not stm piece is pinned
        if pin and not abs_pinned(board, board.turn ^ 1):
            logging.warning('Skip this pos no piece of not stm is pinned')
            continue
        
        # If side to move is in check, skip this position
        if board.is_check():
            logging.warning('Skip this pos, stm is in check')
            continue
        
        # Run engine in multipv 2
        logging.info('{} is searching at multipv {} for {}s ...'.format(
                engname, 2, maxtime))
        
        bm1, bm2, depth = None, None, None
        raw_pv = None
        bestmovechanges = 0  # Start comparing bestmove1 at depth 4
        tmpmove, oldtmpmove = None, None
        
        # Run engine at multipv 2        
        with engine.analysis(board, limit, multipv=2) as analysis:
            for info in analysis:
                time.sleep(0.01)
                try:
                    multipv = info['multipv']
                    depth = info['depth']
                    if info['score'].is_mate():
                        s = info['score'].relative.score(mate_score=32000)
                    else:
                        s = info['score'].relative.score()
                    pv = info['pv'][0:5]
                    t = info['time']
                
                    if multipv == 1:
                        bm1 = pv[0]
                        bs1 = s
                        raw_pv = pv
                        
                        # Exit early if score is below half of minbest1score3
                        if t >= mintime and bs1 < minbs1th3/2:
                            logging.warning('Exit search early, current best score is only {}'.format(bs1))
                            break
                        
                        # Record bestmove move changes to determine position complexity
                        if 'depth' in info and 'pv' in info \
                                and 'score' in info \
                                and not 'lowerbound' in info \
                                and not 'upperbound' in info \
                                and depth >= 4:
                            tmpmove = info['pv'][0]
                            if oldtmpmove is not None and tmpmove != oldtmpmove:
                                bestmovechanges += 1
                            
                    elif multipv == 2:
                        bm2 = pv[0]
                        bs2 = s
                        
                    # Save analysis time by exiting it if score difference
                    # between bestscore1 and bestcore2 is way below the
                    # minimum score difference based from user defined
                    # score thresholds
                    if t >= mintime and bs1 - bs2 < minscorediffcheck:
                        logging.warning('Exit search early, scorediff of {} is below minscorediff of {}'.format(
                                bs1 - bs2, minscorediffcheck))
                        break
                    
                    oldtmpmove = tmpmove
                    
                except (KeyError):
                    pass
                except Exception as e:
                    logging.error('Unexpected exception {} in in parsing engine analysis'.format(e))

        time.sleep(0.1)
        
        logging.info('Search is done!!'.format(engname))
        logging.info('game move       : {} ({})'.format(g_move, curboard.san(g_move)))
        logging.info('complexity      : {}'.format(bestmovechanges))
        logging.info('best move 1     : {}, best score 1: {}'.format(bm1, bs1))
        logging.info('best move 2     : {}, best score 2: {}'.format(bm2, bs2))
        logging.info('scorediff       : {}'.format(bs1 - bs2))
        
        # Don't save positions if score is already bad
        if bs1 < minbs1th3:
            logging.warning('Skip this pos, score {} is below minbs1th3 of {}'.format(bs1, minbs1th3))
            continue
        
        # If complexity is 1 or less and if bestmove1 is a capture, skip this position
        if board.is_capture(bm1) and bestmovechanges <= 1:
            logging.warning('Skip this pos, bm1 is a capture and pos complexity is below 2')
            continue
        
        if bs1 - bs2 < minbs1th3 - maxbs2th3:
            logging.warning('Skip this pos, min score diff of {} is below user min score diff of {}'.format(
                    bs1 - bs2, minbs1th3 - maxbs2th3))
            continue
        
        # Filter on --positional to skip positions
        if positional:
            # (1) Skip if bestmove1 is a capture or promote
            if board.is_capture(bm1) or len(str(bm1)) == 5:
                logging.warning('Skip this pos, the bestmove1 is a {} move'.format('promote' if len(str(bm1))==5 else 'capture'))
                continue

        # Save epd if criteria is satisfied
        is_save = False
        if positional:
            if positional_pos(board, bs1, bs2, minbs1th1, minbs1th2,
                               minbs1th3, maxbs2th1, maxbs2th2, maxbs2th3):
                is_save = True
        else:
            if interesting_pos(board, bs1, bs2, minbs1th1, minbs1th2,
                               minbs1th3, maxbs2th1, maxbs2th2, maxbs2th3):
                is_save = True
                
        # Create new epd
        ae_oper = 'Analyzing engine: ' + engname
        complexity_oper = 'Complexity: ' +  str(bestmovechanges)
        bs2_oper = 'bestscore2: ' + str(bs2)
        new_epd = board.epd(
                    bm = bm1,
                    ce = bs1,
                    sm = g_move,
                    acd = depth,
                    acs = int(t),                        
                    fmvn = board.fullmove_number,
                    hmvc = board.halfmove_clock,
                    pv = raw_pv,                        
                    c0 = c0_val,
                    c1 = complexity_oper,
                    c2 = bs2_oper,
                    c3 = ae_oper)
        
        # Save this new epd to either interesting.epd or dull.epd
        if is_save:
            logging.info('Save this position to {}'.format(outepdfn))
            with open(outepdfn, 'a') as f:
                f.write('{}\n'.format(new_epd))
                
            save_as_pgn(outpgnfn, game, fen, bm1)
        else:
            # Save all pos to dull.epd that were analyzed to a maxtime but
            # failed to be saved in interesting.epd. It can be useful to
            # improve the algorith by examing these positions visually.
            logging.info('Saved to {}'.format(dullfn))            
            with open(dullfn, 'a') as f:
                f.write('{}\n'.format(new_epd))

    
def main():
    parser = argparse.ArgumentParser(prog='Chess Chiller {}'.format(VERSION), 
                description='Generates interesting positions using an engine and ' +
                'some user defined score thresholds', epilog='%(prog)s')    
    parser.add_argument('-i', '--inpgn', help='input pgn file',
                        required=True)
    parser.add_argument('-o', '--outepd', help='output epd file, (default=interesting.epd)',
                        default='interesting.epd', required=False)
    parser.add_argument('-e', '--engine', help='engine file or path',
                        required=True)
    parser.add_argument('-t', '--threads', help='engine threads (default=1)',
                        default=1, type=int, required=False)
    parser.add_argument('-a', '--hash', help='engine hash in MB (default=128)',
                        default=128, type=int, required=False)
    parser.add_argument('-w', '--weight', help='weight file for NN engine like Lc0',
                        required=False)
    parser.add_argument('-n', '--mintime', help='analysis minimum time in sec (default=5.0)',
                        default=5.0, type=float, required=False)
    parser.add_argument('-x', '--maxtime', help='analysis maximum time in sec (default=15.0)',
                        default=15.0, type=float, required=False)
    parser.add_argument('--skipdraw', help='a flag to skip games with draw results',
                        action='store_true')
    parser.add_argument('--log', help='values can be debug, info, warning, error and critical (default=critical)',
                        default='critical', required=False)
    parser.add_argument('--pin', help='a flag when enabled will only save interesting' +
                        'position if not stm piece is pinned', action='store_true')
    parser.add_argument('--positional', help='a flag to save positional positions',
                        action='store_true')
    parser.add_argument('--minpiecevalue', help='minimum piece value on the board, N=B=3, R=5, Q=9, (default=0)',
                        default=0, type=int, required=False)
    parser.add_argument('--maxpiecevalue', help='maximum piece value on the board, N=B=3, R=5, Q=9, (default=62)',
                        default=62, type=int, required=False)
    parser.add_argument('--minbs1th1', help='minimum best score 1 threshold 1 (default=2000)',
                        default=2000, type=int, required=False)
    parser.add_argument('--minbs1th2', help='minimum best score 1 threshold 2 (default=1000)',
                        default=1000, type=int, required=False)
    parser.add_argument('--minbs1th3', help='minimum best score 1 threshold 3 (default=500)',
                        default=500, type=int, required=False)
    parser.add_argument('--maxbs2th1', help='maximum best score 2 threshold 1 (default=300)',
                        default=300, type=int, required=False)
    parser.add_argument('--maxbs2th2', help='maximum best score 2 threshold 2 (default=200)',
                        default=200, type=int, required=False)
    parser.add_argument('--maxbs2th3', help='maximum best score 3 threshold 3 (default=100)',
                        default=100, type=int, required=False)

    args = parser.parse_args()

    pgnfn = args.inpgn
    outepdfn = args.outepd
    thread_val = args.threads
    hash_val = args.hash    
    enginefn = args.engine
    weightsfile = args.weight
    mintime = args.mintime
    maxtime = args.maxtime
    skipdraw = args.skipdraw
    pin = args.pin
    positional = args.positional
    minpiecevalue = args.minpiecevalue
    maxpiecevalue = args.maxpiecevalue
    
    # Define logging levels
    if args.log == 'debug':
        # logging.DEBUG includes engine logs
        initialize_logger(logging.DEBUG)
    elif args.log == 'info':
        initialize_logger(logging.INFO)
    elif args.log == 'warning':
        initialize_logger(logging.WARNING)
    elif args.log == 'error':
        initialize_logger(logging.ERROR)
    else:
        initialize_logger(logging.CRITICAL)
   
    start_move = 16  # Stop the analysis when this move no. is reached
    dullfn = 'dull.epd'  # Save uninteresting positions in this file
    outpgnfn = 'interesting.pgn'
    
    # Adjust score thresholds to save interesting positions
    # (1) Positional score threshold, if flag --positional is set
    if positional:
        minbs1th1 = 100  # min bs1 (best score 1) threshold 1 in cp (centipawn)
        minbs1th2 = 50
        minbs1th3 = 0
        maxbs2th1 = 50   # max bs2 (best score 2) threshold 1
        maxbs2th2 = 0
        maxbs2th3 = -50
    # (2) Other score thresholds
    else:
        minbs1th1 = args.minbs1th1
        minbs1th2 = args.minbs1th2
        minbs1th3 = args.minbs1th3
        maxbs2th1 = args.maxbs2th1
        maxbs2th2 = args.maxbs2th2
        maxbs2th3 = args.maxbs2th3
        
    # Calculate minimum score diff check, while engine is seaching we exit
    # early if minscorediffcheck is not satisfied.
    scoredifflist = []
    scoredifflist.append(minbs1th1 - maxbs2th1)
    scoredifflist.append(minbs1th2 - maxbs2th2)
    scoredifflist.append(minbs1th3 - maxbs2th3)
    minscorediffcheck = min(scoredifflist)/2
    
    logging.info('pgn file: {}'.format(pgnfn))    
    logging.info('Conditions:')
    logging.info('mininum time               : {}s'.format(mintime))
    logging.info('maximum time               : {}s'.format(maxtime))
    logging.info('mininum score diff check   : {}'.format(minscorediffcheck))
    logging.info('mininum best score 1 th 1  : {}'.format(minbs1th1))
    logging.info('mininum best score 1 th 2  : {}'.format(minbs1th2))
    logging.info('mininum best score 1 th 3  : {}'.format(minbs1th3))
    logging.info('maximum best score 2 th 1  : {}'.format(maxbs2th1))
    logging.info('maximum best score 2 th 2  : {}'.format(maxbs2th2))
    logging.info('maximum best score 2 th 3  : {}'.format(maxbs2th3))
    logging.info('stm is not in check        : {}'.format('Yes'))
    logging.info('stop analysis move number  : {}'.format(start_move))
            
    # Define analyzing engine
    engine = chess.engine.SimpleEngine.popen_uci(enginefn)
    engname = engine.id['name']
    
    # Set Lc0 SmartPruningFactor to 0 to avoid analysis time pruning
    if 'lc0' in engname.lower():
        try:
            engine.configure({"SmartPruningFactor": 0})
        except:
            pass
    else:
        try:
            engine.configure({"Hash": hash_val})
        except:
            pass 
        
    try:
        engine.configure({"Threads": thread_val})
    except:
        pass
    
    # For NN engine that uses uci option WeightsFile similar to Lc0
    if weightsfile is not None:
        try:
            engine.configure({"WeightsFile": weightsfile})
        except:
            pass
        
    # Read pgn file and analyze positions in the game    
    gcnt = 0    
    with open(pgnfn, 'r') as pgn:
        game = chess.pgn.read_game(pgn)        
        while game:
            gcnt += 1 
            analyze_game(game,
                     engine,
                     enginefn,
                     hash_val,
                     thread_val,
                     start_move,
                     outepdfn,
                     gcnt,
                     engname,
                     dullfn,
                     outpgnfn,
                     mintime=mintime,
                     maxtime=maxtime,
                     minscorediffcheck=minscorediffcheck,
                     minbs1th1=minbs1th1,
                     minbs1th2=minbs1th2,    
                     minbs1th3=minbs1th3,
                     maxbs2th1=maxbs2th1,
                     maxbs2th2=maxbs2th2,    
                     maxbs2th3=maxbs2th3,
                     weightsfile=weightsfile,
                     skipdraw=skipdraw,
                     pin=pin,
                     positional=positional,
                     minpiecevalue=minpiecevalue,
                     maxpiecevalue=maxpiecevalue)
            
            # Analyze another game
            game = chess.pgn.read_game(pgn)
        
    engine.quit()


if __name__ == '__main__':
    main()
