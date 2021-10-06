# Kinopoisk.bundle

> Документация в разработке. Последнее обновление 21.05.2020 г.

Данный плагин является агентом для [Plex Media Server](https://plex.tv) и грузит информацию о фильмах с сайта [Кинопоиск](https://www.kinopoisk.ru).

## Установка Plex Media Server
[Скачать Plex Media Server](https://www.plex.tv/media-server-downloads/) для вашей операционной системы. Далее Plex Media Server - PMS.

## Пути и установка плагина
Скачайте ZIP-архив с сайта [github.com](https://github.com/Jenstel/Kinopoisk.bundle)

![Скриншот](https://user-images.githubusercontent.com/562733/135882979-d7c38ba7-a643-4da5-94f7-aec144cc7011.png)
### Windows
Распакуйте скачанный архив в папку `%LOCALAPPDATA%\Plex Media Server\Plug-ins`. Альтернативно можно щелкнуть правой кнопкой мыши на иконке PMS в системном трее (рядом с часами) и выбрать пункт "Открыть папку плагинов" ("Open plugins folder").

### MacOS
Распакуйте скачанный архив в папку `~/Library/Application Support/Plex Media Server/Plug-ins`

### Debian / Ubuntu
Проверяем наличие необходимых библиотек и/или устанавливаем все необходимое
```
sudo apt update && sudo apt install -y git
cd /var/lib/plexmediaserver/Library/Application\ Support/Plex\ Media\ Server/Plug-ins/
sudo git clone https://github.com/Jenstel/Kinopoisk.bundle.git
sudo chown -R plex:plex Kinopoisk.bundle/
sudo systemctl restart plexmediaserver
```
### FreeBSD
Распакуйте скачанный архив в папку `/usr/local/plexdata/Plex Media Server/`

### FreeNAS
Распакуйте скачанный архив в папку `${JAIL_ROOT}/var/db/plexdata/Plex Media Server/`

### QNAP
Конкретное расположение может меняться. Для проверки введите в консоли <br />
`getcfg -f /etc/config/qpkg.conf PlexMediaServer Install_path`

Копируем выданный путь, добавляя в конце `/Library/Plex Media Server`, например, `/share/CACHEDEV1_DATA/.qpkg/PlexMediaServer/Library/Plex media Server`

### Synology
Распакуйте скачанный архив в папку `/volume1/Plex/Library/Application Support/Plex Media Server/Plug-ins`

### Другие операционные системы

Пути расположения папки с плагинами других систем ищите на официальном сайте [Plex.TV](https://support.plex.tv/articles/202915258-where-is-the-plex-media-server-data-directory-located/)

## Возможности
1. Загрузка рейтингов для фильмов
+ Kinopoisk
+ Rotten Tomatoes
+ IMDb
+ The Movies Database
2. Источники рецензий на фильмы
+ Kinopoisk
+ Rotten Tomatoes
3. Загрузка трейлеров фильмов
4. Загрузка дополнительных материалов (сцены, интервью)
5. Загрузка английских имен актеров
6. Приоритет локализованных обложек фильмов
7. Поддержка прокси-серверов (http, sock5)

![Скриншот](https://b.radikal.ru/b41/1901/88/404cf326bbff.png)

## [Список изменений](CHANGELOG.md)

## Получение API-ключа
![image](https://user-images.githubusercontent.com/562733/136152946-6f2b40a4-9465-400a-960e-1529b97244bc.png)

Необходимо перейти на сайт [API-unofficial](https://kinopoiskapiunofficial.tech/) и нажать вверху "Sign up", после регистрации на вашу почту придет письмо с кодом активации аккаунта. Далее заходим в личный кабинет и выбираем вкладку "Profile", в которой можно будет увидеть ваш персональный API-ключ, который необходимо скопировать и вставить в настройки плагина.

## Об авторе
Автор: Artem Mirotin aka @amirotin<br />
Автор доработок: Aleksey Ganuta aka [@ziemenz](https://t.me/ziemenz) и [@Jenstel](https://t.me/Jenstel)<br />
Документация: Vladimir Sharapov aka [@EvelRus](mailto:evelrus@mail.ru)

Постоянная ссылка на обновленный плагин - [https://github.com/Jenstel/Kinopoisk.bundle](https://github.com/Jenstel/Kinopoisk.bundle)
