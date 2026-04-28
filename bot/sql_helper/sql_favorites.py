from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint

from bot import LOGGER
from bot.sql_helper import Base, Session, engine


class EmbyFavorites(Base):
    """记录用户收藏的剧集、电影、演员等项目，用于 WebHook 推送。"""

    __tablename__ = "emby_favorites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    embyid = Column(String(64), nullable=False)
    embyname = Column(String(128), nullable=False)
    item_id = Column(String(64), nullable=False)
    item_name = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    __table_args__ = (
        UniqueConstraint("embyid", "item_id", name="uix_emby_item"),
    )


EmbyFavorites.__table__.create(bind=engine, checkfirst=True)


def sql_add_favorites(embyid: str, embyname: str, item_id: str, item_name: str, is_favorite: bool = True) -> bool:
    """
    添加或移除收藏记录。
    使用 embyname + item_id 作为幂等更新条件，避免 embyid 变更时产生脏数据。
    """
    try:
        with Session() as session:
            records = session.query(EmbyFavorites).filter(
                EmbyFavorites.embyname == embyname,
                EmbyFavorites.item_id == item_id,
            ).all()

            if is_favorite:
                if records:
                    primary = records[0]
                    primary.embyid = embyid
                    primary.item_name = item_name
                    primary.created_at = datetime.now()
                    for duplicate in records[1:]:
                        session.delete(duplicate)
                else:
                    session.add(
                        EmbyFavorites(
                            embyid=embyid,
                            embyname=embyname,
                            item_id=item_id,
                            item_name=item_name,
                        )
                    )
            else:
                for record in records:
                    session.delete(record)

            session.commit()
            return True
    except Exception as e:
        LOGGER.error(f"操作收藏记录失败: {str(e)}")
        return False


def sql_delete_favorites_by_embyid(embyid: str) -> bool:
    """在 Emby 账号被删除时，按 embyid 清理对应的收藏记录。"""
    try:
        with Session() as session:
            session.query(EmbyFavorites).filter(
                EmbyFavorites.embyid == embyid
            ).delete(synchronize_session=False)
            session.commit()
        return True
    except Exception as e:
        LOGGER.error(f"按 embyid 清理收藏记录失败: {str(e)}")
        return False
