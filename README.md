# Tally: Flask + SQLite3 on AWS EC2

Live site: http://http://ec2-18-190-156-6.us-east-2.compute.amazonaws.com (replace with your instance's Public IPv4 DNS)

Tally is a small Flask web app deployed on an Ubuntu Server 24.04 LTS EC2 instance behind Apache and mod_wsgi, with a SQLite3 database.

A visitor creates an account with a username and password, enters their first name, last name, email and address, and can attach a `.txt` file in the same form. On submit, the details are stored in the `users` table (the password as a salted hash), the file is saved in `uploads/`, and the browser is redirected to a profile page that shows the saved details, the file's word count and a button to download the file. The login page lets a returning user retrieve the same information with their username and password, and the profile page also accepts a different file.

## Files

```
flaskapp/
├── flaskapp.py       Flask routes, SQLite3 access, upload + word count + download
├── flaskapp.wsgi     entry point that Apache's mod_wsgi loads
├── schema.sql        users table (the app also runs it on startup)
├── templates/        base, register, login and profile pages (Jinja2)
└── static/           style.css and favicon
```

`users.db`, `uploads/` and `secret_key` are created on the server at runtime and are not committed.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install flask
python3 flaskapp.py        # then open http://127.0.0.1:5000
```

## Deploy on Ubuntu 24.04 (EC2)

```bash
sudo apt-get update
sudo apt-get install -y apache2 libapache2-mod-wsgi-py3 python3-pip python3-flask sqlite3
git clone https://github.com/<your-username>/<this-repo>.git ~/flaskapp
sudo ln -sT ~/flaskapp /var/www/html/flaskapp
chmod 755 /home/ubuntu
```

Then add this inside `<VirtualHost *:80>` in `/etc/apache2/sites-enabled/000-default.conf`, right after the `DocumentRoot` line, and restart Apache with `sudo systemctl restart apache2`:

```apache
WSGIDaemonProcess flaskapp user=ubuntu group=ubuntu threads=5 home=/var/www/html/flaskapp
WSGIScriptAlias / /var/www/html/flaskapp/flaskapp.wsgi

<Directory /var/www/html/flaskapp>
    WSGIProcessGroup flaskapp
    WSGIApplicationGroup %{GLOBAL}
    Require all granted
</Directory>
```

Running the daemon as `ubuntu` lets the app write `users.db` and `uploads/` inside the home folder. If something fails, `sudo tail -n 30 /var/log/apache2/error.log` shows why.
