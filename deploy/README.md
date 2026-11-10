# Автодеплой дашборда

Публичный сайт: https://redwings.altair.ad/.

После каждого push в `шаг-1` GitHub Actions
проверяет и публикует **уже собранные и закоммиченные** HTML, изображения,
Excel и паспорт. Сначала пересчитайте модель локально и закоммитьте её выходы.
CI не скачивает исходники исследования и не меняет финансовые результаты.

Workflow можно запустить вручную в Actions → Deploy dashboard → Run workflow,
выбрав ветку `шаг-1`. Из других веток production deployment пропускается.

Проверки: UTF-8, синтаксис встроенного JavaScript через Node, наличие данных
городов, целостность Office-файлов, контрольные суммы и HTTPS. Это проверка
публикации, **не научный или финансовый аудит** модели.

Секреты репозитория: `REDWINGS_DEPLOY_KEY` и `REDWINGS_KNOWN_HOSTS`.
Ключ привязан к пользователю `redwings-deploy` и forced command; нет shell,
sudo и доступа к конфигурации Nginx. Пароль root в GitHub не используется.
Ключ сервера закреплён, проверка SSH host key включена.

Серверный receiver установлен как root-owned
`/usr/local/libexec/redwings-deploy`, исходник — `dashboard_receiver.py`.
После изменения этого исходника администратор отдельно обновляет receiver:
автодеплой не может изменять собственные ограничения.

Каждая версия хранится в `/var/www/redwings/releases/<полный SHA>`.
`current` переключается атомарно; при провале серверной HTTPS-проверки
возвращается предыдущая версия. Ссылка `previous` хранит прошлый успешный
release. Старые версии автоматически не удаляются.

Для ручного отката с административным доступом и установленным receiver:

```sh
sudo -u redwings-deploy env SSH_ORIGINAL_COMMAND='rollback ПОЛНЫЙ_SHA' /usr/local/libexec/redwings-deploy
```

Текущая версия и контрольные суммы доступны в `/release.json`.

Локальная проверка:

```sh
python3 -m unittest discover -s tests -p test_dashboard_deploy.py -v
python3 scripts/package_dashboard.py --revision "$(git rev-parse HEAD)" --output /tmp/dashboard.tar.gz
```
