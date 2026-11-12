[English](README.md) · **简体中文**

# 随身音乐遥控器

把 AI Passport 变成电脑网易云音乐的蓝牙遥控器：抬手看歌名、进度和三行同步歌词，按键调网易云内部音量、切歌、播放暂停，还能开关电脑桌面歌词。

新版电脑控制器把安装、连接状态和设置放进一个窗口。首次点击“开始使用”，以后从桌面或托盘打开；设备、网易云和歌词是否正常，一眼就能看清。网易云收进托盘后，也能一键唤回原窗口。

九款像素背景、耳机猫／小狗／小兔／企鹅随心选。播放时轻晃，暂停时闭眼，进入设置也跟随音乐。歌词快慢、亮度和自动息屏都能调，改完自动保存。

适用 Windows 桌面版网易云音乐，需配套电脑控制器；声音由电脑播放。

<img src="docs/images/passport-music-cover.png" width="480" alt="Passport Music interface">

现版界面渲染，歌曲与歌词为演示内容。

[九款背景](docs/images/passport-music-wallpapers.png) · [电脑控制器](docs/images/passport-music-pets.png) · [按键](docs/images/passport-music-controls.png) · [设置](docs/images/passport-music-settings.png)

## 开始使用

1. 在社区刷入玩法固件。
2. 下载并解压电脑控制器，打开 `PassportMusicControl.exe`，点击“开始使用”。
3. 点击“打开网易云”并播放歌曲。
4. 首次在 Windows 蓝牙设置中配对 **Passport Music**，输入设备六位码。

以后从桌面快捷方式或托盘打开控制器；关闭窗口仍在后台运行。

[电脑控制器与固件 v1.3.1](https://github.com/wyh1351/passport-music/releases/tag/v1.3.1) · [完整使用说明](docs/netease-music.zh_CN.md)

## 按键

| 按键 | 短按 | 双击 | 长按 |
| --- | --- | --- | --- |
| 上 | 网易云音量 +5 | +20 | 上一首 |
| 下 | 网易云音量 -5 | -20 | 下一首 |
| 确定 | 播放/暂停 | 开关电脑桌面歌词 | 设置 |

音量数字为百分点。设置中上下选择，短按确定进入或返回，长按确定回主页。

## 兼容性

需要 Windows、蓝牙和网易云桌面版；已验证 3.1.31.205174。菜单为中文，支持中文/西文、日文假名和现代韩文；其他文字或表情可能不显示。网易云更新后若控制失效，先用配套启动器重新打开。

## 从源码构建

Windows 电脑端：安装 Python 3.12，执行 `python -m pip install -r companion/requirements-gui.txt pyinstaller==6.22.3`，再运行 `python tools/build_windows_companion.py --output dist/PassportMusic`。请选择新的输出目录；工程路径较长时使用较短的输出路径，并指定 `--work-dir C:/Temp`。构建器不会打包本机配置或日志。

设备固件：激活 ESP-IDF 5.5.3 后运行 `./tools/validate.sh --firmware`，得到经过布局验证的 `build/FoloToy-AI-Passport-full.bin`；仅完整合并镜像用于从 0x0 刷写。环境和调试归档说明见 [构建文档](docs/development/engineering/build-and-test.zh_CN.md)。

## 来源与许可

基于 [FoloToy AI Passport](https://gitee.com/FoloToy/ai-passport) 开发。项目许可与第三方字体说明见 [LICENSE](LICENSE) 和 [素材说明](assets/README.zh_CN.md)。
