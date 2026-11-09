# Диагностика Git push HTTP408

Проверено 2026-11-09T13:37:34.654077+00:00. Изменений Git config, remote, refs, index, known_hosts и процессов не выполнялось. Push диагност не запускал.

## Наблюдения

- Родитель предоставил две завершённые ошибки `RPC failed; HTTP 408 curl22`, `send-pack: unexpected disconnect while reading sideband packet`, `fatal: the remote end hung up unexpectedly`; завершающее `Everything up-to-date` не подтверждает публикацию.
- Три read-only `ls-remote` проверки ветки `research/case5-raw-core-20261109` вернули exit0 и пустой список refs. На момент проб ветка отсутствовала; локальный HEAD `daa2d8f6d2a5d9bac8bf95e8b16f3a278cafec33`.
- Default Git negotiated HTTP/2: GET200, около1.15сек. Per-command HTTP/1.1: GET200, около2.82сек. Ошибка общего DNS/TLS/read-path этими пробами не воспроизведена.
- Git2.50.1 Apple; libcurl8.7.1 поддерживает nghttp2. `http.version`, `http.postBuffer`, low-speed настройки не заданы. Из proxy-related Git config/environment имён ничего не обнаружено. Это не исключает прозрачный маршрут/системный VPN.
- Unauthenticated GitHub API вернул public/private=false. Чтение публичного репозитория не доказывает права записи.
- SSH443 с BatchMode+StrictHostKeyChecking сначала вернул HOST_KEY_VERIFICATION_FAILED. Повторный read-only пробник с HostKeyAlias=github.com использовал уже доверенную запись github.com и **завершился exit0 за8.8сек**. Никакие ключи сервера не добавлялись, проверки не отключались. Существующая SSH-аутентификация и read-доступ работают; write черезSSH пока NOT_RUN.

## Вывод

Подтверждён сбой HTTP write/upload path по предоставленным push-ошибкам. Конкретный источник408 — GitHub, посредник, потокHTTP2, тайм-аут загрузки или другой слой — **UNKNOWN**: для этого нет безопасно сохранённой write-трассы. Подмена вывода утверждением «неисправен HTTP2» была бы преждевременной. Права записи отдельно не проверены.

Заявленные родителем ~46MB всего и max4.64MB/object ниже [жёстких лимитов GitHub](https://docs.github.com/en/repositories/creating-and-managing-repositories/repository-limits):2GB/push и100MB/object. Это исключает простое объяснение документированным превышением размера при корректности этих размеров; не исключает тайм-аут.

## Минимальный безопасный тест

После проверки remote ref и отсутствия своей незавершённой передачи:

```sh
git -c http.version=HTTP/1.1 -c http.postBuffer=104857600 push -u origin research/case5-raw-core-20261109
```

Команда не меняет общую конфигурацию, main или историю. Это контролируемый тест альтернативного HTTP-протокола, не подтверждённое исправление. В [документации Git](https://git-scm.com/docs/git-config) http.version выбирает протокол; postBuffer влияет прежде всего на chunked encoding, а не является общим лечением push. 100MB уже использовалось родителем без эффекта; дополнительная проверяемая переменная здесьHTTP1.1.

После команды критерий успеха — точное совпадение серверного ref с localSHA через `git ls-remote`, не строка Everything up-to-date. Если1.1 снова вернёт408, дальнейшие одинаковые retries малоинформативны. Рекомендуется сохранить только протокол/статус/длительность/число отправленных байтов из трассы, никогда Authorization/Set-Cookie/Cookie или сырую curl verbose трассу. SSH443 с HostKeyAlias=github.com успешно проверен для чтения; возможен следующий write-тест без изменения remote/config:

```sh
git -c 'core.sshCommand=ssh -oBatchMode=yes -oStrictHostKeyChecking=yes -oHostKeyAlias=github.com' push ssh://git@ssh.github.com:443/Mput13/case_championship.git HEAD:refs/heads/research/case5-raw-core-20261109
```

Это использует уже доверенный ключ github.com, не отключает его проверку и не добавляет known_hosts. Write-доступ этим диагностом не проверялся. После успешного SSH push и серверной сверкиSHA обычный `git push -u origin research/case5-raw-core-20261109` потребует лишь настройки tracking/проверки refs без большого нового pack. Не использовать multi-valued `-c remote.origin.url` как гарантированное перекрытие URL; явный SSH URL исключает такую неоднозначность.

Файлы: local_readonly.json, http_read_probes.json, repo_public_visibility.json, ssh443_read_probe.json, ssh443_alias_read_probe.json. В них только имена конфигурационных опций, статусы и числовые показатели, без значений auth/proxy/keys.
