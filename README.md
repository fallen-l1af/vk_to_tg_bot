## Описание

Написанный на питоне бот, способный пересылать сообщения, видео, музыку, гифки, изображения и записи сообществ из вк в теелграм.
Является сильно переписанным проектом [Vk-to-telegram-transfer-bot](https://github.com/Whiletruedoend/Vk-to-telegram-transfer-bot)

## Обзор файлов

* main.py - основной скрипт
* config.py - файл-хранилище настроек пользователя, единственный файл, в который нужно вносить свои значения для токенов, нстроек и всего такого
* requirements.txt - список библиотек на питоне, которые должны быть установлены, чтобы запустить код
* last_forwarded_message_id.txt - файл, в котором будет храниться номер последнего пересланного сообщения в переписке из вк в телеграм
* links.txt - файл со ссылками на чужие проекты, из которых брал значимые куски кода 

## Установка

Потребуются: 
* Python 3.8+
* ffmpeg
* Бот в Телеграм (можно создать при помощи [Botfather](https://t.me/BotFather))

1. Скачиваем проект. Ставим необходимые библиотеки из requirements.txt

2. Ставим утиллиту для командной строки ffmpeg (проще всего ставить через командную строку, для Windows это *winget install ffmpeg*)

3. Открываем config.py
   В строке *setCell("project_directory_path", 'XXXXXXX')* прописывем путь до папки с проектом
   В строке *setCell("download_directory_path", 'XXXXXXX')* пишем путь до папки, куда хотим временно загружать файлы для пересылки.
   Это должна быть отдельная папка, в которой не должно лежать ничего больше, так как она будет регулярно полностью очищаться.
   Проще всего создать папку Downloads в иректории с проектом и скопировать путь к ней.
   
   В строке *setCell("vk_name", "XXXXXX")* прописываем, как вас зовут в вк (чтобы боту регулярно об этом вк не спрашивать)
   
   У меня не работала авторизация по логину с паролем, выдавая постоянно неизвестную ошибку api, поэтому я настроил на вход по токену:
   Идём на [сайт](https://vkhost.github.io/), тыкаем настройки, выдаём разрешения (вроде быдолжно хватать ответов, сообщений, доступа в любое время и групп, но это не точно),
   тыкаем получить -> разрешить -> копируем часть ссылки между **access_token=** и **&expires_in**
   Записываем скопированное в setCell("access_token", "XXXXXXXXXX")
   Не светите этим значением ни передкем - оно равнозначно доступу к вашему аккаунту со всеми выданными разрешениями

   
4. Создаём отдельные переписку в вк.
   В десктопной версии вк ссылка на переписку будет выглядеть так: *https://vk.com/im/convo/2000000XXX?entrypoint=list_all*
   Копируем значение 2000000XXX в файл config в строчку *setCell("peer_id", 2000000XXX)*

6. Создаём отдельную переписку в телеграмме.
   Проще всего узнать её ID через официального бота:
   Добавляем в переписку @LeadConverterToolkitBot как участника, отправляем сообщение */get_chat_id*, получаем id. Бота из переписки можно удалять.
   Копируем значение id чата в *setCell("tg_chat_id", -ХХХХХХХХ)*

7. Идём в [Botfather](https://t.me/BotFather), создаём бота.
   Настраиваем бота:
   Group Privacy —> Turn Off
   Allow groups? —> Turn groups On
   Копируем имя бота и выданный токен в *строки setCell("bot_name", "@ХХХХХХХХХ")* и *setCell( "telegram_token", "ХХХХХХХХХ" )*

8. Если при пересылке записей групп хотим, чтобы пересылались не только картинки с видео имузыкой, но и название группы и текст записи, меняем False на True в следующих строчках:
   setCell("vk_group_name", False)
   setCell("vk_wall_caption", False)

Теперь можно запускать main.py, пересылка должна работать.

## Особые моменты:

При пересылке музыки, видео или файлов весом более 50 мб бот не сможет это осуществить, поэтому необходимо авторизоваться в качестве клиента.
Поэтому программа попросит вас ввести логин в Телеграмме и пришедший код.
