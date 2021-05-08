from selenium import webdriver
import time
import selenium.webdriver.support.ui as ui
from selenium.webdriver.common.keys import Keys
import os
import pandas as pd
from config import config, save

last_directory = config(section='general')['directory']

def return_match(pattern:str, text:str, groups=1):
    import re
    result = []
    match = re.search(pattern, text)
    if isinstance(groups, int):
        if match:
            result = match.group(groups)
        else:
            pass
    elif isinstance(groups, list) or isinstance(groups, range):
        for group in groups:
            if match:
                result.append(match.group(group))
            else:
                pass                    
    else:
        raise ValueError('groups must be one of the following types: int, list or range')
    
    return result

class RuctScraper():

    def __init__(self,
        directory = '', reset_csv=False):
        self.directory = directory
        option = webdriver.ChromeOptions()
        chrome_prefs = {}
        option.experimental_options["prefs"] = chrome_prefs
        chrome_prefs["profile.default_content_settings"] = {"images": 2}
        chrome_prefs["profile.managed_default_content_settings"] = {"images": 2}
        option.add_experimental_option( "prefs",{'profile.managed_default_content_settings.javascript': 2})
        self.driver = webdriver.Chrome("chromedriver.exe", chrome_options=option)
        self.reset_csv = reset_csv
        if self.reset_csv:
            self.location = config(section='default_location')
        else:
            self.location = config()
        for k,v in self.location.items():
            self.location[k] = int(v)
        self.ruct_url = "https://www.educacion.gob.es/ruct/home"
        self.universities = self.create_file('universities.csv')
        self.centers = self.create_file('centers.csv')
        self.titles = self.create_file('titles.csv')
    
    def create_file(self, address):
        file = self.directory + "/" + address
        if self.reset_csv:
            if address == 'universities.csv':
                cols = f"university_name$university_code$acronym$university_type$cif$erasmus_code$profit_motive$authority$locality$municiplaity$province$comunidad_autonoma$bulletin_type$publication_year$disposition_type$disposition_date$publication_date$start_date"
            elif address == 'centers.csv':
                cols = f"university_code$center_name$center_code$university_type$center_classification$center_nature$address$zip_code$locality$municiplaity$province$comunidad_autonoma$url$email$phone1$phone2$fax$bulletin_type$publication_year$disposition_type$disposition_date$publication_date$start_date"
            elif address == 'titles.csv':
                cols = f"university_code$center_code$title_code$title_name$academic_level$rd_academic_level$status_pub$status$meces_level$title_branch$professionalizer$credits_basic$credits_mandatory$credits_optional$credits_practices$credits_thesis$total_credits"            
            with open(file, 'w') as f:
                f.write(cols)
        return file
    
    def save_location(self):
        for k,v in self.location.items():
            save(k, str(v))

    def extract_data(self):
        def append_university(university):
            university_fields = university.find_elements_by_xpath(".//td")
            url =  university.find_element_by_xpath(".//a").get_attribute("href") 
            self.driver.execute_script("window.open('');")

            # University        
            self.driver.switch_to.window(self.driver.window_handles[1])
            self.driver.get(url)

            centers = self.driver.find_elements_by_link_text('Ver centros')
            url =  centers[0].get_attribute("href") 
            self.driver.execute_script("window.open('');")

            university_row = UNIVERSITY_TEMPLATE.copy()
                    
            university_name = self.driver.find_element_by_css_selector("h2").text
            university_row[university_row.index('university_name')] = university_name
            
            fields = self.driver.find_elements_by_xpath(".//fieldset/label")
            for field in fields:
                field = field.find_elements_by_css_selector("span")
                try:
                    key = field[0].text
                    value = field[1].text
                    set_key_value(university_row, key, value)
                except:
                    pass
            
            university_row = [x if x not in UNIVERSITY_TEMPLATE else '' for x in university_row]
            with open(self.universities, 'a', encoding='utf-8') as f:
                f.write(f"\n{'$ '.join(university_row)}")

            # Centers view
            self.driver.switch_to.window(self.driver.window_handles[2])
            self.driver.get(url)

            results = self.driver.find_element_by_class_name('pagebanner').text        
            if results != "Ningún registro encontrado.":                              
                if self.location['centers_page']:
                    p = self.location['centers_page']
                    while p > 0:
                        nextpg = self.driver.find_element_by_link_text("Siguiente")
                        nextpg.click()
                        p -= 1
                nxt_content = True
                while nxt_content:
                    try:
                        nextpg = self.driver.find_element_by_link_text("Siguiente")
                        nxt_content = True
                    except:
                        nxt_content = False
                    center_rows = self.driver.find_elements_by_xpath("//tbody/tr")
                    l_center_rows = len(center_rows)    
                    while self.location['center_num'] < l_center_rows:
                        center = center_rows[self.location['center_num']]
                        append_center(center)          
                        self.location['center_num'] += 1
                    if nxt_content:
                        nextpg.click()
                    self.location['center_num'] = 0
                    self.location['centers_page'] += 1
            
            self.location['centers_page'] = 0 
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[1]) 
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])

        def append_center(center):
            center_fields = center.find_elements_by_xpath(".//td")

            url =  center_fields[1].find_element_by_xpath(".//a").get_attribute("href") 
            self.driver.execute_script("window.open('');")

            # Center        
            self.driver.switch_to.window(self.driver.window_handles[3])
            self.driver.get(url)

            center_row = CENTER_TEMPLATE.copy()
            center_row[center_row.index('university_code')] = str(self.location['university_code'])                
            center_name = self.driver.find_element_by_css_selector("h3").text
            center_row[center_row.index('center_name')] = center_name
            
            fields = self.driver.find_elements_by_xpath(".//fieldset/label")
            for field in fields:
                field = field.find_elements_by_css_selector("span")
                try:
                    key = field[0].text
                    value = field[1].text
                    set_key_value(center_row, key, value)
                except:
                    pass
            center_row = [x if x not in CENTER_TEMPLATE else '' for x in center_row]
            with open(self.centers, 'a', encoding='utf-8') as f:
                f.write(f"\n{'$ '.join(center_row)}")

            url =  self.driver.find_element_by_link_text('Ver títulos').get_attribute("href") 
            self.driver.execute_script("window.open('');")

            # Titles view          
            self.driver.switch_to.window(self.driver.window_handles[4])
            self.driver.get(url)
            results = self.driver.find_element_by_class_name('pagebanner').text
            if results != "Ningún registro encontrado.":                              
                if self.location['titles_page']:
                    p = self.location['titles_page']
                    while p > 0:
                        nextpg = self.driver.find_element_by_link_text("Siguiente")
                        nextpg.click()
                        p -= 1
                nxt_content = True
                while nxt_content:
                    try:
                        nextpg = self.driver.find_element_by_link_text("Siguiente")
                        nxt_content = True
                    except:
                        nxt_content = False
                    title_rows = self.driver.find_elements_by_xpath("//tbody/tr")
                    l_title_rows = len(title_rows)
                    while self.location['titles_num'] < l_title_rows:
                        title = title_rows[self.location['titles_num']]
                        append_title(title)
                        self.location['titles_num'] += 1
                    if nxt_content:
                        nextpg.click()
                    self.location['titles_num'] = 0
                    self.location['titles_page'] += 1
            
            self.location['titles_page'] = 0                
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[3])
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[2]) 

        def append_title(title):

            title_row = TITLE_TEMPLATE.copy()
            title_row[title_row.index('university_code')] =  str(self.location['university_code'])
            title_row[title_row.index('center_code')] = str(self.location['center_code'])

            title_fields = title.find_elements_by_xpath(".//td")
            title_code = title_fields[0].text
            title_row[title_row.index('title_code')] = title_code
            title_name = title_fields[1].text
            title_row[title_row.index('title_name')] = title_name
            status_txt = title_fields[3].text
            status = return_match("(.+)\s+[(](.+)[)]", status_txt, [1,2])
            if status:    
                status_pub = status[0]
                title_row[title_row.index('status_pub')] = status_pub
                status = status[1]
                title_row[title_row.index('status')] = status
            else:    
                status_pub = status_txt.strip()
                title_row[title_row.index('status_pub')] = status_pub
                status = "TITULACIÓN VIGENTE"
                title_row[title_row.index('status')] = status

            url = title_fields[1].find_element_by_xpath(".//a").get_attribute("href") 
            self.driver.execute_script("window.open('');")

            # Title page            
            self.driver.switch_to.window(self.driver.window_handles[5])
            self.driver.get(url)

            fields = self.driver.find_elements_by_xpath(".//fieldset/label")

            for field in fields:
                field = field.find_elements_by_css_selector("span")
                try:
                    key = field[0].text
                    value = field[1].text
                    set_key_value(title_row, key, value)
                except:
                    pass         
            title_row = [x if x not in TITLE_TEMPLATE else '' for x in title_row]
            with open(self.titles, 'a', encoding='utf-8') as f:
                f.write(f"\n{'$ '.join(title_row)}")

            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[4])

        def iterate_over_pages(order):
            PARAMS = {
                'university' : {'page' : 'universities_page', 'num' : 'university_num', 'func' : append_university},
                'center' : {'page' : 'centers_page', 'num' : 'center_num', 'func' : append_center},
                'title' : {'page' : 'titles_page', 'num' : 'titles_num', 'func' : append_title}
                }
            page = PARAMS[order]['page']
            num = PARAMS[order]['num']
            func = PARAMS[order]['func']
            results = self.driver.find_element_by_class_name('pagebanner').text
            if results != "Ningún registro encontrado.":  
                if self.location[page]:
                    p = self.location[page]
                    while p > 0:
                        nextpg = self.driver.find_element_by_link_text("Siguiente")
                        nextpg.click()
                        p -= 1
                nxt_content = True
                while nxt_content:
                    try:
                        nextpg = self.driver.find_element_by_link_text("Siguiente")
                        nxt_content = True
                    except:
                        nxt_content = False
                    rows = self.driver.find_elements_by_xpath("//tbody/tr")
                    l_rows = len(rows)
                    while self.location[num] < l_rows:
                        data = rows[self.location[num]]
                        func(data)
                        self.location[num] += 1
                    if nxt_content:
                        nextpg.click()
                    self.location[num] = 0
                    self.location[page] += 1
                
                self.location[page] = 0

        def set_key_value(row, key, value):
            def set_university_code(row, key, value):
                self.location['university_code'] = value
                row[row.index(key)] = value
            def set_center_code(row, key, value):
                self.location['center_code'] = value
                row[row.index(key)] = value
            def set_credits(row, key, value):
                if value != '0':
                    row[row.index(key)] = value
            def set_date(row, key, value):
                raw_date = return_match(r"([0-9]{2})/([0-9]{2})/([0-9]{4,})", value, range(1,4))
                d = raw_date[0]
                m = raw_date[1]
                y = raw_date[2]
                row[row.index(key)] = f"{y}-{m}-{d}"

            def set_academic_level(row, key, value):
                match = return_match(r"(.+) - (.+)", value, [1, 2])
                if match:
                    row[row.index(key)] = match[0]
                    row[row.index('rd_academic_level')] = match[1]
                else:
                    row[row.index(key)] = value

            TRANSLATOR = {
                'Código de la universidad :' : {'key' : 'university_code', 'func' : set_university_code},
                'Acrónimo :' : {'key' : 'acronym', 'func' : None},
                'Tipo :' : {'key' : 'university_type', 'func' : None},
                'CIF :' : {'key' : 'cif', 'func' : None},
                'Código Erasmus :' : {'key' : 'erasmus_code', 'func' : None},
                'Con ánimo de lucro :' : {'key' : 'profit_motive', 'func' : None}, 
                'Administración Educativa Responsable :' : {'key' : 'authority', 'func' : None}, 
                'Localidad :' : {'key' : 'locality', 'func' : None},  
                'Municipio :' : {'key' : 'municiplaity', 'func' : None},  
                'Provincia :' : {'key' : 'province', 'func' : None},  
                'Comunidad Autónoma :' : {'key' : 'comunidad_autonoma', 'func' : None},  
                'Tipo Boletín :' : {'key' : 'bulletin_type', 'func' : None},  
                'Año publicación :' : {'key' : 'publication_year', 'func' : None},  
                'Tipo disposición :' : {'key' : 'disposition_type', 'func' : None},  
                'Fecha disposición :' : {'key' : 'disposition_date', 'func' : set_date},  
                'Fecha publicación :' : {'key' : 'publication_date', 'func' : set_date},  
                'Fecha entrada en Vigor :' : {'key' : 'start_date', 'func' : set_date},
                'Código del centro :' : {'key' : 'center_code', 'func' : set_center_code},
                'Tipo de centro :' : {'key' : 'center_type', 'func' : None},
                'Calificación jurídica :' : {'key' : 'center_classification', 'func' : None},
                'Naturaleza vinculación :' : {'key' : 'center_nature', 'func' : None},
                'Domicilio :' : {'key' : 'address', 'func' : None},
                'Código postal :' : {'key' : 'zip_code', 'func' : None},
                'URL :' : {'key' : 'url', 'func' : None},
                'E-mail :' : {'key' : 'email', 'func' : None},
                'Teléfono 1 :' : {'key' : 'phone1', 'func' : None},
                'Teléfono 2 :' : {'key' : 'phone2', 'func' : None},
                'Fax :' : {'key' : 'fax', 'func' : None},
                'Código del título:' : {'key' : 'title_code', 'func' : None},
                'Nivel académico:' : {'key' : 'academic_level', 'func' : set_academic_level},
                'Nivel MECES:' : {'key' : 'meces_level', 'func' : None},
                'Rama:' : {'key' : 'title_branch', 'func' : None},
                'Habilita para profesión regulada:' : {'key' : 'professionalizer', 'func' : None},
                'Nº Créditos de Formación Básica:' : {'key' : 'credits_basic', 'func' : set_credits},
                'Nº Créditos Obligatorios:' : {'key' : 'credits_mandatory', 'func' : set_credits},
                'Nº Créditos Optativos:' : {'key' : 'credits_optional', 'func' : set_credits},
                'Nº Créditos en Prácticas Externas:' : {'key' : 'credits_practices', 'func' : set_credits},
                'Nº Créditos Trabajo Fin de Grado/Master:' : {'key' : 'credits_thesis', 'func' : set_credits},
                'Créditos Totales:' : {'key' : 'total_credits', 'func' : set_credits}
            }

            try:
                func = TRANSLATOR[key]['func']
                key = TRANSLATOR[key]['key']
            except:
                raise Exception('Key not found')
            if func:
                func(row, key, value)
            else:
                row[row.index(key)] = value
       
        UNIVERSITY_TEMPLATE = ['university_name','university_code', 'acronym','university_type', 'cif',
            'erasmus_code', 'profit_motive', 'authority', 'locality','municiplaity','province',
            'comunidad_autonoma','bulletin_type','publication_year', 'disposition_type','disposition_date',
            'publication_date','start_date']

        CENTER_TEMPLATE = ['university_code', 'center_name','center_code','university_type','center_classification',
            'center_nature', 'address', 'zip_code', 'locality','municiplaity','province','comunidad_autonoma',
            'url', 'email', 'phone1', 'phone2','fax', 'bulletin_type','publication_year', 'disposition_type',
            'disposition_date','publication_date','start_date']

        TITLE_TEMPLATE = ['university_code', 'center_code', 'title_code', 'title_name', 'academic_level', 'rd_academic_level', 
            'status_pub', 'status', 'meces_level', 'title_branch', 'professionalizer', 'credits_basic', 
            'credits_mandatory', 'credits_optional', 'credits_practices', 'credits_thesis', 'total_credits']
        try:
            self.driver.get(self.ruct_url)
            self.driver.find_element_by_link_text('Sección universidades').click()
            self.driver.find_element_by_class_name('boton-inicio').click()

            # Universities view                              
            iterate_over_pages('university')
        except Exception as e:
            self.save_location()
            print(f"Error in title {self.location['titles_num']+1} at page {self.location['titles_page']+1}\nin center {self.location['center_num']+1} at page {self.location['centers_page']+1}\nin university {self.location['university_num']+1} at page {self.location['universities_page']+1}\n")
            print(e)
        self.save_location()
        time.sleep(50000)

rs = RuctScraper(directory=last_directory, reset_csv=True)
rs.extract_data()