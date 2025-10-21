#%%
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import time
import warnings
from diccionario_inversores import get_superinvestor_updates
warnings.filterwarnings('ignore')


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.dataroma.com',
}

class Wallet:
    def __init__(self, name_investor, link_to_investor, quantity):

        self.name_investor = name_investor
        self.link_to_investor = link_to_investor
        self.quantity = quantity

        self.date = None
        self.df_dataroma = None

        self.df_wallet = None
 
    
    def create_wallet(self):

        all_pages_data = []
        page = 1    

        while True:
            # Construct URL with page parameter
            if page == 1:
                page_url = self.link_to_investor
            else:
                # Add page parameter
                if '?' in self.link_to_investor:
                    page_url = f"{self.link_to_investor}&L={page}"
                else:
                    page_url = f"{self.link_to_investor}?L={page}"

            try:
                # Get the page
                html = requests.get(page_url, headers=headers).text


                if page == 1:
                    soup = BeautifulSoup(html, "lxml")
                    p2 = soup.find("p", id="p2")
                    if p2:
                        # buscar el span que sigue a la etiqueta "Portfolio date:"
                        label = p2.find(string=lambda t: t and "Portfolio date" in t)
                        if label:
                            span = label.find_next("span")
                            if span:
                                date_str = span.get_text(strip=True)      # ej. "30 Jun 2025"
                                self.date = pd.to_datetime(date_str, dayfirst=True)
                # Let pandas read the table(s)
                tables = pd.read_html(html)

                if tables and len(tables) > 0:
                    df = tables[0]

                    # Check if we got data
                    if len(df) == 0:
                        break

                    # Add the investor column
                    df['Investor'] = self.name_investor
                    df['Page'] = page  # Optional: track which page the data came from

                    all_pages_data.append(df)

                    print(f"    Page {page}: {len(df)} holdings")

                    # If we got exactly 200 rows, there might be another page
                    if len(df) == 200:
                        page += 1
                        time.sleep(0.5)  # Small delay between pages
                    else:
                        # Less than 200 rows means this is the last page
                        break
                else:
                    break

            except Exception as e:
                if page == 1:
                    print(f"    ✗ Error: {str(e)[:50]}")
                break

            # Safety check to avoid infinite loops
            if page > 10:  # Assuming no investor has more than 10 pages
                print(f"    Warning: Stopped at page {page} (safety limit)")
                break

        # Combine all pages for this investor
        if all_pages_data:

            self.df_dataroma = pd.concat(all_pages_data, ignore_index=True)
            self.df_dataroma["Current Price"] = pd.to_numeric(self.df_dataroma["Current Price"].astype(str).str.replace('$', '', regex=False), errors='coerce')
        
        else:
            None

    def update_wallet(self):

        if self.df_dataroma is not None:
            html = requests.get(self.link_to_investor, headers=headers).text

            soup = BeautifulSoup(html, "lxml")
            p2 = soup.find("p", id="p2")

            if p2:
                # buscar el span que sigue a la etiqueta "Portfolio date:"
                label = p2.find(string=lambda t: t and "Portfolio date" in t)
                if label:
                    span = label.find_next("span")

                    if span:
                        date_str = span.get_text(strip=True)      # ej. "30 Jun 2025"
                        new_date = pd.to_datetime(date_str, dayfirst=True)

            if new_date > self.date:

                all_pages_data = []
                page = 1    

                while True:
                    # Construct URL with page parameter
                    
                    try:
                        # Get the page
                    
                        # Let pandas read the table(s)
                        tables = pd.read_html(html)

                        if tables and len(tables) > 0:
                            df = tables[0]

                            # Check if we got data
                            if len(df) == 0:
                                break

                            # Add the investor column
                            df['Investor'] = self.name_investor
                            df['Page'] = page  # Optional: track which page the data came from

                            all_pages_data.append(df)

                            print(f"    Page {page}: {len(df)} holdings")

                            # If we got exactly 200 rows, there might be another page
                            if len(df) == 200:
                                page += 1
                                time.sleep(0.5)  # Small delay between pages
                            else:
                                # Less than 200 rows means this is the last page
                                break
                        else:
                            break

                    except Exception as e:
                        if page == 1:
                            print(f"    ✗ Error: {str(e)[:50]}")
                        break

                    # Safety check to avoid infinite loops
                    if page > 10:  # Assuming no investor has more than 10 pages
                        print(f"    Warning: Stopped at page {page} (safety limit)")
                        break

                # Combine all pages for this investor
                if all_pages_data:

                    new_table = pd.concat(all_pages_data, ignore_index=True)
                    new_table["Current Price"] = pd.to_numeric(new_table["Current Price"].astype(str).str.replace('$', '', regex=False), errors='coerce')
                
                else:
                    None
                
                new_table_modified = new_table[["Stock", "% of Portfolio", "Current Price"]]
                new_table_modified["Shares"] = ((new_table_modified["% of Portfolio"] / 100) * self.quantity) / new_table_modified["Current Price"]
                new_table_modified["Value"] = new_table_modified["Shares"] * new_table_modified["Current Price"]

                new_table_modified["Shares"] = new_table_modified["Shares"] - self.df_wallet["Shares"]
                diff = new_table_modified["Shares"].fillna(0)

                # construir la orden
                self.new_table_modified["Update"] = diff.apply(lambda x: f"BUY {abs(x):.4f}" if x > 0 else (f"SELL {abs(x):.4f}" if x < 0 else "Nothing"))

                self.df_dataroma = new_table
                self.show_wallet()
        else:
            raise ValueError("No se ha creado la cartera")


        

    def add_money(self, money):
        return

    def remove_money(self, money):
        return


    def show_wallet(self):

        if self.df_wallet is not None and not self.df_wallet.empty:
            return self.df_wallet[["Stock", "Shares", "Value"]]
        else:
            self.df_wallet = self.df_dataroma[["Stock", "% of Portfolio", "Current Price"]].copy()
            self.df_wallet["Shares"] = ((self.df_wallet["% of Portfolio"] / 100) * self.quantity) / self.df_wallet["Current Price"]
            self.df_wallet["Value"] = self.df_wallet["Shares"] * self.df_wallet["Current Price"]
        
        return self.df_wallet[["Stock", "Shares", "Value"]]



#%%
if __name__ == "__main__":
    w = Wallet('Mason Hawkins - Longleaf Partners', 'https://www.dataroma.com/m/holdings.php?m=LLPFX', 12000)
    w.create_wallet()
    
# %%
