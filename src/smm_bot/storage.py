import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class UserProfile:
    user_id: int
    niche: str = "не указана"
    tone: str = "дружелюбно, ясно, уверенно"
    style: str = "коротко, структурно, без канцелярита"


class Storage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                create table if not exists profiles (
                    user_id integer primary key,
                    niche text not null,
                    tone text not null,
                    style text not null,
                    updated_at text default current_timestamp
                );

                create table if not exists sessions (
                    user_id integer primary key,
                    last_source_text text,
                    last_result text,
                    photo_context text,
                    updated_at text default current_timestamp
                );

                create table if not exists history (
                    id integer primary key autoincrement,
                    user_id integer not null,
                    kind text not null,
                    payload text not null,
                    created_at text default current_timestamp
                );
                """
            )

    def get_profile(self, user_id: int) -> UserProfile:
        with self._connect() as conn:
            row = conn.execute("select * from profiles where user_id = ?", (user_id,)).fetchone()
        if row is None:
            return UserProfile(user_id=user_id)
        return UserProfile(
            user_id=user_id,
            niche=row["niche"],
            tone=row["tone"],
            style=row["style"],
        )

    def set_profile(self, profile: UserProfile) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into profiles (user_id, niche, tone, style, updated_at)
                values (?, ?, ?, ?, current_timestamp)
                on conflict(user_id) do update set
                    niche = excluded.niche,
                    tone = excluded.tone,
                    style = excluded.style,
                    updated_at = current_timestamp
                """,
                (profile.user_id, profile.niche, profile.tone, profile.style),
            )

    def save_session(
        self,
        user_id: int,
        *,
        last_source_text: str | None = None,
        last_result: str | None = None,
        photo_context: str | None = None,
    ) -> None:
        current = self.get_session(user_id)
        with self._connect() as conn:
            conn.execute(
                """
                insert into sessions (user_id, last_source_text, last_result, photo_context, updated_at)
                values (?, ?, ?, ?, current_timestamp)
                on conflict(user_id) do update set
                    last_source_text = excluded.last_source_text,
                    last_result = excluded.last_result,
                    photo_context = excluded.photo_context,
                    updated_at = current_timestamp
                """,
                (
                    user_id,
                    last_source_text if last_source_text is not None else current.get("last_source_text"),
                    last_result if last_result is not None else current.get("last_result"),
                    photo_context if photo_context is not None else current.get("photo_context"),
                ),
            )

    def get_session(self, user_id: int) -> dict[str, str | None]:
        with self._connect() as conn:
            row = conn.execute("select * from sessions where user_id = ?", (user_id,)).fetchone()
        if row is None:
            return {"last_source_text": None, "last_result": None, "photo_context": None}
        return {
            "last_source_text": row["last_source_text"],
            "last_result": row["last_result"],
            "photo_context": row["photo_context"],
        }

    def append_history(self, user_id: int, kind: str, payload: Any) -> None:
        data = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                "insert into history (user_id, kind, payload) values (?, ?, ?)",
                (user_id, kind, data),
            )
