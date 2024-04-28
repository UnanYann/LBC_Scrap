#!/usr/bin/env python
# coding: utf-8

# In[8]:


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from bs4 import BeautifulSoup
import requests
import pandas as pd


# In[3]:


# Creat a function that scrap projects url from a page
def scrap_urls(driver):
    urls = []
    # Make a soup
    html_content = driver.page_source
    soup = BeautifulSoup(html_content, 'html.parser')
    # Find urls
    project_links = soup.find_all('a', href=lambda href: href and href.startswith('/projets/'))
    
    #Concatenate main url with scrapped url
    for link in project_links:
        urls.append("https://label-bas-carbone.ecologie.gouv.fr/" + link['href'])
    return urls
    
# Create a function that scrap each project urls from every page
def turn_pages(driver):
    all_urls = []
    previous_element = None
    while True:
        # Scrap urls from current page
        current_urls = scrap_urls(driver)
        # Add urls to a the definitive list
        all_urls.extend(current_urls)
        # Bot to turn page
        try:
            # Find the element to turn page and click on it
            next_page = driver.find_element(By.CSS_SELECTOR, ".fr-pagination__link.fr-pagination__link--next.fr-pagination__link--lg-label")
            next_page.click()
        # Behavior in NoSuchElement case
        except NoSuchElementException:
            break
        #Determinate the last page to stop the script
        if next_page and previous_element and next_page.id == previous_element.id:
            break
        #Attributing previous element for the next run 
        previous_element = next_page
    return all_urls


# In[4]:


# Run the function
driver = webdriver.Firefox()
driver.get("https://label-bas-carbone.ecologie.gouv.fr/liste-projets-labellises")
urls = turn_pages(driver)
driver.quit()


# In[91]:


#Create a function that scrap data from projects
def scrap_projects(urls):
    #First, create a dictionnary to gather datas
    all_datas = []
    #Connect to each url
    for url in urls:
        r = requests.get(url)
        r_html_content = r.text
        #Make the soup
        soup = BeautifulSoup(r_html_content, 'html.parser')

        # Extract datas
        datas = {"Nom du projet": [], "Le Responsable du projet": [], "Mail responsable projet": [], "Financeurs": []}

        # Scrap some elements
        # Scrap of the title project
        name_element_menthe = soup.find(class_="heading-title display-inline-flex fr-py-1v fr-px-2w fr-background-contrast--green-menthe")
        name_element_archipel = soup.find(class_="heading-title display-inline-flex fr-py-1v fr-px-2w fr-background-contrast--green-archipel")

        if name_element_menthe:
            name = name_element_menthe.get_text().strip()
        elif name_element_archipel:
            name = name_element_archipel.get_text().strip()
        else:
            name = "Nom du projet non trouvé"
        #Scrap of the name and mail of the responsible of the project
        responsable_element = soup.find(class_="fr-callout__title fr-mb-1w")
        responsable_projet = responsable_element.get_text().strip()

        mail_responsable_element = soup.find('a', href=lambda href: href and href.startswith('mailto:'))
        mail_responsable = mail_responsable_element['href'].split(':')[1]

        # add them to the dictionnary
        datas["Nom du projet"] = name
        datas["Le Responsable du projet"] = responsable_projet
        datas["Mail responsable projet"] = mail_responsable

        # Scrap infos on project element
        list_elements = soup.find_all('li')

        for element in list_elements:
            # Extract the elements
            titre_element = element.find('p', class_='item-info-title')
            if titre_element:
                titre = titre_element.get_text().strip()
            else:
                titre = "Titre non trouvé"

            # Extract elements descritpion
            description_element = element.find('p', class_='item-info-description')
            if description_element:
                description = description_element.get_text().strip()
            else:
                description = "Description non trouvée"
            # Add all to th dictionnary
            datas[titre] = description

        # Scrap of info on tC02
        keyfigure_projects = soup.find_all('div', class_='keyfigure-project')
        for project in keyfigure_projects:
            #Extract description and title
            description = project.find('h3', class_='keyfigure-project-title').get_text().strip()
            title = project.find('p', class_='keyfigure-project-description').get_text().strip()
            # Add all to dictionnary
            datas[title] = description

        # Scrap info on project financeurs
        financeur_elements = soup.find_all('div', class_='paragraph')

        for financeur_element in financeur_elements:
            financeur_name = financeur_element.find('h3', class_='fr-my-2w').get_text().strip()
            financeur_type_element = financeur_element.find('p', string='Type')
            financeur_type = financeur_type_element.find_next('p').get_text().strip()
            financeur_percent_element = financeur_element.find('p', string='% du projet financé')
            financeur_percent = financeur_percent_element.find_next('p').get_text().strip()
            financeur_tCO2_element = financeur_element.find('p', string='Nombre de tCO2 reconnues sur le projet')
            financeur_tCO2 = financeur_tCO2_element.find_next('p').get_text().strip()

            # Add them to the dictionnary
            datas["Financeurs"].append({
                "Nom": financeur_name,
                "Type": financeur_type,
                "% du projet financé": financeur_percent,
                "Nombre de tCO2 reconnues sur le projet": financeur_tCO2
            })
        #Append the datas to all datas
        all_datas.append(datas)

    return all_datas


# In[92]:


# Use the function 
LBC_datas = scrap_projects(urls)


# In[90]:


print(LBC_datas)


# In[93]:


#Function to check keys
def check_keys(d):
    return 'Titre non trouvé' in d and 'Description non trouvée' in d
#Function to fill missing values
def fill_missing_values(d):
    if 'Titre non trouvé' not in d:
        d['Titre non trouvé'] = ''
    if 'Description non trouvée' not in d:
        d['Description non trouvée'] = ''
    return d
#Use functions
data_list_checked = [fill_missing_values(d) for d in LBC_datas if check_keys(d)]


# In[94]:


#Create the dataframe and divide financeurs
df = pd.DataFrame(LBC_datas)
df_financeurs = pd.json_normalize(df['Financeurs'].explode())
df.drop(columns = ['Financeurs'], inplace = True)
df = pd.concat([df,df_financeurs], axis = 1)
print(df)


# In[95]:


###Dataframe to csv 
df.to_csv('LBC_projects', index=False, sep = ";")


# 
