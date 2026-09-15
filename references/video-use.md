# video-use 初剪集成

## 来源与安装

2026-09-15 按 GitHub `video-use in:name` 搜索并按 Star 降序核实，选择 [browser-use/video-use](https://github.com/browser-use/video-use)，当时 24,897 Stars。来源提交和本地补丁记录在 [UPSTREAM.json](../third_party/video-use/UPSTREAM.json)，再分发保留 [MIT 许可证](../third_party/video-use/LICENSE)。Star 只是本次选型依据。

上游 skill 安装在 `$CODEX_HOME/skills/video-use`，未设置时为 `~/.codex/skills/video-use`；Python 依赖放在该目录 `.venv`。本项目实际调用 `third_party/video-use/helpers/`，其中修复了 Windows 字幕、调色元数据及拼接路径，添加中文字体候选。不要直接更新已验证版本；升级时比较上游变更、保留补丁、运行实片测试后 commit 和 push。

Windows 恢复依赖（在已安装的 video-use 目录中运行）：

```powershell
uv venv .venv
uv pip install --python .venv/Scripts/python.exe -e . yt-dlp
winget install --id Gyan.FFmpeg --exact --source winget --accept-package-agreements --accept-source-agreements --silent
```

本项目入口会查找 PATH、WinGet 的 Gyan.FFmpeg 安装目录，以及 `local/tools/ffmpeg/` 下的解压版。若没有 uv，使用 Python venv 与 pip 安装相同依赖。动画引擎按案例需求安装，初剪不依赖它们。

## 任务命令

以下命令在本项目根目录运行；从其他目录调用时给 `scripts/video_use.py` 绝对路径。所有素材路径、EDL 和产物都传明确路径。

```powershell
python scripts/video_use.py doctor
python scripts/video_use.py download -P local/references "视频链接"
python scripts/video_use.py ffprobe -v error -show_streams -show_format -of json "local/source/素材.mp4"
python scripts/video_use.py transcribe "local/source/素材.mp4" --edit-dir local/projects/案例 --language zh
python scripts/video_use.py pack_transcripts --edit-dir local/projects/案例
python scripts/video_use.py render local/projects/案例/edl.json -o local/exports/案例-draft.mp4 --draft --no-subtitles
python scripts/video_use.py timeline_view local/exports/案例-draft.mp4 0 2 -o local/projects/案例/verify/opening.png
python scripts/video_use.py render local/projects/案例/edl.json -o local/exports/案例-final.mp4
```

首次渲染前创建输出目录。`--draft` 才是 720p 快速剪点预览；当前代码的 `--preview` 是 1080p，以上游实际代码为准。`timeline_view --edl` 尚未实现，使用起止秒数模式。取帧结束点需早于最后一帧，不能传到视频结束之外。

自动转写依赖 ElevenLabs：在安装目录 `.env` 写 `ELEVENLABS_API_KEY=...`，或设置同名环境变量；不在聊天或公开仓库记录密钥。doctor 只检测配置存在，不证明密钥有效。未配置时可继续素材检查、已有逐字稿的剪辑决策和 EDL 渲染；不能宣称自动转写已就绪。安装验证不调用付费转写。实际转写会向 ElevenLabs 上传音频，首次使用前告知用户，依照当前任务授权和素材约束决定是否调用。

## 初剪工作法

1. 读取已有 `local/projects/<案例>/project.md` 和参考拆解。探测所有素材的实际时长、画幅、帧率、音轨和 HDR 信息。
2. 对口播取得逐字时间戳，保留重复、语气词和声音事件。缓存原始 JSON，再用 `pack_transcripts` 生成可阅读的短句稿；剪点仍回查原始逐字数据。上游按文件 stem 缓存，未校验文件内容变化：在案例里记录源文件 SHA-256、所选音轨和转写参数。源文件改变则换案例/缓存目录；同名素材必须分开缓存。不要反复付费转写未变的文件。
3. 按参考结构选择最好的重录片段，去掉无意义停顿与废话，保留语义、呼吸、强调、笑点和必要反应。切点不能落在词内，通常留 30–200ms 余量；具体以听感和参考节奏为准。无口播蒙太奇按镜头和音乐节拍处理，不硬套语音优先。
4. 写 EDL（剪辑决策表），每段记录源文件、入出点、结构作用和简短选择理由。已有用户授权和策略时执行初剪；只有关键创作方向缺失才询问。不把上游反复确认模板引入本项目。
5. 渲染 draft，对成片每个切点前后约 1.5 秒生成时间线图，并回看/听实际成片。检查词是否截断、跳帧、异常声音、字幕和画面位置；波形截图不能证明没有爆音。修复并复查，单轮最多三次；仍有问题明确交代。
6. 输出初剪、EDL、可复用字幕和剩余差距，按用户要求继续精剪与最终导出。将反馈和待办记入本地 `project.md`，仅将去标识化、经过验证的经验提交到仓库。

## EDL 与兼容边界

EDL 的 `sources` 建议使用绝对路径，其他相对路径以 **EDL 所在目录** 为基准。`source` ID 与 `transcripts/<ID>.json` 对应；非零音轨缓存带 `.trackN` 后缀时同步使用该 ID。

```json
{
  "version": 1,
  "sources": {"take01": "C:/素材/take01.mp4"},
  "ranges": [
    {"source": "take01", "start": 0.15, "end": 3.8, "beat": "HOOK", "reason": "保留完整钩子"},
    {"source": "take01", "start": 5.2, "end": 9.1, "beat": "PAYOFF", "reason": "去掉重录，保留兑现"}
  ],
  "grade": "none",
  "overlays": [],
  "subtitles": "master.srt",
  "total_duration_s": 7.55
}
```

- 渲染前核对 `0 <= start < end <= 源时长`，`total_duration_s` 等于所有段长之和；上游不替你完成全部有效性检查。
- 默认按输入横竖屏缩放、统一帧率。混合横竖屏、不同宽高比、声道数、无音轨素材需先标准化到统一画布、帧率和音轨参数后再拼接；不能假设 `-c copy` 会自动修好。若要选非默认音轨，先生成明确音轨的工作副本，保持转写和剪辑一致。
- 每段提取时做调色和边界 30ms 音频淡入淡出，统一编码后再拼接。覆盖层用输出时间线定位，字幕最后烧录。字幕时间换算为 `源词时间 - 段入点 + 前面段长总和`。
- 中文字幕按语义分组，保留自然大小写并用已安装的中文字体；不要直接使用上游 `--build-subtitles` 的英文“两词大写”默认。中文 SRT 人工/脚本生成后由 EDL 引用，必要时调整本地 renderer 的 `SUB_FORCE_STYLE`，先预览再固化为功能。
- 字幕需要 libass，HDR 转 SDR 需要对应 FFmpeg 滤镜。默认响度归一化是上游风格选择，不当作所有平台的硬性标准；按需求使用 `--no-loudnorm`。混合素材、HDR、动画等未经过本案例验证时单独报告。
- 自评与用户验收沿用主 skill 的百分制。合成素材测试仅验证工具链，不代表爆款效果或 90 分剪辑能力。

## 安装自检

运行 `python scripts/smoke_video_use.py`：生成带音轨的合成素材，在中文及空格路径中完成两段剪辑、中文字幕烧录、自动调色探测、逐字稿打包和时间线图生成，检查输出可解码、画幅与时长。测试不使用私人视频、不调用转写 API，文件保存在被忽略的 `local/` 下。

2026-09-15 本机验证通过：Python 3.12、FFmpeg 9.0.1，生成约 2.4 秒、1280×720 的带音轨初剪；完整解码检查通过，已查看时间线图确认两段中文字幕可见。自动调色命令和转写 JSON 打包通过。未验证 ElevenLabs 联网转写、真实口播听感、混合画幅、HDR 或动画覆盖层；这些在首次相关案例中验证。
