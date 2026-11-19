"""配置。数据库连接串从环境变量读，不写死在代码里。"""

import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "mysql+pymysql://root@localhost:3306/historia?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
