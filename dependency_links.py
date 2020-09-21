### DEPENDENCY REPORT FOR BOUNDED CONTEXTS ###
### MARK BERNARDO FOR SAVVAS LEARNING COMPANY, 2020 ###
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium import webdriver
from urllib.parse import urlparse
from getpass import getpass
import pandas as pd
import re

########## USER PROMPTS ##########
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
print('Dependency Analysis for Bounded Contexts:')
print('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')


# protected credential system for single-use
savvasuser = input('Savvas SSO Username: ')
savvaspass = getpass()

# projects list
print('Enter project descriptor key(s). Separate multiple keys with a single space (ex: ESB REAL RR).')
projects_list = input('Key(s): ')
projects_list = projects_list.split(' ')

########## HARD-CODED PARAMETERS ##########

# filter out external service flags for npmjs, github, etc?
filter_external_services = True

# init chrome webdriver
driver = webdriver.Chrome(
    executable_path='/Users/mgbernardo/Downloads/chromedriver')

query = 'properties%20https'
########## BITBUCKET PARSER ##########

# get_project_links: takes a project key from bitbucket, outputs link metadata and table of occurences


def get_project_links(project='REAL', query=query,
                      savvasuser=savvasuser, savvaspass=savvaspass):
    # access search page through selenium
    url = 'https://bitbucket.savvasdev.com/plugins/servlet/search?q=project%3A{}%20{}'.format(
        project, query)
    driver.get(url)
    # sso login sequence
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.NAME, 'username')))

        driver.find_element_by_name('username').send_keys(savvasuser)
        driver.find_element_by_name('password').send_keys(savvaspass)
        driver.find_element_by_id('btn-login').click()
    except TimeoutException:
        pass
    df = pd.DataFrame(
        columns=['project', 'repo', 'filepath', 'filename', 'last commit', 'service', 'links', 'netloc', 'path', 'keywords'])
    # wait for 2FA, then store code search results

    results = WebDriverWait(driver, 60).until(EC.presence_of_element_located(
        (By.CLASS_NAME, 'search-result.code-search-result.truncated')))
    # get list of results
    results = (driver.find_elements_by_class_name(
        'search-result.code-search-result'))
    results += (driver.find_elements_by_class_name(
        'search-result.code-search-result.truncated'))
    for i in range(len(results)):
        # scrape info for project column
        projecttext = results[i].find_element_by_class_name(
            'code-search-repo-link.code-search-header-link').text
        projecttext = projecttext.replace(' ', '')
        # scrape info for repo column
        repotext = results[i].find_element_by_class_name(
            'code-search-repository').text
        repotext = repotext.replace(' ', '')
        # scrape info for path column
        pathtext = ''
        for path in results[i].find_elements_by_class_name('code-search-filepart'):
            pathtext += path.text
        # scrape info for ilename column
        nametext = results[i].find_element_by_class_name(
            'non-collapsible.code-search-filename').text
        nametext = nametext.replace(' ', '')
        # scrape info for links column
        try:
            linktext = results[i].find_element_by_tag_name('code').text
            links = re.findall(
                r'://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', linktext)
        except NoSuchElementException:
            links = '[]'
        # scrape info for time column
        fileurl = results[i].find_element_by_class_name(
            "non-collapsible.code-search-filename").get_attribute('href')
        driver.execute_script("window.open(arguments[0])", fileurl)
        driver.switch_to_window(driver.window_handles[1])
        timetext = driver.find_element_by_tag_name('time').text
        driver.close()
        driver.switch_to_window(driver.window_handles[0])
        # create dataframe
        df = df.append({'project': projecttext, 'repo': repotext,
                        'filepath': pathtext, 'filename': nametext,
                        'last commit': timetext, 'links': links}, ignore_index=True)
    # remove rows with no links
    df = df[df.astype(str)['links'] != '[]'].reset_index(drop=True)
    df = df.explode('links')
    # scrape info for services referenced column
    servicenames = ['rumba', 'easybridge', 'goldengate', 'telemetry',
                    'savvas', 'pearson', 'realize', 'bitbucket', 'config']
    # dissect urls to extract service keywords
    for i in range(len(df.links)):
        df['keywords'].iloc[i] = [
            name for name in servicenames if name in str(df.links.iloc[i])]
        df.links.iloc[i] = 'https' + df.links.iloc[i]
        parse = urlparse(str(df.links.iloc[i]))
        df['netloc'].iloc[i] = parse.netloc
        df['path'].iloc[i] = parse.path
        # extract value from path to service column
        try:
            df['service'].iloc[i] = df['path'].iloc[i].split('/')[1]
        except IndexError:
            df['service'].iloc[i] = ''
        # sometimes HTML tags arent cleaned correctly, this finds the right services
        if (df['service'].iloc[i] == '<' or df['service'].iloc[i] == 'string>' or df['path'].iloc[i] == ''
                or 'sapi' in df['path'].iloc[i] or df['path'].iloc[i] == '/'):
            df['service'].iloc[i] = df['netloc'].iloc[i].split('.')[0]
        # drop rows that link to  JPG or PNG files
        if 'jpg' in df['path'].iloc[i] or 'png' in df['path'].iloc[i]:
            df['keywords'].iloc[i] = '[]'
    # internal/external link filter: drop rows w/ no keywords
    if filter_external_services == True:
        df = df[df.astype(str)['keywords'] != '[]'].reset_index(drop=True)
    # drop rows w/ readme.md files
    df = df[df.astype(str)['filename'] != 'README.md'].reset_index(drop=True)
    # save main dataframe as csv
    df.to_csv(project+'-frame.csv')
    # create pivot table for at-a-glance service mapping
    df_pivot = df.pivot_table(values='links', index=[
        'repo', 'service'], aggfunc='count')
    df_pivot.to_csv(project+'-pivot.csv')
    # verify program has finished
    return 'Saved as: {p}-frame.csv and {p}-pivot.csv'.format(p=project)


# execute code for given project(s)
for project in projects_list:
    get_project_links(project=project)
