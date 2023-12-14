from bs4 import BeautifulSoup
import requests
from selenium import webdriver
import selenium.common.exceptions as exceptions
import time
import pandas as pd
import numpy as np
from config import DRIVER_PATH

# Scraper based on tutorial by Brandon Jacobson: <How to Scrape Dynamically Loaded Websites with Selenium and BeautifulSoup>

def seatfinder():
    """Returns a dataframe containing the number of free, occupied and total seats for all studyzones listed on <https://seatfinder.unisg.ch>"""
    # URL to access
    url = "https://seatfinder.unisg.ch/"

    try:
        # Initialize driver and configuration
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

            # Set up dataframe to fill with scraped data
            seatfinder_df = pd.DataFrame(index=['Library Ground Floor', 'Library Upper Floor', 'Main Building - Learning Zone 2nd floor', 'Main Building - Learning Zone 3rd floor', 'theCo', 'theStage', 'GYM area at Unisport'], columns=['free', 'occupied', 'total', 'occupancy'])
            free_seats = soup.find('table', class_='seatfinder-bar-graph').tbody.tr.td.next_sibling.next_sibling['title'].split(' ')[1]
            
            # Loop through each location and corresponding table element and assign scraped values
            for location, table in zip(seatfinder_df.index, soup.find_all('table', class_='seatfinder-bar-graph')):
                summary = table['summary'].split(' ') # Extract summay tag, containing relevant information and split into list
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
            print('You need to update your ChromeDriver')
            return ''
    
    # Returns dummy dataframe in case scraper doesn't work or website is inaccessible
    except:
        seatfinder_df = pd.DataFrame(index=['Library Ground Floor', 'Library Upper Floor', 'Main Building - Learning Zone 2nd floor', 'Main Building - Learning Zone 3rd floor', 'theCo', 'theStage', 'GYM area at Unisport'], columns=['free', 'occupied', 'total'])
        seatfinder_df['free'] = [50 for i in range(7)]
        seatfinder_df['occupied'] = [20 for i in range(7)]
        seatfinder_df['total'] = [70 for i in range(7)]
        return seatfinder_df