from enum import Enum
from io import BytesIO
from PIL import Image, ImageDraw
from PIL.Image import Image as IMG
from typing import Tuple, List, Optional

from .utils import legal_word, load_font, save_jpg


class GuessResult(Enum):
    WIN = 0  # 猜出正确单词
    LOSS = 1  # 达到最大可猜次数，未猜出正确单词
    DUPLICATE = 2  # 单词重复
    ILLEGAL = 3  # 单词不合法


class Wordle(object):
    def __init__(self, word: str, meaning: str):
        self.word: str = word  # 单词
        self.meaning: str = meaning  # 单词释义
        self.word_lower: str = self.word.lower()
        self.length: int = len(word)  # 单词长度
        self.rows: int = self.length + 1  # 可猜次数
        self.guessed_words: List[str] = []  # 记录已猜单词

        self.block_size = (40, 40)  # 文字块尺寸
        self.block_padding = (10, 10)  # 文字块之间间距
        self.padding = (20, 20)  # 边界间距
        self.border_width = 2  # 边框宽度
        self.font_size = 20  # 字体大小
        self.font = load_font("KarnakPro-Bold.ttf", self.font_size)

        self.correct_color = (134, 163, 115)  # 存在且位置正确时的颜色
        self.exist_color = (198, 182, 109)  # 存在但位置不正确时的颜色
        self.wrong_color = (123, 123, 124)  # 不存在时颜色
        self.border_color = (123, 123, 124)  # 边框颜色
        self.bg_color = (255, 255, 255)  # 背景颜色
        self.font_color = (255, 255, 255)  # 文字颜色

    def guess(self, word: str) -> Optional[GuessResult]:
        if not legal_word(word):
            return GuessResult.ILLEGAL
        word = word.lower()
        if word in self.guessed_words:
            return GuessResult.DUPLICATE
        self.guessed_words.append(word)
        if word == self.word_lower:
            return GuessResult.WIN
        if len(self.guessed_words) == self.rows:
            return GuessResult.LOSS

    def draw_block(self, color: Tuple[int, int, int], letter: str) -> IMG:
        block = Image.new("RGB", self.block_size, self.border_color)
        block.paste(
            Image.new(
                "RGB",
                (
                    self.block_size[0] - self.border_width * 2,
                    self.block_size[1] - self.border_width * 2,
                ),
                color,
            ),
            (self.border_width, self.border_width),
        )
        if letter:
            letter = letter.upper()
            draw = ImageDraw.Draw(block)
            letter_size = self.font.getsize(letter)
            draw.text(
                (
                    (self.block_size[0] - letter_size[0]) / 2,
                    (self.block_size[1] - letter_size[1]) / 2,
                ),
                letter,
                font=self.font,
                fill=self.font_color,
            )
        return block

    def draw(self) -> BytesIO:
        board_width = (
            self.length * self.block_size[0]
            + (self.length - 1) * self.block_padding[0]
            + 2 * self.padding[0]
        )
        board_height = (
            self.rows * self.block_size[1]
            + (self.rows - 1) * self.block_padding[1]
            + 2 * self.padding[1]
        )
        board_size = (board_width, board_height)
        board = Image.new("RGB", board_size, self.bg_color)

        for i in range(self.rows):
            for j in range(self.length):
                letter = self.guessed_words[i][j] if len(self.guessed_words) > i else ""
                if letter:
                    if letter == self.word_lower[j]:
                        color = self.correct_color
                    elif letter in self.word_lower:
                        color = self.exist_color
                    else:
                        color = self.wrong_color
                else:
                    color = self.bg_color

                board.paste(
                    self.draw_block(color, letter),
                    (
                        self.padding[0]
                        + (self.block_size[0] + self.block_padding[0]) * j,
                        (
                            self.padding[1]
                            + (self.block_size[1] + self.block_padding[1]) * i
                        ),
                    ),
                )
        return save_jpg(board)

    def get_hint(self) -> str:
        letters = set()
        for word in self.guessed_words:
            for letter in word:
                if letter in self.word_lower:
                    letters.add(letter)
        return "".join([i if i in letters else "*" for i in self.word_lower])

    def draw_hint(self, hint: str) -> BytesIO:
        board = Image.new(
            "RGB",
            (
                self.length * self.block_size[0]
                + (self.length - 1) * self.block_padding[0]
                + 2 * self.padding[0],
                self.block_size[1] + 2 * self.padding[1],
            ),
            self.bg_color,
        )

        for i in range(len(hint)):
            letter = hint[i].replace("*", "")
            color = self.correct_color if letter else self.bg_color

            board.paste(
                self.draw_block(color, letter),
                (
                    self.padding[0] + (self.block_size[0] + self.block_padding[0]) * i,
                    (self.padding[1]),
                ),
            )
        return save_jpg(board)
