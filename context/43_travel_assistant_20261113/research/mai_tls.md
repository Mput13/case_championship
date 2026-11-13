# TLS api-ai.mai.ru

Проверка: 13.11.2026, 12:30–12:40 UTC, macOS; T3 environment `d463a92a-a497-4213-aeb8-69f0a1470b87`, parent thread `4e4ac1ba-0f15-4776-b7db-f79fda61fa0b`.

Причина ошибки — отсутствие **Russian Trusted Root CA** в проверенных локальных хранилищах доверия. Сервер передаёт нужный промежуточный сертификат. Корень, полученный с официального ресурса публикации через HTTPS с обычной проверкой TLS, позволяет проверить цепочку и имя `api-ai.mai.ru`: OpenSSL, Python и системный curl прошли проверку; curl получил HTTP 200.

Постоянное доверие и API-клиент не менялись. Проверки выполнены без авторизации и inference-запросов. Корень использовался только в памяти отдельных диагностических процессов. Его применение в рабочем клиенте остаётся решением координатора.

## Сертификаты и SNI

DNS на момент проверки: `194.54.177.229`. С SNI `api-ai.mai.ru` и без SNI сервер передал одни и те же два PEM-сертификата.

| Уровень | Subject / Issuer | Действует, UTC |
| --- | --- | --- |
| Сервер | `CN=mai.ru`, Московский авиационный институт / `Russian Trusted Sub CA` | 25.08.2026 09:14:13 — 25.08.2027 09:14:13 |
| Промежуточный | `Russian Trusted Sub CA`, serial `1005` / `Russian Trusted Root CA` | 15.07.2024 12:50:41 — 19.07.2029 12:50:41 |
| Корень, получен отдельно | `Russian Trusted Root CA`, serial `1000`, self-signed | 01.03.2022 21:04:15 — 27.02.2032 21:04:15 |

SAN сервера: `mai.ru`, `*.mai.ru`. Проверка hostname для `api-ai.mai.ru` прошла. Сервер использует RSA 2048 / SHA-256; промежуточный и корневой CA — RSA 4096. В диагностическом соединении согласованы TLS 1.3 и `TLS_AES_256_GCM_SHA384`.

SHA-256 отпечатки DER:

- Сервер: `48a503e3f0c547e0505d510d1595a21ead7a6e41badd2cd71e79423ec77ff4a7`.
- Промежуточный 2024: `2155785036c900dbb5f1bb2a1569c80c55595bd6bf94867a29bbddbc7d88a3f2`.
- Корень: `d26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31`.

Полные публичные PEM и выводы инструментов сохранены в [mai_tls_public.json](../receipts/mai_tls_public.json).

## Различение причин

**Неполная цепочка промежуточных CA не подтверждается.** Сервер передал leaf и правильный Sub CA 2024. С добавлением только корня цепочка проверяется до depth 2. Серверу не требуется передавать корень, чтобы клиент мог проверить цепочку при наличии доверенного корня.

**Локальное доверие — подтверждённая причина.** Ошибка OpenSSL возникает на depth 1: issuer промежуточного CA не найден. `Russian Trusted` отсутствует в следующих проверенных источниках:

- Python 3.11: certifi bundle, 137 CA.
- `/etc/ssl/cert.pem`: 128 CA.
- Homebrew OpenSSL `/opt/homebrew/etc/openssl@3/cert.pem`: 191 CA.
- `/System/Library/Keychains/SystemRootCertificates.keychain` и `/Library/Keychains/System.keychain`: поиск публичных сертификатов `Russian Trusted` не дал совпадений.

**Истечение и SNI не объясняют сбой.** Все три сертификата действуют на дату проверки; SAN подходит; с SNI и без него цепочка одинакова.

**Признаков подмены сертификата прокси не обнаружено.** Переменные HTTP(S)/ALL_PROXY отсутствуют, системные HTTP/HTTPS/SOCKS/PAC выключены. Все curl-запросы выполнены с `-q`, исключающим чтение curlrc. Сертификат криптографически проверен до отдельно полученного официального корня. Это не доказывает отсутствия любых прозрачных сетевых посредников; менять маршруты или прокси для устранения наблюдаемой ошибки не требуется.

## Сравнение клиентов

| Клиент | Обычное доверие | Отдельный root-only контекст |
| --- | --- | --- |
| Python 3.11.9 / OpenSSL 3.0.13 | `SSLCertVerificationError`, verify_code 20 | TLS 1.3, hostname проверен, `CERT_REQUIRED`, один CA |
| Системный `/usr/bin/curl` 8.7.1 / LibreSSL 3.3.6 | exit 60, verify_result 20, HTTP 000 | exit 0, verify_result 0, HEAD / → HTTP 200 |
| Homebrew OpenSSL 3.6.3 | exit 1, depth 1, verify_code 20 | `Verification: OK`, `Verified peername: *.mai.ru`; offline verify → `stdin: OK` |
| Системный LibreSSL s_client | `Verify return code: 20` | Отдельно не требовался |
| Homebrew curl | Не установлен по проверенным стандартным путям opt/Cellar | Не запускался и не устанавливался |

У системного LibreSSL `s_client` процесс вернулся с exit 0 при `Verify return code: 20`. Сам по себе exit 0 здесь не означает успешную проверку сертификата.

## Источник корня

[Корневой PEM на gu-st.ru](https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt) загружен системным curl с обычным доверием: HTTPS, HTTP 200, exit 0, без отключения verification и без переходов по редиректам. Размер исходного ответа — 2088 байт. Это ресурс публикации сертификатов Госуслуг; соответствующие прямые ссылки приведены также в [официальной документации RuStore для разработчиков](https://www.rustore.ru/help/developers/monetization/payment-callback/Preparing-the-server-for-RuStore%20API).

[Официальный раздел Госуслуг](https://www.gosuslugi.ru/tls) текстовый web-инструмент увидел как страницу ожидания. Локальный обычный TLS для него завершился ошибкой доверия; отдельный контекст с найденным корнем также не подтвердил его цепочку. Эта страница не использовалась как локально верифицированное основание для добавления доверия. HTTPS-загрузка самого PEM с `gu-st.ru` прошла обычную проверку.

Файл `russian_trusted_sub_ca_pem.crt` с того же ресурса содержит старый промежуточный CA 2022, а сервер использует CA 2024. Старый промежуточный не добавлялся: нужный CA уже приходит от сервера. Для исследованного соединения достаточно одного корня.

## Воспроизводимая проверка без установки

Команда использует публичный PEM из receipt, проверяет его отпечаток, создаёт отдельный контекст и выполняет только TLS handshake. Секрет, HTTP-запрос и изменение системного доверия не нужны. Выполнять из корня проекта:

```sh
python3 - <<'PY'
import hashlib
import json
import socket
import ssl
from pathlib import Path

receipt = json.loads(Path(
    "context/43_travel_assistant_20261113/receipts/mai_tls_public.json"
).read_text())
root_pem = receipt["scoped_trust"]["root_pem"]
assert hashlib.sha256(ssl.PEM_cert_to_DER_cert(root_pem)).hexdigest() == (
    "d26d2d0231b7c39f92cc738512ba54103519e4405d68b5bd703e9788ca8ecf31"
)
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.load_verify_locations(cadata=root_pem)
assert ctx.check_hostname and ctx.verify_mode == ssl.CERT_REQUIRED
assert ctx.cert_store_stats()["x509_ca"] == 1

with socket.create_connection(("api-ai.mai.ru", 443), timeout=12) as tcp:
    with ctx.wrap_socket(tcp, server_hostname="api-ai.mai.ru") as tls:
        print("VERIFIED", tls.version(), tls.getpeercert()["subjectAltName"])
PY
```

Для системного curl эквивалентная проверка публичного корня сайта с CA только на время команды, в zsh/bash:

```sh
/usr/bin/curl -q -sS -I --connect-timeout 7 --max-time 14 \
  --cacert <(python3 -c 'import json; print(json.load(open("context/43_travel_assistant_20261113/receipts/mai_tls_public.json"))["scoped_trust"]["root_pem"])') \
  --proto '=https' \
  --write-out '\nhttp_code=%{http_code} ssl_verify_result=%{ssl_verify_result}\n' \
  https://api-ai.mai.ru/
```

Обе команды проверены после записи receipt. Для рабочего Python-клиента координатор может передать такой выделенный `ctx` в `http.client.HTTPSConnection("api-ai.mai.ru", context=ctx)`. Контекст следует использовать только для этого хоста. Он сохраняет проверку цепочки, срока и hostname. Глобальные переменные доверия и общие bundles менять не требуется. Перенос корня в постоянный bundle или рабочий клиент здесь не выполнен.

## Публичная документация после проверки TLS

Все HTTP-запросы ниже выполнены без Authorization и cookies, после успешного verified TLS:

- `HEAD /` и `GET /` → 200. Корень сайта содержит `LiteLLM API - Swagger UI` и ссылку на `/openapi.json`.
- `GET /docs` → 404.
- `GET /openapi.json` → 200; Content-Length 2 052 095. Прочитаны только первые 262 145 байт, поэтому receipt содержит отпечаток прочитанного фрагмента, а не полного файла. В начале указаны OpenAPI 3.1.0 и LiteLLM API 1.106.4. Вся схема не разбиралась.
- Скрипты Swagger не исполнялись; POST, login и вызовы моделей не выполнялись.

TLS-препятствие для отдельного клиента технически устранимо указанным контекстом. Авторизация, доступные модели, квоты и платное исполнение остаются **NOT_TESTED**. CRL/OCSP и политика отзыва отдельно не проверялись.
