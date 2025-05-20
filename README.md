TODO:
- проставь энвы (см. .env.example)
- запусти постгрю (тестилось на 15й версии, но другая тоже подойдет) и создай базу
- прогони миграции
- доделай ручку, к которой написан TODO комментарий

Как запустить приложение, прогнать линтер и миграции - см. Makefile

За помощью обращайся к чему угодно, но начать лучше с документации:
- [poetry](https://python-poetry.org/)
- [yoyo](https://ollycope.com/software/yoyo/latest/)
- [strawberry](https://strawberry.rocks/docs)
- [graphql](https://graphql.org/learn/)
- [fastapi](https://fastapi.tiangolo.com/)
- [asyncpg](https://magicstack.github.io/asyncpg/current/)
- [ruff](https://docs.astral.sh/ruff/)
- [mypy](https://mypy.readthedocs.io/en/stable/getting_started.html)

Мы знаем, что наше тестовое может решить (или помочь решить) ChatGPT.
Мы ок с использованием вспомогательных инструментов для разработки,
но, пожалуйста, не делайте этого бездумно.

А есть ли в коде баги? Кто знает...




### Примеры GraphQL запросов

```
# 1. Получить все книги (с пагинацией)
{
  books(limit: 100, offset: 0) {
    title
    author {
      name
    }
  }
}

# 2. Найти книги по автору (несколько авторов)
{
  books(authorIds: [1, 2, 3]) {
    title
    author {
      name
    }
  }
}

# 3. Поиск книг по названию (регистронезависимый поиск)
{
  books(search: "dorian") {
    title
    author {
      name
    }
  }
}

# 4. Комбинированный поиск (автор + название)
{
  books(authorIds: [1], search: "dorian") {
    title
    author {
      name
    }
  }
}

# 5. Получение с пагинацией (получаем вторую страницу по 10 элементов)
{
  books(limit: 10, offset: 10) {
    title
    author {
      name
    }
  }
}

# 6. Пример с использованием всех параметров
{
  books(
    authorIds: [1, 2],
    search: "dorian",
    limit: 10,
    offset: 0
  ) {
    title
    author {
      name
    }
  }
}
```