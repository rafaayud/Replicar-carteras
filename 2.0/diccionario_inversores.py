import pandas as pd
import requests
from bs4 import BeautifulSoup
import time
import warnings
warnings.filterwarnings('ignore')

BASE_URL = "https://www.dataroma.com/m/home.php"
SECOND_URL = "https://www.dataroma.com"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.dataroma.com',
}

def get_superinvestor_updates():

    response = requests.get(BASE_URL, headers=headers)

    time.sleep(1)

    soup = BeautifulSoup(response.text, 'html.parser')

    port_body = soup.find("span", id="port_body")
    if not port_body:
        raise RuntimeError("No encontré el bloque con id='port_body'")

    data = {}
    for li in port_body.find_all("li"):
        a = li.find("a", href=True)
        if not a:
            continue

     
        name = a.get_text(strip=True).split("Updated")[0].strip()
        
         
        href = f"{SECOND_URL}{a['href']}"

        if name:
            data[name] = href

    return data

if __name__ == "__main__":
    data = get_superinvestor_updates()
    print(data)