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
    """Тип книги с информацией об авторе."""
    id: int
    title: str
    author: Author


@strawberry.enum
class SortDirection:
    """Направление сортировки."""
    ASC = "ASC"
    DESC = "DESC"

@strawberry.enum
class SortField:
    """Поля для сортировки."""
    TITLE = "title"
    AUTHOR_NAME = "author_name"

@strawberry.type
class Query:
    """
    Класс для определения запросов GraphQL.
    Поддерживает выбор полей, сортировку и пагинацию.
    """

    @strawberry.field
    async def books(
            self,
            info: Info[Context, None],
            # Параметр author_ids должен быть списком ID авторов или None для получения всех книг
            author_ids: list[int] | None = None,
            # Поисковый запрос по названию книги
            search: str | None = None,
            # Максимальное количество результатов
            limit: int | None = 100,
            # Смещение для пагинации
            offset: int = 0,
            # Параметры сортировки
            sort_field: SortField | None = SortField.TITLE,
            # Направление сортировки (ASC или DESC)
            sort_direction: SortDirection | None = SortDirection.ASC,
    ) -> list[Book]:
        """
        Получение книг с опциональной фильтрацией по автору, поиску и пагинации.

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

            # Безопасный SQL-запрос с параметризацией
            query = """
                -- основной запрос
                SELECT b.id, b.title, a.name as author_name 
                FROM books b
                JOIN authors a ON b.author_id = a.id
                -- фильтрация по авторам
                WHERE (COALESCE($1::text, '') = '' OR b.author_id = ANY($1::bigint[]))
                -- фильтрация по названию
                AND (COALESCE($2::text, '') = '' OR b.title ILIKE '%' || $2 || '%')
                -- сортировка с обработкой NULL значений
                ORDER BY 
                    CASE $5
                        WHEN 'title' THEN COALESCE(b.title, '')
                        WHEN 'author_name' THEN COALESCE(a.name, '')
                    END $6
                LIMIT $3 OFFSET $4
            """

            # Подготовка параметров сортировки
            sort_field = "title" if sort_field == SortField.TITLE else "author_name"
            sort_direction = "ASC" if sort_direction == SortDirection.ASC else "DESC"
            
            # Подготовка параметров запроса
            params = [
                author_ids if author_ids else [],
                search.lower() if search else "",
                limit,
                offset,
                sort_field,
                sort_direction
            ]

            # Выполнение запроса с таймаутом для предотвращения зависания
            rows = await info.context.db.fetch_all(query, params, timeout=5.0)

            if not rows:
                # Если нет результатов, возвращаем пустой список
                return []
            
            return [
                Book(
                    id=row["id"],
                    title=row["title"],
                    author=Author(name=row["author_name"]),
                )
                for row in rows
            ]

        except Exception as e:
            print(f"Ошибка при выполнении запроса: {type(e).__name__}: {str(e)}")
            # Возвращаем пустой список вместо выброса ошибки для GraphQL клиента
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
