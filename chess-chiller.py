# -*- coding: utf-8 -*-
"""
chess-chiller.py

Requirements:
    * python 3
    * python-chess v0.26.0 or up, https://github.com/niklasf/python-chess
    * Analysis engine that supports multipv and movetime commands
    
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


def interesting_pos(board, bs1, bs2, mib1s1, mib1s2, mib1s3, mab2s1, mab2s2, mab2s3):
    """ 
    board: board position
    bs1: bestscore1 from multipv 1
    bs2: bestscore2 from multipv 2
    
    mib1s1: minimum best score1, threshold 1
    mib1s2: minimum score2, threshold 2
    mib1s3: minimum score3, threshold 3
    
    mib1s1 > mib1s2 > mib1s3
    
    mab2s1: maximum best score2, threshold 1
    mab2s2: maximum best score2, threshold 2
    mab2s3: maximum best score2, threshold 3
    
    mab2s1 > mab2s2 > mab2s3
    
    """
    logging.info('bestscore1: {}, bestscore2: {}'.format(bs1, bs2))
    if bs1 >= mib1s1:
        # mate score
        if bs1 >= 30000 and bs2 <= 2*mab2s1:
            return True
        if bs2 <= mab2s1:
            return True
    elif bs1 >= mib1s2:
        if bs2 <= mab2s2:
            return True
    elif bs1 >= mib1s3:
        if bs2 <= mab2s3:
            return True
    
    logging.info('Not an interesting pos: {}'.format(board.fen()))
    
    return False


def positional_pos(board, bs1, bs2, mib1s1, mib1s2, mib1s3, mab2s1, mab2s2, mab2s3):
    """ 
    * The engine bestscore1 is not winning and bestscore2 is not lossing
    * The score gap between bestscore1 and bestcore2 is small    
    """
    if bs1 >= mib1s1 and bs1 <= mib1s1 + 50:
        if bs2 <= mab2s1 and bs2 >= mab2s1 - 25:
            return True
    if bs1 >= mib1s2 and bs1 <= mib1s1:
        if bs2 <= mab2s2 and bs2 >= mab2s2 - 25:
            return True
    if bs1 >= mib1s3 and bs1 <= mib1s2:
        if bs2 <= mab2s3 and bs2 >= mab2s3 - 25:
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
                 analysis_start_move_num,
                 outepdfn, gcnt, engname, mintime=2.0, maxtime=10.0,
                 minscorediffcheck=25, minbest1score1=2000,
                 minbest1score2=1000, minbest1score3=500,
                 maxbest2score1=300, maxbest2score2=200,
                 maxbest2score3=100, weightsfile=None, skipdraw=True,
                 pin=False, positional=False, minpiecevalue=62):
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
        
        # Print the fen before g_move is made on the board
        poscnt += 1  
        
        print('game {} / position {} \r'.format(gcnt, poscnt), end='')
        
        logging.info('game {} / position {}'.format(gcnt, poscnt))
        logging.info('{}'.format(board.fen()))
        logging.info('game move: {}'.format(curboard.san(g_move)))
        
        pcval = piece_value(curboard)
        if pcval < minpiecevalue:
            logging.warning('Skip this pos piece value {} is below minimmum of {}'.format(pcval, minpiecevalue))
            continue
        
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
                        if t >= mintime and bs1 < minbest1score3/2:
                            logging.warning('Exit search early, current best score is only {}'.format(bs1))
                            break
                        
                        # Record bestmove move changes to determine position complexity
                        if 'depth' in info and 'pv' in info \
                                and 'score' in info \
                                and not 'lowerbound' in info \
                                and not 'upperbound' in info \
                                and depth >= 4:
                            tmpmove = info['pv'][0]
                            if tmpmove is not None and tmpmove != oldtmpmove:
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
                    logging.error('Error in parsing engine analysis', exc_info=e)

        time.sleep(0.1)
        
        logging.info('Search is done!!'.format(engname))
        logging.info('game move       : {} ({})'.format(g_move, curboard.san(g_move)))
        logging.info('complexity      : {}'.format(bestmovechanges))
        logging.info('best move 1     : {}, best score 1: {}'.format(bm1, bs1))
        logging.info('best move 2     : {}, best score 2: {}'.format(bm2, bs2))
        logging.info('scorediff       : {}'.format(bs1 - bs2))
        
        # Don't save positions if score is already bad
        if bs1 < minbest1score3:
            logging.warning('Skip this pos, score {} is below minbest1score3 of {}'.format(bs1, minbest1score3))
            continue
        
        # If complexity is 1 or less and if bestmove1 is a capture, skip this position
        if board.is_capture(bm1) and bestmovechanges <= 1:
            logging.warning('Skip this pos, bm1 is a capture and pos complexity is below 2')
            continue
        
        if bs1 - bs2 < minbest1score3 - maxbest2score3:
            logging.warning('Skip this pos, min score diff of {} is below user min score diff of {}'.format(
                    bs1 - bs2, minbest1score3 - maxbest2score3))
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
            if positional_pos(board, bs1, bs2, minbest1score1, minbest1score2,
                               minbest1score3, maxbest2score1, maxbest2score2,
                               maxbest2score3):
                is_save = True
        else:
            if interesting_pos(board, bs1, bs2, minbest1score1, minbest1score2,
                               minbest1score3, maxbest2score1, maxbest2score2,
                               maxbest2score3):
                is_save = True
                
        if is_save:
            logging.warning('Save this position!!')
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
            print(new_epd)
            with open(outepdfn, 'a') as f:
                f.write('{}\n'.format(new_epd))

    
def main():
    parser = argparse.ArgumentParser(prog='Chess Chiller {}'.format(VERSION), 
                description='Generates interesting positions using an engine and ' +
                'some user defined score thresholds', epilog='%(prog)s')    
    parser.add_argument('-i', '--inpgn', help='input pgn file',
                        required=True)
    parser.add_argument('-o', '--outepd', help='output epd file, default=interesting.epd',
                        default='interesting.epd', required=False)
    parser.add_argument('-e', '--engine', help='engine file or path',
                        required=True)
    parser.add_argument('-t', '--threads', help='engine threads (default=1)',
                        default=1, type=int, required=False)
    parser.add_argument('-a', '--hash', help='engine hash in MB (default=128)',
                        default=128, type=int, required=False)
    parser.add_argument('-w', '--weight', help='weight file for NN engine',
                        required=False)
    parser.add_argument('-n', '--mintime', help='analysis minimum time in sec (default=2.0)',
                        default=2.0, type=float, required=False)
    parser.add_argument('-x', '--maxtime', help='analysis maximum time in sec (default=10.0)',
                        default=10.0, type=float, required=False)
    parser.add_argument('--skipdraw', help='a flag to skip games with draw results',
                        action='store_true')
    parser.add_argument('--log', help='values can be debug, info, warning, error and critical (default=critical)',
                        default='critical', required=False)
    parser.add_argument('--pin', help='a flag when enabled will only save interesting' +
                        'position if not stm piece is pinned', action='store_true')
    parser.add_argument('--positional', help='a flag to save positional positions',
                        action='store_true')
    parser.add_argument('--minpiecevalue', help='minimum piece value on the board, N=B=3, R=5, Q=9, (default=62)',
                        default=62, type=int, required=False)

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
        # Default
        initialize_logger(logging.CRITICAL)
   
    start_move = 16  # Stop the analysis when this move no. is reached
    
    # Adjust score thresholds to save interesting positions
    # (1) Positional score threshold, if flag --positional is set
    if positional:
        minbest1score1 = 100  # cp, threshold 1
        minbest1score2 = 50   # cp, threshold 2
        minbest1score3 = 0    # cp, threshold 3
        maxbest2score1 = 50   # cp, threshold 4
        maxbest2score2 = 0   # cp, threshold 5
        maxbest2score3 = -50  # cp, threshold 6
    else:
        minbest1score1 = 1000  # cp, threshold 1
        minbest1score2 = 500  # cp, threshold 2
        minbest1score3 = 300  # cp, threshold 3
        maxbest2score1 = 300  # cp, threshold 4
        maxbest2score2 = 200  # cp, threshold 5
        maxbest2score3 = 150   # cp, threshold 6
        
    # Calculate minimum score diff check, while engine is seaching we exit
    # early if minscorediffcheck is not satisfied.
    scoredifflist = []
    scoredifflist.append(minbest1score1 - maxbest2score1)
    scoredifflist.append(minbest1score2 - maxbest2score2)
    scoredifflist.append(minbest1score3 - maxbest2score3)
    minscorediffcheck = min(scoredifflist)/2
    
    logging.info('pgn file: {}'.format(pgnfn))    
    logging.info('Conditions:')
    logging.info('mininum time               : {}s'.format(mintime))
    logging.info('maximum time               : {}s'.format(maxtime))
    logging.info('mininum score diff check   : {}'.format(minscorediffcheck))
    logging.info('mininum best 1 score 1     : {}'.format(minbest1score1))
    logging.info('mininum best 1 score 2     : {}'.format(minbest1score2))
    logging.info('mininum best 1 score 3     : {}'.format(minbest1score3))
    logging.info('maximum best 2 score 1     : {}'.format(maxbest2score1))
    logging.info('maximum best 2 score 2     : {}'.format(maxbest2score2))
    logging.info('maximum best 2 score 3     : {}'.format(maxbest2score3))
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
                     mintime=mintime,
                     maxtime=maxtime,
                     minscorediffcheck=minscorediffcheck,
                     minbest1score1=minbest1score1,
                     minbest1score2=minbest1score2,    
                     minbest1score3=minbest1score3,
                     maxbest2score1=maxbest2score1,
                     maxbest2score2=maxbest2score2,    
                     maxbest2score3=maxbest2score3,
                     weightsfile=weightsfile,
                     skipdraw=skipdraw,
                     pin=pin,
                     positional=positional,
                     minpiecevalue=minpiecevalue)
            game = chess.pgn.read_game(pgn)
        
    engine.quit()


if __name__ == '__main__':
    main()
