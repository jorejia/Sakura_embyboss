# 🌸 Sakura_embyboss 初学练习版

<p align="center">
<img src="image/bot2.png" alt="bot"><br>
<a href="https://github.com/berry8838/Sakura_embyboss/stargazers"><img src="https://img.shields.io/github/stars/berry8838/Sakura_embyboss" alt="stars"></a> 
<a href="https://github.com/berry8838/Sakura_embyboss/forks"><img src="https://img.shields.io/github/forks/berry8838/Sakura_embyboss" alt="forks"></a> 
<a href="https://github.com/berry8838/Sakura_embyboss/issues"><img src="https://img.shields.io/github/issues/berry8838/Sakura_embyboss" alt="issue"></a>  
<a href="https://github.com/berry8838/Sakura_embyboss/blob/master/LICENSE"><img src="https://img.shields.io/github/license/berry8838/Sakura_embyboss" alt="license"></a> 
<a href="https://hub.docker.com/r/jingwei520/sakura_embyboss" ><img src="https://img.shields.io/docker/v/jingwei520/sakura_embyboss/latest?logo=docker" alt="docker"></a>
<a href="" ><img src="https://img.shields.io/badge/platform-amd64-pink" alt="plat"></a>
</p>

## 📜 项目说明
- [项目文档 https://berry8838.github.io/Sakura_embyboss](https://berry8838.github.io/Sakura_embyboss) ，安装使用请点击此
- **推荐使用 Debian 11操作系统，AMD处理器架构的vps搭建**
- 解决不了大的技术问题（因为菜菜），如需要，请自行fork修改，~~如果能提点有意思的pr更好啦~~
- 反馈请尽量 issue，看到会处理

> **声明：本项目仅供学习交流使用，仅作为辅助工具借助tg平台方便用户管理自己的媒体库成员，对用户的其他行为及内容毫不知情**

## 线路与 Pro 线路配置

在 `config.json` 中修改 `default_line_id` 和 `line_options`。每条线路的 `id` 就是写入
Sidecar `emby_user.use_line` 的数字；`pro: true` 表示该线路只对直连 Pro 用户显示和开放。
可以同时标记任意多条 Pro 线路，例如：

```json
"default_line_id": 1,
"line_options": [
  {"id": 1, "name": "直连一线", "pro": false},
  {"id": 2, "name": "直连二线", "pro": false},
  {"id": 3, "name": "直连三线 Pro", "pro": true},
  {"id": 4, "name": "直连四线 Pro", "pro": true},
  {"id": 7, "name": "海外 Pro", "pro": true}
]
```

对应的 OpenResty `pro_line_auth.lua` 必须配置相同编号：

```lua
pro_line_ids = { 3, 4, 7 },
```

Sakura 修改 `config.json` 后需要重启 Bot；OpenResty 修改 Lua 配置后需要 reload。
`default_line_id` 指向的线路是 Pro 到期时切回的默认线路，应保持为非 Pro。
线路编号不要求连续，但不能重复。

## 账号与直连 Pro 到期时间权重

在 `config.json` 中可分别设置账号到期时间和直连 Pro 到期时间的权重：

```json
"expiry_weights": {
  "account": 1.0,
  "line_pro": 1.0
}
```

账号到期检测会先处理已经到期的直连 Pro，再尝试米币自动续期。只有米币没有续期成功、
账号已经到期且直连 Pro 仍有效时，才按上述权重计算两个时间的加权平均值。只有平均值
严格晚于本次检测时间 1 天，账号和直连 Pro 才会同时改为该时间；等于或不足 1 天时，
账号按原到期流程处理。两个权重必须为非负数，且不能同时为 `0`。修改后需要重启 Bot。

## 💐 Our Contributors

<a href="https://github.com/berry8838/Sakura_embyboss/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=berry8838/Sakura_embyboss" />
</a>  

## 特别感谢（排序不分先后）

- [Pyrogram • 一个现代、优雅和异步的MTProto API框架](https://github.com/pyrogram/pyrogram)
- [Nezha探针 • 自托管、轻量级、服务器和网站监控运维工具](https://github.com/naiba/nezha)
- [小宝 • 按钮风格](https://t.me/EmbyClubBot)
- [MisakaF_Emby • 启发](https://github.com/MisakaFxxk/MisakaF_Emby)
  以及  [EMBY API官方文档](https://swagger.emby.media/?staticview=true#/UserService)
- [Nolovenodie • 播放榜单海报推送借鉴](https://github.com/Nolovenodie/EmbyTools)
- [罗宝 • 提供的代码援助](https://github.com/dddddluo)
- [折花 • 日榜周榜推送设计图](https://github.com/U41ovo)<br>
<img src="image/bixin.jpg" alt="比心" height=300>
