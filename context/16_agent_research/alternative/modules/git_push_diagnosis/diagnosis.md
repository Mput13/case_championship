# Диагностика Git HTTP 408

Проверка начата 2026-11-09 13:14:36 UTC. Ветка `research/case5-raw-alternative-20261109`, проверенный HEAD `0fd05faaee208d59cd1b6f49683a9e7c7bb308af`, Git 2.50.1 (Apple Git-155). Root сообщил push с exit 1:

```text
error: RPC failed; HTTP 408 curl 22 The requested URL returned error: 408
send-pack: unexpected disconnect while reading sideband packet
fatal: the remote end hung up unexpectedly
Everything up-to-date
```

Само сочетание exit 1 и `Everything up-to-date` не подтверждает публикацию. Перед повтором root должен прочитать remote SHA и сравнить его с intended SHA. Диагност этого не делал и push/fetch не запускал.

Локально воспроизведён pack через `git pack-objects --stdout --revs` для закреплённого HEAD за исключением baseline `9dbaee7ee53ee10ecb6db64d1cf634a7c0bceba7`. Вывод только подсчитан и хеширован в памяти; pack на диск и в object store не записан. Получено 13 860 564 байта. Объекты: 571, из них 517 blobs общим несжатым размером 45 618 930 байт. Крупнейший blob — `modules/telegram_correction/normalized/comparison_original_corrected.csv`, 6 267 983 байта. Это расчёт относительно локального baseline, фактический server-negotiated upload может отличаться. Явных `http.*` overrides в Git config нет; обнаружены только названия `credential.helper` и `remote.origin.url/fetch`. Значения секретов/прокси/credentials не выводились.

Предположение: ошибка возникла на HTTP-передаче между клиентом, посредником и remote. Какой компонент вернул 408, неизвестно. Она не доказывает ошибку токена, отказ GitHub по размеру файла или повреждение данных. Установить точную причину без серверной/прокси-телеметрии не удалось.

После проверки remote SHA допустим один ограниченный транспортный тест без постоянной смены конфигурации:

```sh
git -c http.version=HTTP/1.1 -c http.postBuffer=33554432 push -u origin research/case5-raw-alternative-20261109
```

32 MiB превышают измеренный pack. По [официальной документации Git v2.50.1](https://raw.githubusercontent.com/git/git/v2.50.1/Documentation/config/http.adoc) default postBuffer равен 1 MiB; увеличение помогает только отключить chunked encoding, когда этот режим несовместим с сервером/прокси. Это не общее исправление push и не доказательство причины 408. При повторном сбое нужны снова remote SHA и точная ошибка; force push, рестарт T3/агентов/профилей и очистка object store не требуются.

`git count-objects -v` отдельно сообщил zero-size garbage warning для общего worktree `refs` directory. Он сохранён как наблюдение, не признан причиной HTTP 408. Ничего не удалялось. Общий object store не является объёмом этого upload.

Официальный git-scm docs URL дал HTTP 403; первичный versioned source документации на GitHub получен успешно. Сети/credentials не менялись, trace с заголовками не включался, параллельные процессы не останавливались. Записаны только файлы этой диагностической подпапки. Push outcome и remote SHA остаются `UNKNOWN` в рамках диагностики; их проверяет root.
