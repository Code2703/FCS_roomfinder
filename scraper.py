from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import selenium.common.exceptions as exceptions
import time
import pandas as pd
import numpy as np
from config import DRIVER_PATH

# Open HTML file

def seatfinder():
    url = "https://seatfinder.unisg.ch/"

    try:
        global driver
        options = webdriver.ChromeOptions()
        options.add_argument('start-maximized')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("detach", True)
        options.add_experimental_option("useAutomationExtension", False)

        try:
            driver = webdriver.Chrome(chrome_options=options, executable_path=DRIVER_PATH)
            driver.get(url)
            time.sleep(5)
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')

            seatfinder_df = pd.DataFrame(index=['Library Ground Floor', 'Library Upper Floor', 'Main Building - Learning Zone 2nd floor', 'Main Building - Learning Zone 3rd floor', 'theCo', 'theStage', 'GYM area at Unisport'], columns=['free', 'occupied', 'total', 'occupancy'])
            free_seats = soup.find('table', class_='seatfinder-bar-graph').tbody.tr.td.next_sibling.next_sibling['title'].split(' ')[1]
            
            for location, table in zip(seatfinder_df.index, soup.find_all('table', class_='seatfinder-bar-graph')):
                summary = table['summary'].split(' ')
                free = summary[1]
                try:
                    free = int(free)
                except: 
                    free = '-'
                seatfinder_df.loc[location, 'free'] = free

                try:
                    occupied = int(summary[6])
                except:
                    occupied = '-'
                seatfinder_df.loc[location, 'occupied'] = occupied

                if type(free) == int and type(occupied) == int:
                    total = free + occupied
                else:
                    total = '-'
                seatfinder_df.loc[location, 'total'] = total
                seatfinder_df.loc[location, 'occupancy'] = np.nan

            driver.close()
            return seatfinder_df
    
        except exceptions.WebDriverException:
            return ''
            print('You need to update your ChromeDriver')
    except:
        seatfinder_df = pd.DataFrame(index=['Library Ground Floor', 'Library Upper Floor', 'Main Building - Learning Zone 2nd floor', 'Main Building - Learning Zone 3rd floor', 'theCo', 'theStage', 'GYM area at Unisport'], columns=['free', 'occupied', 'total'])
        seatfinder_df['free'] = [50 for i in range(7)]
        seatfinder_df['occupied'] = [20 for i in range(7)]
        seatfinder_df['total'] = [70 for i in range(7)]
        return seatfinder_df