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

**以下命令需要加[命令前缀](https://v2.nonebot.dev/docs/api/config#Config-command_start) (默认为`/`)，可自行设置为空**

```
@机器人 + 猜单词
```

绿色块代表此单词中有此字母且位置正确

黄色块代表此单词中有此字母，但该字母所处位置不对

灰色块代表此单词中没有此字母

猜出单词或用光次数则游戏结束

可发送“结束”结束游戏；可发送“提示”查看提示

可使用 -l / --length 指定单词长度，默认为 5

可使用 -d / --dic 指定词典，默认为 CET4

支持的词典：GRE、考研、GMAT、专四、TOFEL、SAT、专八、IELTS、CET4、CET6


或使用 `wordle` 指令：

```
wordle [-l --length <length>] [-d --dic <dic>] [--hint] [--stop] [word]
```


### 示例

<div align="left">
  <img src="https://s2.loli.net/2022/03/25/nuNRBUgy8KsEjiW.png" width="400" />
</div>


### 特别感谢

- [SAGIRI-kawaii/sagiri-bot](https://github.com/SAGIRI-kawaii/sagiri-bot) 基于Graia Ariadne和Mirai的QQ机器人 SAGIRI-BOT
