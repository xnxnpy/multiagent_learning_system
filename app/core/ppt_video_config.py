"""PPT 视频生成配置常量"""

# Playwright 渲染参数
RENDER_WIDTH = 1280
RENDER_HEIGHT = 720

# TTS 参数
TTS_VOICE = "x4_yezi"
TTS_SPEED = 50       # 0-100, 50 = normal
TTS_VOLUME = 50      # 0-100
TTS_AUE = "opus"     # 音频编码: opus → mp3

# FFmpeg 参数
FFMPEG_CODEC_VIDEO = "libx264"
FFMPEG_CODEC_AUDIO = "aac"
FFMPEG_TUNE = "stillimage"
FFMPEG_PIX_FMT = "yuv420p"
SUBTITLE_FONT_SIZE = 22
SUBTITLE_FONT_NAME = "Microsoft YaHei"
SUBTITLE_MARGIN_V = 30
SUBTITLE_OUTLINE = 2

# 字幕分割标点
SENTENCE_DELIMITERS = "。！？；\n"
CLAUSE_DELIMITERS = "，、,"

# PPT 页面范围
MIN_PAGES = 5
MAX_PAGES = 10

# OSS 上传路径模板
OSS_VIDEO_KEY_TEMPLATE = "videos/{user_id}/{stage_id}/teaching_video.mp4"
