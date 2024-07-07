from requests import post
import time

while True:
    req1 = post('https://sso.mycar.kz/auth/login/', data={
        "phone_number": "+77002760224"})

    print(req1.json())
    time.sleep(360)
