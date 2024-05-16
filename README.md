# praktikum_new_diplom

Продуктовый помощник.
http://foodgramchik.zapto.org/

 

## Как запустить проект: 

 

### Клонировать репозиторий: 

 

git clone git@github.com:Maria-Lts/foodgram-project-react.git

 

### Cоздать и активировать виртуальное окружение: 

 

python3 -m venv env 

source env/bin/activate 

 

### Установить зависимости из файла requirements.txt: 

 

python3 -m pip install --upgrade pip 

pip install -r requirements.txt 


### Создать файл .env


POSTGRES_DB=foodgram
POSTGRES_USER=django_user
POSTGRES_PASSWORD=mysecretpassword
DB_NAME=foodgram
DB_HOST=db
DB_PORT=5432


### Скачать образы для контейнеров


docker compose -f docker-compose.production.yml up
 

### Выполнить миграции, собрать статику, загрузить ингредиенты: 


sudo docker compose -f docker-compose.production.yml exec backend sh -c 'cd foodgram; DJANGO_SETTINGS_MODULE=foodgram.settings PYTHONPATH=.. django-admin migrate'
sudo docker compose -f docker-compose.production.yml exec backend sh -c 'cd foodgram; DJANGO_SETTINGS_MODULE=foodgram.settings PYTHONPATH=.. django-admin collectstatic'
sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /static/static/
sudo docker compose -f docker-compose.production.yml exec backend sh -c 'cd foodgram; DJANGO_SETTINGS_MODULE=foodgram.settings PYTHONPATH=.. django-admin load_csv'
 

### Данные для админа: 

email: adminchik@mail.ru
password: ibyibkkf15
