import asyncio
import re
import shlex
from asyncio import TimerHandle
from dataclasses import dataclass
from io import BytesIO
from typing import Dict, List, NoReturn, Optional

from nonebot import on_command, on_message, on_shell_command, require
from nonebot.adapters import Bot, Event, Message
from nonebot.exception import ParserExit
from nonebot.matcher import Matcher
from nonebot.params import (
    CommandArg,
    CommandStart,
    EventPlainText,
    EventToMe,
    ShellCommandArgv,
)
from nonebot.plugin import PluginMetadata
from nonebot.rule import ArgumentParser, Rule
from nonebot.typing import T_State

require("nonebot_plugin_saa")
require("nonebot_plugin_session")

from nonebot_plugin_saa import Image, MessageFactory
from nonebot_plugin_saa import __plugin_meta__ as saa_plugin_meta
from nonebot_plugin_session import SessionIdType
from nonebot_plugin_session import __plugin_meta__ as session_plugin_meta
from nonebot_plugin_session import extract_session

assert saa_plugin_meta.supported_adapters
assert session_plugin_meta.supported_adapters
supported_adapters = (
    saa_plugin_meta.supported_adapters & session_plugin_meta.supported_adapters
)

from .data_source import GuessResult, Wordle
from .utils import dic_list, random_word

__plugin_meta__ = PluginMetadata(
    name="猜单词",
    description="wordle猜单词游戏",
    usage=(
        "@我 + “猜单词”开始游戏；\n"
        "答案为指定长度单词，发送对应长度单词即可；\n"
        "绿色块代表此单词中有此字母且位置正确；\n"
        "黄色块代表此单词中有此字母，但该字母所处位置不对；\n"
        "灰色块代表此单词中没有此字母；\n"
        "猜出单词或用光次数则游戏结束；\n"
        "发送“结束”结束游戏；发送“提示”查看提示；\n"
        "可使用 -l/--length 指定单词长度，默认为5；\n"
        "可使用 -d/--dic 指定词典，默认为CET4\n"
        f"支持的词典：{'、'.join(dic_list)}"
    ),
    type="application",
    homepage="https://github.com/noneplugin/nonebot-plugin-wordle",
    supported_adapters=supported_adapters,
    extra={
        "unique_name": "wordle",
        "example": "@小Q 猜单词\nwordle -l 6 -d CET6",
        "author": "meetwq <meetwq@gmail.com>",
        "version": "0.3.0",
    },
)


parser = ArgumentParser("wordle", description="猜单词")
parser.add_argument("-l", "--length", type=int, default=5, help="单词长度")
parser.add_argument("-d", "--dic", default="CET4", help="词典")
parser.add_argument("--hint", action="store_true", help="提示")
parser.add_argument("--stop", action="store_true", help="结束游戏")
parser.add_argument("word", nargs="?", help="单词")


@dataclass
class Options:
    length: int = 0
    dic: str = ""
    hint: bool = False
    stop: bool = False
    word: str = ""


games: Dict[str, Wordle] = {}
timers: Dict[str, TimerHandle] = {}

wordle = on_shell_command("wordle", parser=parser, block=True, priority=13)


@wordle.handle()
async def _(
    bot: Bot,
    matcher: Matcher,
    event: Event,
    argv: List[str] = ShellCommandArgv(),
):
    await handle_wordle(bot, matcher, event, argv)


def get_cid(bot: Bot, event: Event):
    return extract_session(bot, event).get_id(SessionIdType.GROUP)


def game_running(bot: Bot, event: Event) -> bool:
    cid = get_cid(bot, event)
    return bool(games.get(cid, None))


def get_word_input(state: T_State, msg: str = EventPlainText()) -> bool:
    if re.fullmatch(r"^[a-zA-Z]{3,8}$", msg):
        state["word"] = msg
        return True
    return False


def shortcut(cmd: str, argv: List[str] = [], **kwargs):
    command = on_command(cmd, **kwargs, block=True, priority=12)

    @command.handle()
    async def _(
        bot: Bot,
        matcher: Matcher,
        event: Event,
        msg: Message = CommandArg(),
    ):
        try:
            args = shlex.split(msg.extract_plain_text().strip())
        except:
            args = []
        await handle_wordle(bot, matcher, event, argv + args)


# 命令前缀为空则需要to_me，否则不需要
def smart_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me


shortcut("猜单词", ["--length", "5", "--dic", "CET4"], rule=smart_to_me)
shortcut("提示", ["--hint"], aliases={"给个提示"}, rule=game_running)
shortcut("结束", ["--stop"], aliases={"结束游戏", "停止游戏"}, rule=game_running)


word_matcher = on_message(Rule(game_running) & get_word_input, block=True, priority=12)


@word_matcher.handle()
async def _(
    bot: Bot,
    matcher: Matcher,
    event: Event,
    state: T_State,
):
    word: str = state["word"]
    await handle_wordle(bot, matcher, event, [word])


async def stop_game(matcher: Matcher, cid: str):
    timers.pop(cid, None)
    if games.get(cid, None):
        game = games.pop(cid)
        msg = "猜单词超时，游戏结束"
        if len(game.guessed_words) >= 1:
            msg += f"\n{game.result}"
        await matcher.finish(msg)


def set_timeout(matcher: Matcher, cid: str, timeout: float = 300):
    timer = timers.get(cid, None)
    if timer:
        timer.cancel()
    loop = asyncio.get_running_loop()
    timer = loop.call_later(
        timeout, lambda: asyncio.ensure_future(stop_game(matcher, cid))
    )
    timers[cid] = timer


async def handle_wordle(
    bot: Bot,
    matcher: Matcher,
    event: Event,
    argv: List[str],
):
    async def send(
        message: Optional[str] = None, image: Optional[BytesIO] = None
    ) -> NoReturn:
        if not (message or image):
            await matcher.finish()

        msg_builder = MessageFactory([])
        if image:
            msg_builder.append(Image(image))
        if message:
            if image:
                message = "\n" + message
            msg_builder.append(message)
        await msg_builder.send()
        await matcher.finish()

    try:
        args = parser.parse_args(argv)
    except ParserExit as e:
        if e.status == 0:
            await send(__plugin_meta__.usage)
        await send()

    options = Options(**vars(args))

    cid = get_cid(bot, event)
    if not games.get(cid, None):
        if options.word:
            await send()

        if options.word or options.stop or options.hint:
            await send("没有正在进行的游戏")

        if not (options.length and options.dic):
            await send("请指定单词长度和词典")

        if options.length < 3 or options.length > 8:
            await send("单词长度应在3~8之间")

        if options.dic not in dic_list:
            await send("支持的词典：" + ", ".join(dic_list))

        word, meaning = random_word(options.dic, options.length)
        game = Wordle(word, meaning)
        games[cid] = game
        set_timeout(matcher, cid)

        await send(f"你有{game.rows}次机会猜出单词，单词长度为{game.length}，请发送单词", game.draw())

    if options.stop:
        game = games.pop(cid)
        msg = "游戏已结束"
        if len(game.guessed_words) >= 1:
            msg += f"\n{game.result}"
        await send(msg)

    game = games[cid]
    set_timeout(matcher, cid)

    if options.hint:
        hint = game.get_hint()
        if not hint.replace("*", ""):
            await send("你还没有猜对过一个字母哦~再猜猜吧~")
        await send(image=game.draw_hint(hint))

    word = options.word
    if not re.fullmatch(r"^[a-zA-Z]{3,8}$", word):
        await send()
    if len(word) != game.length:
        await send("请发送正确长度的单词")

    result = game.guess(word)
    if result in [GuessResult.WIN, GuessResult.LOSS]:
        games.pop(cid)
        await send(
            ("恭喜你猜出了单词！" if result == GuessResult.WIN else "很遗憾，没有人猜出来呢")
            + f"\n{game.result}",
            game.draw(),
        )
    elif result == GuessResult.DUPLICATE:
        await send("你已经猜过这个单词了呢")
    elif result == GuessResult.ILLEGAL:
        await send(f"你确定 {word} 是一个合法的单词吗？")
    else:
        await send(image=game.draw())
