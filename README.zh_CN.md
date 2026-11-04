[English](README.md) · **简体中文**

# 随身音乐遥控器

把随身小屏变成电脑网易云音乐的蓝牙遥控器。抬手查看歌名、播放进度和三行同步歌词，用三个按键调音量、切歌、播放暂停，还能开关电脑桌面歌词。

歌词早一点或晚一点，都能在设备上微调；亮度和自动息屏也可按习惯设置并保存。配套 Windows 桥接支持登录后隐藏运行，打开已配置的网易云即可使用。音频仍由电脑播放。需要下载配套桥接，已验证网易云 3.1.31.205174。

[下载 Windows 桥接与固件](https://github.com/wyh1351/passport-music/releases/latest) · [完整使用说明](docs/netease-music.zh_CN.md)

## 操作

| 按键 | 短按 | 双击 | 长按 |
| --- | --- | --- | --- |
| 上 | 音量 +5 | 音量 +20 | 上一首 |
| 下 | 音量 -5 | 音量 -20 | 下一首 |
| 确定 | 播放/暂停 | 桌面歌词开关 | 设置 |

## 开发与验证

基于 [FoloToy/ai-passport](https://gitee.com/FoloToy/ai-passport) 开发，保留原 BSP 与许可。开发前读 AGENTS.md。使用 ESP-IDF 5.5.3；运行 ./tools/validate.sh 完整验证；电脑依赖见 companion/requirements.txt，打包见 tools/package_music_bridge.ps1。

固件 v13；电脑桥接含歌词直连优先修复。构建和 57 项电脑回归及 C/BSP 测试通过。用户已验收按键、歌词同步/微调、桌面歌词、亮度/息屏、设置保存和关闭 FlClash 后切歌。完整 0x0 实刷、真实 Windows 重登录触发、长期续航及未来客户端兼容性未验证。

源代码沿用原项目 MIT 许可；字体及其他第三方资源的许可见 assets/README.zh_CN.md。封面为 AI 生成玩法示意图。
