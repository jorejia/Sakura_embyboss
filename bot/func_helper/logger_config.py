"""
logger_config - 

Author:susu
Date:2023/12/12
"""
# logger_config.py

import datetime
import logging
from loguru import logger

# 转换为亚洲上海时区
# shanghai = pytz.timezone("Asia/Shanghai")
# Now = datetime.datetime.now(shanghai)
Now = datetime.datetime.now()

# 使用 add() 方法来配置日志器的输出格式和级别
"""笔记： rotation：一种条件，指示何时应关闭当前记录的文件并开始新的文件。
         retention ：过滤旧文件的指令，在循环或程序结束期间会删除旧文件。 方便好用，比loging好"""
logger.add(f"log/log_{Now:%Y%m%d}.txt", format="{time} - {name} - {level} - {message}", level="INFO", rotation="00:00",
           retention="30 days")


class PyrogramContextFilter(logging.Filter):
    def filter(self, record):
        if not record.name.startswith("pyrogram"):
            return True

        message = record.getMessage()
        if "Unable to connect due to network issues" in message:
            record.msg = (
                "【Telegram连接阶段】Pyrogram 在 bot.start() 建立 Telegram MTProto 会话时连接失败；"
                "连接对象是 Telegram 数据中心，不是 Emby/Sidecar/WebHook。原始错误："
                + message
            )
            record.args = ()
        elif "Connection failed! Trying again" in message:
            record.msg = (
                "【Telegram连接阶段】Pyrogram 连接 Telegram MTProto 数据中心失败，正在按库内重试策略重连。"
                "这仍然发生在 bot.start() 启动阶段。原始提示："
                + message
            )
            record.args = ()
        return True


pyrogram_handler = logging.StreamHandler()
pyrogram_handler.setLevel(logging.WARNING)
pyrogram_handler.addFilter(PyrogramContextFilter())
pyrogram_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

pyrogram_logger = logging.getLogger("pyrogram")
pyrogram_logger.setLevel(logging.WARNING)
pyrogram_logger.propagate = False
if not pyrogram_logger.handlers:
    pyrogram_logger.addHandler(pyrogram_handler)


def logu(name):
    return logger.bind(name=name)
