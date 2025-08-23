import os
import time
import requests

from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from dotenv import load_dotenv

load_dotenv()


class AutoZakup:    
    def __init__(self):
        self.driver = webdriver.Chrome()


    def main(self):
        self.driver.get("https://v3bl.goszakup.gov.kz/ru/user/login")
        time.sleep(3)

        auth_button = self.driver.find_element(By.CSS_SELECTOR, "input#selectP12File")
        auth_button.click()
        time.sleep(2)

        sign_key = ""
        for request in self.driver.requests:
            if "goszakup.gov.kz" in request.url:
                if request.url == "https://v3bl.goszakup.gov.kz/ru/user/sendkey/kz":
                    sign_key = request.response.body.decode("utf-8")
                    print(f"Получен sign_key: {sign_key}")

        if sign_key is '':
            raise Exception("Sign key не получен!")
        xml_raw = self.get_xml_sing_by_key(sign_key)        
        xml_clean = xml_raw.replace('\\"', '"').replace("\\n", "\n").replace('&#13;', "")
        script = f"""
            var xhr = new XMLHttpRequest();
            xhr.open('POST', 'https://v3bl.goszakup.gov.kz/user/sendsign/kz', false);
            xhr.setRequestHeader('Content-Type', 'application/x-www-form-urlencoded');
            
            var data = 'sign=' + encodeURIComponent(`{xml_clean}`);
            xhr.send(data);
            
            return xhr.status + '|' + xhr.responseText;
            """
            
        result = self.driver.execute_script(script)
        status_code, response_text = result.split('|', 1)

        print(f"Status: {status_code}")
        print(f"Response: {response_text}")
        if response_text == "<script>document.location.href = 'https://v3bl.goszakup.gov.kz/ru/user/registration'</script>":
            self.driver.refresh()
        
        input("Нажмите Enter чтобы завершить программу.")
        
        
    def get_xml_sing_by_key(self, key: str):
        base64_key = os.environ.get("BASE64_KEY")
        password = os.environ.get("KEY_PASSWORD")
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "xml": f"<root><key>{key}</key></root>",
            "signers": [
                {
                "key": base64_key,
                "password": password,
                "keyAlias": None
                }
            ],
            "clearSignatures": False,
            "trimXml": False
        }
        
        response = requests.post("http://localhost:14579/xml/sign", headers=headers, json=payload)
        if response.status_code == 200:
            resp_json = response.json()
            return resp_json['xml']
        else:
            raise Exception(f"Ошибка при отправке запроса на http://localhost:14579/xml/sign. Ответ: {response.text}")
    
    def health_check(self):
        health_resp = requests.get("http://localhost:14579/actuator/health")
        
        print("Ответ health check:", health_resp.json())
            
if __name__ == "__main__":
    soft = AutoZakup()
    soft.main()
    # soft.health_check()
    