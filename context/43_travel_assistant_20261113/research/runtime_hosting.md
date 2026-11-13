# Движок и хостинг Red Wings Travel Assistant

Проверено 13.11.2026. Рекомендация: **Node.js 24 + Pi agent-core/ai в отдельном контейнере на российском VPS**, с собственным HTTP API и только предметными инструментами чтения. Запускать терминальный coding agent для пассажирского сервиса не требуется. Прямой OpenAI-compatible клиент — более простой вариант для первого однопроходного ответа и полезный транспортный эталон при проверке шлюза.

**Статус: архитектура обоснована; live-интеграция не проверена.** Прочитаны публичные источники и OpenAPI МАИ; ключи не искались, запросы с авторизацией и LLM-генерации не выполнялись. Установки, Git-операции и публикация отсутствуют. Источники, HTTP-результаты и извлечение OpenAPI находятся в [runtime_sources.json](runtime_sources.json).

## Что такое Pi и что известно о Яндексе

Pi — TypeScript-проект Mario Zechner, агентная обвязка и библиотеки. Это самостоятельное название, а не сокращение Python. Старый URL `badlogic/pi-mono` сейчас перенаправляет на `earendil-works/pi`. В проверенном commit `35019ae989fc6e45eb18d0c757ef81dd18cb30e3` пакеты называются `@earendil-works/pi-agent-core` и `@earendil-works/pi-ai`, версия в package.json — 1.5.2, требование Node.js — ≥22.19.0. Старые примеры с namespace `@mariozechner` нужно сверять с закреплённой версией. [Репозиторий](https://github.com/earendil-works/pi), [package.json agent-core](https://github.com/earendil-works/pi/blob/35019ae989fc6e45eb18d0c757ef81dd18cb30e3/packages/agent/package.json).

Разделение компонентов:

- `pi-ai`: транспорт к моделям, сообщения, описания tools, streaming, usage/cost. Поддерживает собственный provider с `baseUrl`, моделью и адаптером Chat Completions либо Responses.
- `pi-agent-core`: состояние диалога, цикл «модель → tool → результат → модель», события и отмена. Исполняемый код инструментов задаёт приложение.
- `pi-coding-agent`: готовый CLI/SDK для программирования. Его инструменты файлов и команд не нужны этому продукту.

Основание: [ai README](https://github.com/earendil-works/pi/blob/35019ae989fc6e45eb18d0c757ef81dd18cb30e3/packages/ai/README.md#custom-providers), [agent-core README](https://github.com/earendil-works/pi/blob/35019ae989fc6e45eb18d0c757ef81dd18cb30e3/packages/agent/README.md).

Утверждение **«Яндекс использует Pi» не подтверждено найденными первичными источниками**. Поиск по официальным доменам Яндекса и сочетаниям Yandex/Яндекс + pi-mono/Pi agent harness не дал подтверждающего кейса. Официальная инструкция Yandex Cloud показывает OpenAI Agents SDK — это другой SDK. Каталог Pi содержит `pi-yandex-bridge` с автором `unitdhda`: это свидетельство наличия интеграционного пакета, а не использования Pi внутри Яндекса. Отсутствие найденного подтверждения не доказывает отсутствие внутреннего использования. [Инструкция Яндекса](https://yandex.cloud/en/docs/tutorials/serverless/streaming-openai-agent), [запись пакета Pi](https://pi.dev/packages/pi-yandex-bridge).

Подтверждённый пример применения Pi у платформенного поставщика есть у Cloudflare: официальная документация описывает Pi harness и Pi Durable в Agents SDK. Это не означает, что соответствующие Durable Objects/Containers доступны через Sites. [Cloudflare Harnesses](https://developers.cloudflare.com/agents/harnesses/).

## API МАИ: установленный протокол и неизвестные

Публичный `GET https://api-ai.mai.ru/openapi.json` вернул 200: OpenAPI 3.1.0, заголовок LiteLLM API, версия в документе 1.106.4. Полный документ: 2 052 095 байт, SHA-256 `5fe6995e9ee80e0f844c316b8a70bb1633417b7f6c25a76ac5ebd19becc12505`; время чтения 13.11.2026 12:32 UTC. Это описание развёрнутого шлюза; оно не подтверждает работоспособность каждого маршрута для доступного пользователю DeepSeek. [OpenAPI МАИ](https://api-ai.mai.ru/openapi.json).

| URL / маршрут | Что проверено |
| --- | --- |
| `GET /docs` | 404 после успешной проверки TLS с официальным CA |
| `GET /openapi.json` | 200; документ прочитан и разобран |
| `GET /health` | 401 без ключа; работоспособность моделей не установлена |
| `GET /models`, `GET /v1/models` | Оба 401 без ключа; список model IDs не получен |
| `POST /chat/completions`, `POST /v1/chat/completions` | Оба документированы; POST не выполнялся |
| `POST /responses`, `POST /v1/responses` | Оба документированы; POST не выполнялся |
| `GET /health/liveliness`, `GET /health/readiness` | Описаны как публичные; фактически не вызывались |

Для нового клиента **обоснованный кандидат base URL — `https://api-ai.mai.ru/v1`**, с последующим путём `chat/completions`. Так получится документированный `/v1/chat/completions`. В OpenAPI нет `servers`; корневые варианты маршрутов тоже присутствуют. Это подтверждение структуры по документу, а не успешного inference. Не добавлять второй `/v1` и не передавать полный `/chat/completions` в поле base URL.

Chat Completions schema содержит `model`, `messages`, `tools`, `tool_choice`, `parallel_tool_calls`, `stream`, `stream_options`, `max_tokens`. Responses schema содержит `input`, `model`, `tools`, `previous_response_id` и streaming. Наличие полей не устанавливает поддержку strict JSON, reasoning, streaming usage или tools конкретной моделью. В security scheme указан `x-litellm-api-key`; примеры того же OpenAPI используют `Authorization: Bearer …`. Какой заголовок разрешён выданному ключу, должен подтвердить координатор; сначала проверять обычный OpenAI Bearer-контракт, не отправлять один секрет во множество заголовков.

Пользовательские обозначения `DeepSeek-V4-Flash` и `deepseek-v4.1-flash` сохранены как названия доступных вариантов. **Exact model ID неизвестен для обоих**: не нормализовать регистр, не заменять точку дефисом, не подставлять ID из прямого API DeepSeek. Нужен точный `id` из авторизованного `/v1/models` либо документа выдачи ключа. Тариф/квота, контекст, лимиты output/reasoning, upstream routing, хранение данных и поддержка tools остаются неизвестными.

CORS МАИ не является условием этой архитектуры: к модели обращается backend. Браузер работает с собственным API приложения; при разных origins ограничение CORS/Origin настраивается именно там.

### TLS и проверки здоровья

Обычные Python urllib и macOS curl не смогли проверить цепочку:
`CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate` и
`curl: (60) SSL certificate problem: unable to get local issuer certificate`.

Read-only TLS-диагностика показала issuer `Russian Trusted Sub CA`. Официальный CA загружен по HTTPS с `gu-st.ru` и добавлен только в SSLContext исследовательского процесса; hostname и цепочка продолжали проверяться. После этого OpenAPI прочитан. Системное хранилище и профили не менялись; `-k` и отключение проверки TLS не использовались. Достаточность одного официального root отдельно подтверждена повторным чтением полного OpenAPI. [Официальный root PEM](https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt), [инструкция разработчика API Точка о тех же сертификатах](https://developers.tochka.com/docs/tochka-api/certificate).

Для Node-контейнера предусмотреть официальный CA в конфигурации доверия выделенного процесса/HTTPS-клиента, с проверкой имени сервера и обновлением сертификатов. Не устанавливать глобальный `NODE_TLS_REJECT_UNAUTHORIZED=0`. Приложение не должно принимать CA или upstream URL из пользовательского ввода. Работу конкретного Node HTTPS-клиента с этим CA ещё нужно проверить.

**Авторизованный `/health` нельзя считать бесплатным ping**: его описание предупреждает о проверке моделей, если не настроены фоновые проверки. Текущий 401 не запускал подтверждённую проверку моделей. Для будущего liveness использовать документированный `/health/liveliness` после проверки его поведения; локальный `/api/healthz` приложения вообще не должен обращаться к LLM.

## Сравнение движков

Оценка сложности — инженерное суждение для этого MVP; live-совместимость с МАИ у всех вариантов `NOT_RUN`.

| Вариант | Сторонний endpoint и tools | Сервер, изоляция, сложность | Лицензия и решение |
| --- | --- | --- | --- |
| **Pi agent-core + ai** | Свой provider/baseUrl, Chat Completions или Responses; готовый цикл custom tools, события, отмена | Встраивается в Node HTTP backend; процесс/контейнер и доступы задаём сами. Нет встроенной системы изоляции OS-доступа. Средняя сложность | MIT. **Рекомендуемый harness** для нескольких предметных tools |
| **Прямой OpenAI-compatible client** | `openai` JS SDK с `baseURL` либо обычный fetch; клиент передаёт tools, но цикл и диспетчер пишет приложение | Node или Worker; удобнее всего для короткого контролируемого запроса. Меньше зависимостей, больше своего кода для состояния/бюджетов | JS SDK Apache-2.0; у fetch нет отдельной зависимости SDK. Хороший минимальный транспорт |
| **PydanticAI** | `OpenAICompatibleProvider` + `OpenAIChatModel`; отдельный Responses-класс. Типизированные tools и валидация | Python backend в контейнере; не Pi. Изоляцию процесса обеспечиваем отдельно. Средняя сложность при уже принятом Python | MIT. Подходит, если backend команды на Python; преимуществ для текущего TS-пути недостаточно |
| **LangGraph** | Модельный адаптер, например ChatOpenAI с custom base URL; граф tools, checkpoints, продолжение | Python или JS backend; больше состояния и настроек. Доступы tools и tenant isolation задаёт приложение | MIT core; условия managed hosting отдельные. Отложить до сложных долгих процессов |
| **Codex SDK** | Custom provider возможен через конфигурацию Codex; требуется совместимый Responses API. Не является универсальным Chat Completions-клиентом | SDK управляет coding runtime; TS-вариант запускает нативный Codex процесс. Sandbox не заменяет запрет shell и предметный allowlist. Высокая сложность для travel | Apache-2.0. **Не выбирать для MVP**; техническую совместимость с МАИ не исключаем |

Источники сравнения: [Pi permissions](https://github.com/earendil-works/pi/blob/35019ae989fc6e45eb18d0c757ef81dd18cb30e3/README.md#permissions--containerization), [OpenAI JS SDK](https://github.com/openai/openai-node), [PydanticAI compatible APIs](https://pydantic.dev/docs/ai/models/compatible-apis/), [LangGraph](https://docs.langchain.com/oss/python/langgraph/overview), [ChatOpenAI custom configuration](https://docs.langchain.com/oss/javascript/integrations/chat/openai). Лицензии: [Pi](https://github.com/earendil-works/pi/blob/35019ae989fc6e45eb18d0c757ef81dd18cb30e3/LICENSE), [OpenAI JS](https://github.com/openai/openai-node/blob/master/LICENSE), [PydanticAI](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE), [LangGraph](https://github.com/langchain-ai/langgraph/blob/main/LICENSE), [Codex](https://github.com/openai/codex/blob/main/LICENSE). Условия МАИ и источников travel-данных этими лицензиями не покрываются.

### Почему Codex SDK не выбран

Сначала выполнены official OpenAI documentation search и fetch. Официальная документация описывает SDK как способ автоматизировать coding-задачи и управлять локальными потоками Codex на сервере. Это отличается и от `openai` SDK, и от OpenAI Agents SDK. [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk).

Custom provider поддерживает base URL, API-ключ из окружения и `wire_api="responses"`. Для допуска нужны incremental SSE с успешным terminal event, продолжение диалога и полный function-call/result/final-answer цикл. Простые health/models либо текстовый ответ этого не подтверждают. [Custom providers](https://learn.chatgpt.com/docs/config-file/config-advanced#custom-model-providers), [Gateway compatibility](https://learn.chatgpt.com/docs/enterprise/gateway-compatibility).

У МАИ Responses **документирован**, поэтому утверждение «Codex с МАИ невозможен» неверно. Неизвестны совместимость выбранного DeepSeek, корректные catalog metadata, reasoning-поля и инструменты. Дополнительно TS SDK создаёт дочерний нативный процесс — его нельзя просто положить в обычный Sites Worker. Это вывод из [исходника exec.ts](https://github.com/openai/codex/blob/main/sdk/typescript/src/exec.ts), а не результат попытки запуска. Для travel-ассистента эти дополнительные слои не дают нужного преимущества.

## Deployable MVP

Предлагаемая схема:

```text
Браузер → HTTPS /api/chat → сессия и лимиты → Pi Agent
                                           ├─ pi-ai → MAI /v1/chat/completions
                                           └─ allowlist предметных read-only tools
```

Backend владеет `MAI_API_KEY`, `MAI_BASE_URL`, `MAI_MODEL_ID`, CA и тарифной конфигурацией. В клиентском bundle, localStorage, URL и ответах этих секретов нет. Нет автоматического fallback на другую модель или внешний платный сервис. Отсутствие ключа/ID оставляет чат в явном недоступном состоянии, без имитации live.

Начальный allowlist: `find_routes` по датированному разрешённому набору маршрутов, `get_travel_policy` по подтверждённым правилам перевозчика, `get_destination_info` и детерминированный `rank_options`. В ответах tool нужны источник, дата актуальности и статус «опубликовано / наблюдалось / предложение». Предлагаемая сеть из исследовательского дашборда не является продаваемым рейсом; без live inventory не обещать цену или наличие кресел.

Каждый tool имеет JSON Schema, проверяемые коды аэропортов/дат, ограниченный размер результата и backend-проверку tenant/session. Название tool сверяется с фиксированным реестром перед исполнением. Нет shell, arbitrary code/eval, browser automation, свободного файлового пути, свободного URL-fetch или пользовательского MCP. Сетевые адреса строит backend из фиксированной конфигурации; redirects к другим hosts запрещены. Инструкции внутри документов/tools считаются данными.

**Бронирование, удержание места, PNR, оплата и изменение билета отсутствуют.** Ассистент может дать проверенную ссылку на официальный канал, но не утверждать, что совершил действие.

Предлагаемые стартовые лимиты — продуктовые настройки для закрытого пилота, не измеренная производительность:

| Ограничение | Начальное значение |
| --- | --- |
| Размер сообщения / HTTP body | 4 000 символов / 16 KiB |
| Частота | 5 сообщений в минуту на сессию; глобально 30/min |
| Одновременные операции | 1 на сессию; 4 на backend; очередь ≤8, ожидание ≤5 секунд |
| LLM вызовы | ≤3 на пользовательский ход; ≤12 на сессию |
| Tools | ≤6 на ход, параллельно ≤2, timeout каждого 5 секунд |
| Время | LLM-call 25 секунд, весь ход 60 секунд; отмена при disconnect |
| Контекст / output | Прикладной input-budget 8 000 tokens и ≤1 200 output tokens на вызов, только после сверки с модельными лимитами |
| Сессия | 30 минут idle TTL; история ограничивается токенами и удаляется после TTL |
| Retry | 0 автоматических повторов принятого/неопределённого LLM POST |

Pi даёт hooks и отмену, однако **лимиты исполняет backend перед каждым модельным запросом и tool**, включая продолжения. Он атомарно резервирует бюджет и слот, затем освобождает их при завершении. Нельзя просто довериться system prompt или mutex одного Worker isolate. Для VPS с одной репликой применим один диспетчер и SQLite-транзакции; при масштабировании нужны общие атомарные счётчики/бюджет.

OpenAI JS SDK по умолчанию повторяет некоторые ошибки дважды и имеет длинный timeout: задать `maxRetries: 0`, явный timeout/AbortSignal. Для Pi отдельно проверить повторы выбранного адаптера и отключить их на реальном транспортном слое; счётчик внешнего цикла не видит скрытый retry SDK. Ошибка после отправки/обрыв SSE означает `outcome=unknown`: автоматический повтор не выполняется, возможный расход остаётся зарезервированным. [Правила клиента](https://github.com/openai/openai-node#retries).

### Стоимость и журнал

Считать каждую попытку LLM, включая промежуточные ответы после tools. Формула при тарифе за миллион токенов:

`C_session = Σ(tokens_uncached × p_uncached + tokens_cached × p_cached + tokens_output × p_output) / 1e6 + отдельные платные tools`.

Категории usage должны быть непересекающимися; reasoning прибавляется отдельно только если провайдер считает его вне output. Валюта, cache accounting и тариф МАИ пока неизвестны. Встроенная оценка Pi по каталогу прямого DeepSeek не является счётом МАИ. Не ставить неизвестный тариф в 0. Нужны `MAX_SESSION_COST`, общий дневной бюджет и согласованные цены либо явно утверждённый владельцем токенный бюджет пилота. При отсутствии usage расход `unknown`; следующий вызов блокируется до сверки или завершения сессии.

В журнале: случайный session/request ID, имя tool, категория результата, длительность, usage, версия тарифа, оценка стоимости и факт отмены. **Без IP, email, почтовых адресов, API-ключей, Authorization, полных URL/query, промптов, ответов и аргументов tools.** Raw ошибки провайдера также не писать. Это распространяется на reverse proxy, tracing и platform access logs. История сессии — отдельные защищённые данные с TTL, не лог. Политику хранения запросов самим МАИ необходимо уточнить; наша настройка логов её не меняет.

## Хостинг

| Размещение | Оценка для MVP |
| --- | --- |
| **Российский VPS + контейнер** | Основной выбор: полноценный Node, контролируемые CA/egress, predictable session state, HTTPS streaming. Стартовая инженерная оценка — 1–2 vCPU, 1–2 GiB RAM, 20 GiB диска; это не benchmark и не тариф. Самостоятельно нужны TLS, обновления, резервная копия конфигурации и наблюдаемость |
| **Yandex Serverless Containers** | Возможен тот же Docker backend; платформа исполняет Docker image. Состояние/лимиты должны переживать несколько instances, заморозку и завершение. Streaming через выбранный ingress нужно проверить отдельно; cold start и runtime-модель сложнее одного VPS |
| **Sites Worker server route** | Подходит для короткого HTTPS вызова через fetch/совместимый JS SDK. Поддержку конкретного Pi bundle нужно проверить сборкой. Нативный Codex runtime внутрь обычного Worker не помещается. Прямой HTTPS к МАИ пока условен из-за CA; наличие server route само по себе не решает доверие TLS |

Для VPS: non-root контейнер, read-only root filesystem, минимальный writable tmpfs, без Docker socket и host-home mounts, ограничение CPU/RAM/PIDs, egress только к МАИ и утверждённым источникам. CA задаётся только этому приложению. Никаких локальных весов DeepSeek или GPU не требуется: inference выполняет внешний API. Контейнер ограничивает среду, а предметный allowlist ограничивает действия модели.

Yandex Cloud подтверждает Docker-image execution; сравнение сервисов различает постоянно работающие контейнеры и обработку вызовов, а описание instance предупреждает о заморозке/завершении. Это основание оценки размещения, а не подтверждение использования Pi Яндексом. [Контейнеры](https://yandex.cloud/en/docs/serverless-containers/concepts/container), [сравнение](https://yandex.cloud/en/docs/serverless-containers/service-comparison).

Для Sites использованы текущий [skill Sites](/Users/a/.codex/plugins/cache/openai-curated-remote/sites/1.1.6/skills/sites/SKILL.md) и [identity/secrets reference](/Users/a/.codex/plugins/cache/openai-curated-remote/sites/1.1.6/skills/sites/references/identity-and-secrets.md). Подтверждённый контракт: ESM `dist/server/index.js`, default export с `fetch(request, env, ctx)`; Worker build без поля `static` в hosting manifest; 128 MB/isolate и HTTP external connections, без raw TCP в Sites. Есть runtime environment variables с `is_secret: true`; после изменения требуется deployment сохранённой версии. Секреты не записываются в hosting.json.

Cloudflare в общем Workers runtime документирует часть Node TLS API, но **это не доказательство**, что Sites допускает custom CA для исходящего fetch или произвольные Cloudflare bindings. Работу МАИ из Sites не проверяли. При несовместимом trust store варианты: публично доверенная цепочка на стороне МАИ либо узкий backend на VPS, который проверяет официальный CA. Тогда Worker передаёт запрос собственному защищённому API, а ключ МАИ остаётся на VPS; открытый proxy недопустим. [Worker fetch](https://developers.cloudflare.com/workers/runtime-apis/fetch/), [TLS API](https://developers.cloudflare.com/workers/runtime-apis/nodejs/tls/). Преимущество serverless уменьшается, если VPS всё равно нужен.

## Что требуется для live

1. **Координатор получает отдельный ограниченный ключ МАИ** и точные IDs двух доступных вариантов. Уточняет Bearer/header, тариф/квоту, context/output, хранение данных и разрешение на публичный ассистент. Никакой поиск чужих ключей не нужен.
2. **Выбирается реальный хост и бюджет.** На нём подтверждаются TLS с hostname validation, исходящий доступ и secret injection. Для Sites дополнительно проверяются CA, bundle и возможность общего атомарного limiter; ни один из этих runtime-тестов сейчас не выполнен.
3. **После отдельной авторизации live-проверки** выполняются минимальные оплачиваемые пробы выбранной модели: текст; один безопасный tool → matching tool result → итог; второй ход; streaming completion/usage; abort/timeout. Для Codex потребовался бы отдельный полный Responses qualification по официальным требованиям. Обрыв после POST не повторять автоматически.
4. **Проверяется приложение:** отклонение неизвестного tool/URL, невозможность shell/booking/payment, изоляция двух сессий, лимиты и бюджет при параллельных запросах, отсутствие секретов и адресов в клиенте/логах. Offline checks и health нельзя выдавать за эти live-результаты.
5. **Согласуются travel-данные:** разрешённые источники, дата расписаний/правил, отсутствие выдачи предложенной сети за действующую продажу. Только затем открывается пилот.

Практический verdict: **Pi core/ai + российский контейнерный backend — выбранный путь реализации; прямой клиент — минимальный транспортный вариант; Codex SDK — технически условно возможен, но избыточен; Sites-only backend требует проверки CA и лимитов.** Exact model IDs, реальные расходы, модельный tool calling, производительность и качество travel-ответов пока `UNKNOWN / NOT_RUN`.
