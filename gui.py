import PySimpleGUI as sg
import sys
import uuid
import json
import requests
import time
import base64
import os
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkd2 import PBKDF2HMAC
import pyperclipf

sg.theme('DarkBlack')
# BASE_URL = 'http://167.99.191.206:80/'
BASE_URL = 'http://127.0.0.1:5000/'

layout = [[sg.Text('Log into Cloud Copy', font=('Helvetica', 18))],
          [sg.Text('Email', font=('Arial', 11)), sg.InputText(font=('Arial', 11), key='email')],
          [sg.Text('Password', font=('Arial', 11)),
           sg.InputText(password_char='*', font=('Arial', 11), key='password')],
          [sg.Text('Incorrect email or password', key='log_in_error', size=(30, 1), text_color='#ff425c',
                   font=('Arial', 11), visible=False)],
          [sg.Button('Log in or Sign up', key='log_in', font=('Arial', 11)),
           sg.Text('forgot password', font=('Arial', 11), enable_events=True, key='forgot_password')]]

logged_in = False 


def start_service(key, token):
    current_text = pyperclip.paste()
    last_update = datetime.now()
    while True:
        try:
            new_copy = pyperclip.paste()
            if current_text != new_copy:
                requests.post(BASE_URL + 'share-copy/', {'token': token, 'contents': encrypt(key, new_copy)})
            else:
                resp = requests.get(BASE_URL + f'newest-copy/?token={token}').text
                if resp != 'false':
                    resp = json.loads(resp)
                    new_copy, timestamp = decrypt(key, resp['current_copy']), resp['timestmap']
                    timestamp = datetime.strptime(timestamp, '%Y-%m-%d %I:%M:%S.%f')
                    if new_copy != current_text and last_update < timestamp:
                        last_update = timestamp
                        current_text = new_copy
                        pyperclip.copy(new_copy)
            time.sleep(2)
        except requests.RequestException: time.sleep(60)  # wait 60 seconds before trying again
    # For every copied data, send the token with the data
    # only if no sockets ^
    # Make sure to handle no wifi
    # Socket connection might be required with the server
    # No copied notifications / sent notifications


def encrypt(key, message: bytes) -> bytes:
    f = Fernet(key)
    return f.encrypt(message)


def decrypt(key, encrypted: bytes) -> bytes:
    f = Fernet(key)
    return f.decrypt(encrypted)


def create_key(provided_password: str) -> bytes:
    password = provided_password.encode()  # Convert to type bytes
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'',
        iterations=100000,
        backend=default_backend())
    key = base64.urlsafe_b64encode(kdf.derive(password))  # Can only use kdf once
    with open('.key', 'wb') as f: f.write(key)
    return key


# using the request module try to authenitcate token
if os.path.exists('.token'):
    with open('.token') as f:
        email, token = f.read().split('\n')
        url = BASE_URL + 'authentic/'
        x = requests.post(url, {'email': email, 'token': token}).text
    if x != 'invalid token':
        logged_in = True
        if x != token:
            with open('.token', 'w') as f:
                f.write(email + '\n' + token)


window = sg.Window('Cloud Copy - Universal Clipboard', layout, return_keyboard_events=True)
while not logged_in:
    event, values = window.read()
    if event in (None, 'Escape:27'):  # if user closes window or clicks cancel
        sys.exit()
    if event == 'forgot_password':
        print('forgot password')
    if event == 't': pass
    if event in ('\r', 'special 16777220', 'special 16777221', 'log_in'):
        email, password = values['email'], values['password']
        if not email:
            window['email'].set_focus()
        elif not password:
            window['password'].set_focus()
        else:
            window['log_in_error'].Update(visible=False)
            window['forgot_password'].Update(value='authenticating...')
            # mac = ''.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) for ele in range(0, 8 * 6, 8)][::-1])
            # NOTE: no ':' as it is a waste of data
            resp = requests.post(BASE_URL + 'authenticate/', {'email': email, 'password': password}).text
            if resp == 'false':
                window['log_in_error'].Update(visible=True)
                window['forgot_password'].Update(value='forgot password')
            else:
                window['log_in_error'].Update(visible=False)
                window['forgot_password'].Update(value='Log in successful')
                token = resp
                with open('.token', 'w') as f: f.write(email + '\n' + token)
                create_key(password)
                logged_in = True
                time.sleep(0.5)
            # also send PC Name?
    # print(event)
window.close()
with open('.key', 'rb') as f:
    start_service(f.read(), token)

