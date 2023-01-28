import re
import shlex
import asyncio
from io import BytesIO
from asyncio import TimerHandle
from dataclasses import dataclass
from typing import Dict, List, Optional, NoReturn, Union

from nonebot.typing import T_State
from nonebot.matcher import Matcher
from nonebot.exception import ParserExit
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule, ArgumentParser
from nonebot import on_command, on_shell_command, on_message
from nonebot.params import (
    ShellCommandArgv,
    CommandArg,
    CommandStart,
    EventPlainText,
    EventToMe,
)

from nonebot.adapters.onebot.v11 import Bot as V11Bot
from nonebot.adapters.onebot.v11 import Message as V11Msg
from nonebot.adapters.onebot.v11 import MessageSegment as V11MsgSeg
from nonebot.adapters.onebot.v11 import MessageEvent as V11MEvent
from nonebot.adapters.onebot.v11 import GroupMessageEvent as V11GMEvent

from nonebot.adapters.onebot.v12 import Bot as V12Bot
from nonebot.adapters.onebot.v12 import Message as V12Msg
from nonebot.adapters.onebot.v12 import MessageSegment as V12MsgSeg
from nonebot.adapters.onebot.v12 import MessageEvent as V12MEvent
from nonebot.adapters.onebot.v12 import GroupMessageEvent as V12GMEvent
from nonebot.adapters.onebot.v12 import ChannelMessageEvent as V12CMEvent

from .utils import dic_list, random_word
from .data_source import Wordle, GuessResult

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
    extra={
        "unique_name": "wordle",
        "example": "@小Q 猜单词\nwordle -l 6 -d CET6",
        "author": "meetwq <meetwq@gmail.com>",
        "version": "0.2.0",
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
    bot: Union[V11Bot, V12Bot],
    matcher: Matcher,
    event: Union[V11MEvent, V12MEvent],
    argv: List[str] = ShellCommandArgv(),
):
    await handle_wordle(bot, matcher, event, argv)


def get_cid(bot: Union[V11Bot, V12Bot], event: Union[V11MEvent, V12MEvent]):
    if isinstance(event, V11MEvent):
        cid = f"{bot.self_id}_{event.sub_type}_"
    else:
        cid = f"{bot.self_id}_{event.detail_type}_"

    if isinstance(event, V11GMEvent) or isinstance(event, V12GMEvent):
        cid += str(event.group_id)
    elif isinstance(event, V12CMEvent):
        cid += f"{event.guild_id}_{event.channel_id}"
    else:
        cid += str(event.user_id)

    return cid


def game_running(
    bot: Union[V11Bot, V12Bot], event: Union[V11MEvent, V12MEvent]
) -> bool:
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
        bot: Union[V11Bot, V12Bot],
        matcher: Matcher,
        event: Union[V11MEvent, V12MEvent],
        msg: Union[V11Msg, V12Msg] = CommandArg(),
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
shortcut("结束", ["--stop"], aliases={"停", "停止游戏", "结束游戏"}, rule=game_running)


word_matcher = on_message(Rule(game_running) & get_word_input, block=True, priority=12)


@word_matcher.handle()
async def _(
    bot: Union[V11Bot, V12Bot],
    matcher: Matcher,
    event: Union[V11MEvent, V12MEvent],
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
    bot: Union[V11Bot, V12Bot],
    matcher: Matcher,
    event: Union[V11MEvent, V12MEvent],
    argv: List[str],
):
    async def send(
        message: Optional[str] = None, image: Optional[BytesIO] = None
    ) -> NoReturn:
        if not (message or image):
            await matcher.finish()

        if isinstance(bot, V11Bot):
            msg = V11Msg()
            if image:
                msg.append(V11MsgSeg.image(image))
        else:
            msg = V12Msg()
            if image:
                resp = await bot.upload_file(
                    type="data", name="wordle", data=image.getvalue()
                )
                file_id = resp["file_id"]
                msg.append(V12MsgSeg.image(file_id))

        if message:
            msg.append(message)
        await matcher.finish(msg)

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
