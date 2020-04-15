# clientsim


## Getting Started
```
git clone https://github.com/joshand/clientsim.git
cd clientsim/
virtualenv venv --python=python3
source venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
Username (leave blank to use 'username'): admin
Email address: email@domain.com
Password: 
Password (again): 
Superuser created successfully.

python manage.py drf_create_token admin
Generated token 1234567890abcdefghijklmnopqrstuvwxyz1234 for user admin

python manage.py runserver 8000
```