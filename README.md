# clientsim


## Getting Started
* Make sure you have Python3, pip, and virtualenv installed
    ```
    sudo apt install python3 python3-pip python3-virtualenv
    ```
* Pull down the repo and initialize application.
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