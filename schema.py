from contextlib import asynccontextmanager
from functools import partial

import strawberry
from databases import Database
from fastapi import FastAPI
from strawberry.fastapi import BaseContext, GraphQLRouter
from strawberry.types import Info

from settings import Settings


class Context(BaseContext):
    """Контекст GraphQL запроса."""
    db: Database

    def __init__(self, db: Database) -> None:
        super().__init__()  # Вызываем конструктор базового класса
        self.db = db


@strawberry.type
class Author:
    name: str


@strawberry.type
class Book:
    title: str
    author: Author


@strawberry.type
class Query:
    """
    Класс для определения запросов GraphQL.
    """

    @strawberry.field
    async def books(
            self,
            info: Info[Context, None],
            # Исправлена ошибка, которая потенциально могла привести приложение к падению
            author_ids: list[int] | None = None,
            search: str | None = None,
            limit: int | None = 100,
            offset: int = 0,
    ) -> list[Book]:
        """
        Получение книг с опциональной фильтрацией по автору, поиску и пагинацией.

        Arguments:
            author_ids: Опциональный список ID авторов для фильтрации
            search: Опциональный поисковый запрос для названий книг
            limit: Максимальное количество возвращаемых результатов
            offset: Количество пропускаемых результатов (для пагинации)

        Returns:
            List of Book objects
        """
        try:
            # Проверка входных параметров
            if limit is not None and limit < 1:
                raise ValueError("Лимит должен быть больше 0")
            if offset < 0:
                raise ValueError("Смещение должно быть неотрицательным")

            # Гибкий и безопасный (от SQL-инъекций) запрос с поддержкой пагинации и регистроназависимым поиском
            query = """
                -- основной запрос
                SELECT b.id, b.title, a.name as author_name 
                FROM books b
                JOIN authors a ON b.author_id = a.id
                -- фильтрация по автарам
                WHERE ($1 IS NULL OR b.author_id = ANY($1))
                -- фильтрация по названию
                -- используетс ILIKE для регистронезависимого поиска
                AND ($2 IS NULL OR b.title ILIKE '%' || $2 || '%')
                -- сортировка и пагинация
                ORDER BY b.title ASC
                LIMIT $3 OFFSET $4
            """

            # Подготовка параметров со значениями по умолчанию
            params = [
                author_ids if author_ids else None,
                search.lower() if search else None,
                limit,
                offset
            ]

            # Выполнение запроса с таймаутом для предотвращения зависания
            rows = await info.context.db.fetch_all(query, params, timeout=5.0)

            if not rows:
                # Если нет результатов, возвращаем пустой список
                return []
            
            return [
                Book(
                    title=row["title"],
                    author=Author(name=row["author_name"]),
                )
                for row in rows
            ]

        except Exception as e:
            print(f"Что-то пошло не так: {e}")
            return []


# Database configuration
settings = Settings()
db = Database(
    url=f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_SERVER}:{settings.DB_PORT}/{settings.DB_NAME}",
)


@asynccontextmanager
async def lifespan(app: FastAPI, db: Database):
    """Асинхронный контекст приложения."""
    async with db:
        yield
    await db.disconnect()

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(  # type: ignore
    schema,
    context_getter=partial(Context, db),
)

app = FastAPI(lifespan=partial(lifespan, db=db))
app.include_router(graphql_app, prefix="/graphql")
