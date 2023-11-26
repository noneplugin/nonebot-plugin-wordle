# nonebot-plugin-wordle

适用于 [Nonebot2](https://github.com/nonebot/nonebot2) 的 wordle 猜单词插件


### 安装

- 使用 nb-cli

```
nb plugin install nonebot_plugin_wordle
```

- 使用 pip

```
pip install nonebot_plugin_wordle
```


### 使用

**以下命令需要加[命令前缀](https://nonebot.dev/docs/appendices/config#command-start-和-command-separator) (默认为`/`)，可自行设置为空**

```
@机器人 + 猜单词
```

绿色块代表此单词中有此字母且位置正确；

黄色块代表此单词中有此字母，但该字母所处位置不对；

黄色块至多着色 **此单词中有这个字母的数量** 次；

灰色块代表此单词中没有此字母；

猜出单词或用光次数则游戏结束。

可发送“结束”结束游戏；可发送“提示”查看提示。

可使用 -l / --length 指定单词长度，默认为 5

可使用 -d / --dic 指定词典，默认为 CET4

支持的词典：GRE、考研、GMAT、专四、TOEFL、SAT、专八、IELTS、CET4、CET6


或使用 `wordle` 指令：

```
wordle [-l --length <length>] [-d --dic <dic>] [--hint] [--stop] [word]
```


### 示例

<div align="left">
  <img src="https://s2.loli.net/2022/03/25/nuNRBUgy8KsEjiW.png" width="400" />
</div>


### 说明

黄色块着色规则为：

```
黄色块至多着色 此单词中有这个字母的数量 次。
```

针对这个规则，下面的例子能帮您更好理解，并且更好猜测词语：

假设答案是 `xOOxxxxx`。（这个词并不存在，只是为了方便理解）

当用户猜测 `xxxxxxxO` 时，O这个字母由于存在但位置不同，会被着为黄色。

当用户猜测 `xxxxxxOO` 时，由于原先单词中有两个O，所以两个O都会被着色。

当用户猜测 `xxxxxOOO` 时，由于原先单词只有两个O，因此前两个O会被着色，第3个会被着为灰色。

当用户猜测 `xxOxxxxO` 时，第1个O由于位置正确，着为绿色。第2个O着为黄色。

当用户猜测 `xxOxxxOO` 时，第1个O着绿色，第2个O着黄色，第3个O着灰色。

当用户猜测 `xOOxxxxO` 时，前两个O着绿色，第3个O着灰色。


### 特别感谢

- [SAGIRI-kawaii/sagiri-bot](https://github.com/SAGIRI-kawaii/sagiri-bot) 基于Graia Ariadne和Mirai的QQ机器人 SAGIRI-BOT
