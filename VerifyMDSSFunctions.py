# coding=utf-8
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import unittest
import json
import requests
import xlrd
from pyvirtualdisplay import Display
# -*- coding: utf-8 -*-

# /Users/ryankavanaugh/Desktop/QA/MDSS\ Update/
# Make sure this test only goes to staging and does not hit prod

def AdjustResolution():
    display = Display(visible=0, size=(800, 800))
    display.start()

# Open corresponding Excel Workbook
workbook = xlrd.open_workbook('MDSSTestInputs.xlsx')
worksheet = workbook.sheet_by_index(0)
worksheetUrls = workbook.sheet_by_index(1)

# Jenkins Resolution Variable (i.e. required function for Jenkins virtual machine)
adjustResolution = worksheet.cell(1, 5).value

# API Call data
authTokenURL = worksheetUrls.cell(1, 0).value
currentConditionsAPIURL = worksheetUrls.cell(1, 1).value
tgWebURL = worksheetUrls.cell(1, 2).value
userName = worksheet.cell(1, 3).value
password = worksheet.cell(1, 4).value

# Lists populated by spreadsheet data
apiJsonList = []
toolTipsList = []
expectedStatementsList = []


for x in range (1,4):
    apiJsonList.append(worksheet.cell(x, 1).value)
    toolTipsList.append(worksheet.cell(x, 0).value)
    expectedStatementsList.append(worksheet.cell(x, 2).value)


if adjustResolution == 1:
    AdjustResolution()


def Create_TG_Segments_Event(apiJson):
    # Get auth token from API
    myResponse = requests.post(authTokenURL, json={'userName': userName, 'password': password})
    jData = json.loads(myResponse.content)
    AuthID = jData.get('id')
    # Post a new snow event to the API
    headers = {'x-crc-authToken': AuthID, 'Accept': 'application/json'}  # , 'text':'javascript'}
    currentConditionsResponse = requests.post(currentConditionsAPIURL, headers=headers, json=apiJson)
    return headers


def Create_Dictionary_Of_IDs_And_Tooltips_From_Json(driver):
    # Link to TG WEB Staging API, open up TG WEB Winter Conditions Road Report
    tgWebDict = {}
    driver.get(tgWebURL)
    # Get all the json from the API
    data = driver.find_element_by_tag_name('body').text
    jsonData = json.loads(data)
    # Get  road reports
    for item in jsonData:
        IDNum = item.get('id')
        toolTip = item.get('tooltip')
        tgWebDict[IDNum] = toolTip
    return tgWebDict


def Verify_MDSS_Data_On_TG_Web_Album_View(driver, toolTipStatement, expectedStatement, tgWebDictMDSS):
    for roadReportsNum in tgWebDictMDSS:
    #    print tgWebDictMDSS[roadReportsNum]
        if toolTipStatement in tgWebDictMDSS[roadReportsNum]:
            roadReportsURL = 'http://mnwebtg.carsstage.org/#roadReports/eventAlbum/' + str(
                roadReportsNum)  # + '?timeFrame=TODAY&layers=winterDriving%2CvoxReports%2Cflooding'
            driver.get(roadReportsURL)

            # Assert Album View Has Been Populated Properly
            mdssWait = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CLASS_NAME, "eventGalleryBodyText")))

            try:
                mdsssTextTest = driver.find_elements_by_xpath("//*[@data-test-desc-source]")
                for item in mdsssTextTest:
                    if 'computers' in item.text:
                        mdssUpdateText = item.text
                    if 'roadway' in item.text:
                        weatherUpdate = item.text

                # Assert the data from TG Segments Album view matches the spreadsheet data
                assert expectedStatement in weatherUpdate

                # Assert the MDSS data is correct
                roadReport = tgWebDictMDSS[roadReportsNum]
                start = ', '
                end = '.'
                mdssWords = roadReport[roadReport.find(start) + len(start):roadReport.rfind(end)]
                mdssList = mdssWords.split()

                print 'MDSS'
                # Check that road report data from the JSon is correctly displayed in TG-Web
                for mdssWord in mdssList:
                    return mdssWord in mdssUpdateText

            except:
                # If no MDSS data is present, asser that the user's input in TG Segments is correctly displayed
                gallery = driver.find_element_by_class_name('eventGallerySideMargin')
                # print gallery.text
                print 'No MDSS data present'
                time.sleep(10)
                return expectedStatement in gallery.text


class Verify_MDSS_Data(unittest.TestCase):

    def setUp(self):
        self.driver = webdriver.Chrome()
        self.driver.maximize_window()


    def test_mdss_data(self):

        # Create instance of WebDriver (named driver as per usual)
        driver = self.driver

        # Assert MDSS data is a part of Winter Driving Events (loop through spreadsheet data)
        for y in range(0, 3):

            # Display item number for spreadsheet
            print 'Item number: ' + str(y+1)

            # Create a new TG Segments Event. Return AuthToken API headers for deleting event later on.
            headers = Create_TG_Segments_Event(apiJsonList[y])
            # Create a dictionary of Segment IDs and the Road Report descriptions that correspond to them
            tgWebDict = Create_Dictionary_Of_IDs_And_Tooltips_From_Json(driver)
            assert Verify_MDSS_Data_On_TG_Web_Album_View(driver, toolTipsList[y], expectedStatementsList[y], tgWebDict)

            # Delete the event
            currentConditionsDeletion = requests.post(currentConditionsAPIURL, headers=headers, json={"segmentIds": [1052], "deleteCurrentConditionsOnly": True})


    def tearDown(self):
        self.driver.quit()


if __name__ == '__main__':
    unittest.main()

