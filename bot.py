#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import sys
import string
from time import sleep

try:
    import telegram
except ImportError:
    sys.path.append('/home/konst/build/python-telegram-bot')
    sys.path.append('/home/konst/build/future/src')
    import telegram

try:
    from urllib.error import URLError
except ImportError:
    from urllib2 import URLError # python 2


def main():
    # Telegram Bot Authorization Token
    bot = telegram.Bot('161872750:AAG4HAstuF3jbH-cYpdqeXcoj00qojWL_uY')

    # get the first pending update_id, this is so we can skip over it in case
    # we get an "Unauthorized" exception.
    try:
        update_id = bot.getUpdates()[0].update_id
    except IndexError:
        update_id = None

    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    context = TalkContext()
    while True:
        try:
            update_id = echo(bot, update_id, context)
        except telegram.TelegramError as e:
            # These are network problems with Telegram.
            if e.message in ("Bad Gateway", "Timed out"):
                sleep(1)
            elif e.message == "Unauthorized":
                # The user has removed or blocked the bot.
                update_id += 1
            else:
                raise e
        except URLError as e:
            # These are network problems on our end.
            sleep(1)


def echo(bot, update_id, context):

    # Request updates after the last update_id
    for update in bot.getUpdates(offset=update_id, timeout=10):
        # chat_id is required to reply to any message
        chat_id = update.message.chat_id
        update_id = update.update_id + 1
        message = update.message.text

        if message:
            # Reply to the message
            response = context.do_response(message)
            bot.sendMessage(chat_id=chat_id,
                            text=response)

    return update_id


class TalkContext:
    help_message = """Доступные команды:

/help — показать справку
/newgame — начать новую игру

Выберите цвет, далее вводите координаты вашего хода, например, b2
"""

    your_move_message = "Ваш ход"

    choose_mark_message = """Выберите 1 или 2:
1: Играть крестиком
2: Ноликом
"""

    def __init__(self):
        self.game = None

    def do_response(self, request_string):
        stripped = request_string.strip()
        if stripped == '/help':
            return TalkContext.help_message
        if self.game is None:
            self.game = Game()
            return("Добро пожаловать!\n" + TalkContext.choose_mark_message)
        if stripped == '/newgame':
            return TalkContext.choose_mark_message
        if self.game.current_status is Game.GameStatus.Creating:
            if stripped == "1":
                self.game.set_ai_is_cross(False)
                return ("\n" + self.game.board_to_string() +
                        TalkContext.your_move_message)
            elif stripped == "2":
                self.game.set_ai_is_cross(True)
                self.game.ai_move()
                return ("\n" + self.game.board_to_string() +
                        TalkContext.your_move_message)
            else:
                return "Введите 1 или 2"
        else:
            try_move = self.game.human_move(stripped)
            if try_move is None:
                if(self.game.current_status is Game.GameStatus.HumanWon):
                    self.game = Game()
                    return ("Случилось почти невероятное (шутка). " +
                            "Вы выиграли!!\n")
                if(self.game.current_status is Game.GameStatus.Draw):
                    self.game = Game()
                    return "Ничья\n"
                self.game.ai_move()
                position = "\n" + self.game.board_to_string()
                if(self.game.current_status is Game.GameStatus.AIWon):
                    position = position + "Вы проиграли\n"
                    self.game = Game()
                elif(self.game.current_status is Game.GameStatus.Draw):
                    position = position + "Ничья\n"
                    self.game = Game()
                else:
                    position = position + "Ваш ход\n"
                return position
            else:
                return "Неправильный ход\n" + TalkContext.help_message


class Game:
    class Square:
        class Cross:
            symbol = '_x'

        class Zero:
            symbol = '_o'

        class Empty:
            symbol = '__'

    class GameStatus:
        class Creating:
            pass

        class InProgress:
            pass

        class AIWon:
            pass

        class HumanWon:
            pass

        class Draw:
            pass

    class BadMoveReason:
        class SquareFilled:
            pass

        class GameNotStarted:
            pass

        class GameFinished:
            pass

        class OpponentsMove:
            pass

        class InvalidSquare:
            pass

    def __init__(self):
        self.position = [Game.Square.Empty for x in xrange(9)]
        self.ai_is_cross = None
        # index of the last played square
        self.last_move = None
        self.current_status = Game.GameStatus.Creating
        self.is_humans_move = None
        self.move_counter = 0

    def set_ai_is_cross(self, arg):
        self.ai_is_cross = arg
        self.current_status = Game.GameStatus.InProgress
        self.is_humans_move = not arg

    # returns None if move is successful or BadMoveReason if something is wrong
    def can_move(self):
        if self.current_status is Game.GameStatus.Creating:
            return Game.BadMoveReason.GameNotStarted
        elif ((self.current_status is Game.GameStatus.AIWon) or
              (self.current_status is Game.GameStatus.HumanWon) or
              (self.current_status is Game.GameStatus.Draw)):
            return Game.BadMoveReason.GameFinished
        else:
            return None

    def human_can_move(self):
        can_move = self.can_move()
        if can_move is not None:
            return can_move
        if not self.is_humans_move:
            return Game.BadMoveReason.OpponentsMove
        else:
            return None

    def ai_can_move(self):
        can_move = self.can_move()
        if can_move is not None:
            return can_move
        if self.is_humans_move:
            return Game.BadMoveReason.OpponentsMove
        else:
            return None

    @staticmethod
    def move_to_index(move):
        letter = move[0]
        digit = move[1]
        if ((letter not in string.ascii_letters) or
                (digit not in string.digits)):
            return Game.BadMoveReason.InvalidSquare
        x_coord = ord(letter) - ord('a')
        if not ((x_coord >= 0) and (x_coord < 3)):
            x_coord = ord(letter) - ord('A')
            if not ((x_coord >= 0) and (x_coord < 3)):
                return Game.BadMoveReason.InvalidSquare
        y_coord = ord(digit) - ord('1')
        if not ((y_coord >= 0) and (y_coord < 3)):
            return Game.BadMoveReason.InvalidSquare
        return y_coord * 3 + x_coord

    def ai_mark(self):
        return Game.Square.Cross if self.ai_is_cross else Game.Square.Zero

    def human_mark(self):
        return Game.Square.Zero if self.ai_is_cross else Game.Square.Cross

    # returns None if move is successful or BadMoveReason if something is wrong
    # move is in format
    def human_move(self, move):
        can_move = self.human_can_move()
        if can_move is not None:
            return can_move
        else:
            index = Game.move_to_index(move)
            if(type(index) != int):
                return index
            if(self.position[index] is Game.Square.Empty):
                self.move_counter += 1
                self.position[index] = self.human_mark()
                self.update_game_status()
                self.is_humans_move = False
                self.last_move = index
            else:
                return Game.BadMoveReason.SquareFilled
        return None

    def ai_move(self):
        can_move = self.ai_can_move()
        if can_move is not None:
            return can_move
        square = self.best_move(self.ai_mark(), self.human_mark())
        self.move_counter += 1
        self.position[square] = self.ai_mark()
        self.update_game_status()
        self.is_humans_move = True
        self.last_move = square
        return None

    @staticmethod
    def check_horiz_line(pos, mark, line_num):
        offset = line_num * 3
        return((pos[offset] is mark) and (pos[offset + 1] is mark) and
               (pos[offset + 2] is mark))

    @staticmethod
    def check_vert_line(pos, mark, line_num):
        return((pos[line_num] is mark) and (pos[line_num + 3] is mark) and
               (pos[line_num + 6] is mark))

    @staticmethod
    def check_diagonals(pos, mark):
        first_diagonal = ((pos[0] is mark) and (pos[4] is mark) and
                          (pos[8] is mark))
        second_diagonal = ((pos[2] is mark) and (pos[4] is mark) and
                           (pos[6] is mark))
        return(first_diagonal or second_diagonal)

    @staticmethod
    def check_wins_with(pos, mark):
        for num in xrange(3):
            if Game.check_horiz_line(pos, mark, num):
                return True
            if Game.check_vert_line(pos, mark, num):
                return True
        return Game.check_diagonals(pos, mark)

    def check_wins(self):
        mark_to_check = (self.human_mark() if self.is_humans_move else
                         self.ai_mark())
        if Game.check_wins_with(self.position, mark_to_check):
            self.current_status = (Game.GameStatus.HumanWon if
                                   self.human_mark() is mark_to_check else
                                   Game.GameStatus.AIWon)

    def check_draws(self):
        if self.move_counter == 9:
            self.current_status = Game.GameStatus.Draw

    def update_game_status(self):
        self.check_draws()
        self.check_wins()

    def best_move(self, mark, opponent_mark):
        pos = self.position
        if self.move_counter == 0:
            return 4
        if self.move_counter == 1:
            if pos[4] is opponent_mark:
                return 8
            else:
                return 4
        if self.move_counter == 2:
            if pos[0] is opponent_mark:
                return 8
            if pos[1] is opponent_mark:
                return 0
            if pos[2] is opponent_mark:
                return 6
            if pos[3] is opponent_mark:
                return 0
            if pos[5] is opponent_mark:
                return 2
            if pos[6] is opponent_mark:
                return 2
            if pos[7] is opponent_mark:
                return 6
            if pos[8] is opponent_mark:
                return 0
            else:
                return first_vacant_square(self.position)
        if self.move_counter == 3:
            (possible_threat, _) = Game.find_threats(self.position,
                                                     opponent_mark)
            if possible_threat is not None:
                return possible_threat
            else:
                try_angle = Game.first_vacant_angle(self.position)
                if try_angle is not None:
                    return try_angle
                else:
                    return Game.first_vacant_square(self.position)
        else:
            (possible_threat, _) = Game.find_threats(self.position, mark)
            if possible_threat is not None:
                return possible_threat
            double_threat = self.find_double_threat(mark)
            if double_threat is not None:
                return double_threat
            angle = Game.first_vacant_angle(self.position)
            if angle is not None:
                return angle
            return Game.first_vacant_square(self.position)

    @staticmethod
    def first_vacant_square(pos, offset=0):
        for square_num in xrange(offset, 9):
            if pos[square_num] is Game.Square.Empty:
                return square_num
        return None

    @staticmethod
    def first_vacant_angle(pos):
        for square_num in [0, 2, 6, 8]:
            if pos[square_num] is Game.Square.Empty:
                return square_num
        return None

    @staticmethod
    def find_threats(pos, opponent_mark):
        forced_move = None
        threat_counter = 0
        first_vacant = Game.first_vacant_square(pos)
        while(first_vacant is not None):
            copied = pos[:]
            copied[first_vacant] = opponent_mark
            if Game.check_wins_with(copied, opponent_mark):
                forced_move = first_vacant
                threat_counter += 1
            first_vacant = Game.first_vacant_square(pos, first_vacant + 1)
        return (forced_move, threat_counter)

    def find_double_threat(self, mark):
        first_vacant = Game.first_vacant_square(self.position)
        while(first_vacant is not None):
            copied = self.position[:]
            copied[first_vacant] = mark
            (threat, threat_count) = Game.find_threats(copied, mark)
            if threat_count >= 2:
                return threat
            first_vacant = Game.first_vacant_square(self.position,
                                                    first_vacant + 1)
        return None

    def board_to_string(self):
        buf = []
        buf.append("__a_b_c\n1")
        for index in xrange(0, 3):
            buf.append(self.position[index].symbol)
        buf.append("\n2")
        for index in xrange(3, 6):
            buf.append(self.position[index].symbol)
        buf.append("\n3")
        for index in xrange(6, 9):
            buf.append(self.position[index].symbol)
        buf.append("\n")
        return "".join(buf)

if __name__ == '__main__':
    main()
